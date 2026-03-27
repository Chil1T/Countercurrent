from __future__ import annotations

import json
import os
import shutil
import time
from ctypes import byref, c_ulong
from argparse import Namespace
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

DEFAULT_TRANSIENT_HTTP_STATUSES = (408, 425, 429, 500, 502, 503, 504)
POLICY_OVERRIDE_FIELDS = (
    "max_concurrent_per_run",
    "max_concurrent_global",
    "max_call_attempts",
    "max_resume_attempts",
)
COORDINATION_ROOT_ENV_VAR = "PROCESSAGENT_COORDINATION_ROOT"
DEFAULT_COORDINATION_DIRNAME = ".processagent-runtime"
OWNER_FILENAME = "owner.json"
STALE_OWNER_GRACE_SECONDS = 1.0
WINDOWS_PROCESS_STILL_ACTIVE = 259


@dataclass(frozen=True)
class ProviderExecutionPolicy:
    provider: str
    max_concurrent_per_run: int
    max_concurrent_global: int
    transient_http_statuses: tuple[int, ...]
    max_call_attempts: int
    max_resume_attempts: int


BUILTIN_PROVIDER_EXECUTION_POLICIES: dict[str, ProviderExecutionPolicy] = {
    "openai": ProviderExecutionPolicy(
        provider="openai",
        max_concurrent_per_run=2,
        max_concurrent_global=8,
        transient_http_statuses=DEFAULT_TRANSIENT_HTTP_STATUSES,
        max_call_attempts=3,
        max_resume_attempts=2,
    ),
    "openai_compatible": ProviderExecutionPolicy(
        provider="openai_compatible",
        max_concurrent_per_run=2,
        max_concurrent_global=8,
        transient_http_statuses=DEFAULT_TRANSIENT_HTTP_STATUSES,
        max_call_attempts=3,
        max_resume_attempts=2,
    ),
    "anthropic": ProviderExecutionPolicy(
        provider="anthropic",
        max_concurrent_per_run=2,
        max_concurrent_global=6,
        transient_http_statuses=DEFAULT_TRANSIENT_HTTP_STATUSES,
        max_call_attempts=3,
        max_resume_attempts=2,
    ),
    "heuristic": ProviderExecutionPolicy(
        provider="heuristic",
        max_concurrent_per_run=1,
        max_concurrent_global=1,
        transient_http_statuses=(),
        max_call_attempts=1,
        max_resume_attempts=1,
    ),
    "stub": ProviderExecutionPolicy(
        provider="stub",
        max_concurrent_per_run=1,
        max_concurrent_global=1,
        transient_http_statuses=(),
        max_call_attempts=1,
        max_resume_attempts=1,
    ),
}


class ProviderPermitRegistry:
    def __init__(
        self,
        *,
        root_dir: Path,
        poll_interval_seconds: float = 0.01,
        stale_owner_grace_seconds: float = STALE_OWNER_GRACE_SECONDS,
    ) -> None:
        self.root_dir = root_dir
        self.poll_interval_seconds = poll_interval_seconds
        self.stale_owner_grace_seconds = stale_owner_grace_seconds

    @contextmanager
    def acquire(self, policy: ProviderExecutionPolicy):
        slot_dir = self._acquire_slot(policy)
        try:
            yield
        finally:
            self._release_slot(slot_dir)

    def active_permits(self, provider: str) -> int:
        provider_dir = self.root_dir / provider
        if not provider_dir.exists():
            return 0
        count = 0
        for path in provider_dir.iterdir():
            if not path.is_dir() or not path.name.startswith("slot-"):
                continue
            if reclaim_stale_owned_directory(
                path,
                stale_owner_grace_seconds=self.stale_owner_grace_seconds,
            ):
                continue
            count += 1
        return count

    def reset(self) -> None:
        if self.root_dir.exists():
            shutil.rmtree(self.root_dir)

    def _acquire_slot(self, policy: ProviderExecutionPolicy) -> Path:
        provider_dir = self.root_dir / policy.provider
        configured_limit = self._ensure_provider_limit(provider_dir, policy)
        owner_payload = build_coordination_owner_payload({"provider": policy.provider, "kind": "provider-slot"})

        while True:
            for slot_index in range(configured_limit):
                slot_dir = provider_dir / f"slot-{slot_index:02d}"
                if try_acquire_owned_directory(
                    slot_dir,
                    owner_payload=owner_payload,
                    stale_owner_grace_seconds=self.stale_owner_grace_seconds,
                ):
                    return slot_dir
            time.sleep(self.poll_interval_seconds)

    def _release_slot(self, slot_dir: Path) -> None:
        release_owned_directory(slot_dir)

    def _ensure_provider_limit(self, provider_dir: Path, policy: ProviderExecutionPolicy) -> int:
        provider_dir.mkdir(parents=True, exist_ok=True)
        limit_path = provider_dir / "limit.json"
        limit_lock_dir = provider_dir / "limit-config.lock"
        requested_limit = policy.max_concurrent_global
        owner_payload = build_coordination_owner_payload({"provider": policy.provider, "kind": "limit-config-lock"})

        with wait_for_owned_directory(
            limit_lock_dir,
            owner_payload=owner_payload,
            poll_interval_seconds=self.poll_interval_seconds,
            stale_owner_grace_seconds=self.stale_owner_grace_seconds,
        ):
            current_limit = _read_provider_limit(limit_path)
            if current_limit == requested_limit:
                return requested_limit
            if current_limit is not None and self.active_permits(policy.provider) > 0:
                raise RuntimeError(
                    "provider global concurrency limit cannot change while permits are active: "
                    f"{policy.provider} {current_limit} -> {requested_limit}"
                )
            _write_json_atomically(limit_path, {"max_concurrent_global": requested_limit})
            return requested_limit


def acquire_provider_permit(policy: ProviderExecutionPolicy, *, coordination_root: Path):
    return ProviderPermitRegistry(root_dir=coordination_root).acquire(policy)


def get_provider_active_permits(provider: str, *, coordination_root: Path) -> int:
    return ProviderPermitRegistry(root_dir=coordination_root).active_permits(provider)


def reset_provider_permit_registry(*, coordination_root: Path | None = None) -> None:
    ProviderPermitRegistry(root_dir=coordination_root or get_provider_coordination_root()).reset()


def get_service_coordination_root() -> Path:
    configured_root = os.environ.get(COORDINATION_ROOT_ENV_VAR)
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return Path(__file__).resolve().parent.parent / DEFAULT_COORDINATION_DIRNAME


def get_provider_coordination_root() -> Path:
    return get_service_coordination_root() / "provider_permits"


def build_coordination_owner_payload(extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "pid": os.getpid(),
        "acquired_at": time.time(),
    }
    if extra:
        payload.update(dict(extra))
    return payload


@contextmanager
def wait_for_owned_directory(
    lock_dir: Path,
    *,
    owner_payload: Mapping[str, Any] | None = None,
    poll_interval_seconds: float = 0.01,
    stale_owner_grace_seconds: float = STALE_OWNER_GRACE_SECONDS,
):
    payload = dict(owner_payload or build_coordination_owner_payload())
    while True:
        if try_acquire_owned_directory(
            lock_dir,
            owner_payload=payload,
            stale_owner_grace_seconds=stale_owner_grace_seconds,
        ):
            break
        time.sleep(poll_interval_seconds)
    try:
        yield lock_dir
    finally:
        release_owned_directory(lock_dir)


def try_acquire_owned_directory(
    lock_dir: Path,
    *,
    owner_payload: Mapping[str, Any] | None = None,
    stale_owner_grace_seconds: float = STALE_OWNER_GRACE_SECONDS,
) -> bool:
    payload = dict(owner_payload or build_coordination_owner_payload())
    try:
        lock_dir.mkdir(parents=False, exist_ok=False)
    except (FileExistsError, PermissionError):
        if reclaim_stale_owned_directory(lock_dir, stale_owner_grace_seconds=stale_owner_grace_seconds):
            try:
                lock_dir.mkdir(parents=False, exist_ok=False)
            except (FileExistsError, PermissionError):
                return False
        else:
            return False
    try:
        _write_json_atomically(lock_dir / OWNER_FILENAME, payload)
    except Exception:
        shutil.rmtree(lock_dir, ignore_errors=True)
        raise
    return True


def release_owned_directory(lock_dir: Path) -> None:
    if not lock_dir.exists():
        return
    shutil.rmtree(lock_dir, ignore_errors=True)


def reclaim_stale_owned_directory(
    lock_dir: Path,
    *,
    stale_owner_grace_seconds: float = STALE_OWNER_GRACE_SECONDS,
) -> bool:
    if not lock_dir.exists():
        return False
    if not _owned_directory_is_stale(lock_dir, stale_owner_grace_seconds=stale_owner_grace_seconds):
        return False
    shutil.rmtree(lock_dir, ignore_errors=True)
    return not lock_dir.exists()


def get_builtin_provider_policy(provider: str) -> ProviderExecutionPolicy:
    try:
        return BUILTIN_PROVIDER_EXECUTION_POLICIES[provider]
    except KeyError as error:
        raise ValueError(f"Unsupported provider policy: {provider}") from error


def apply_config_policy_overrides(
    policy: ProviderExecutionPolicy,
    overrides: Mapping[str, Any] | object | None,
) -> ProviderExecutionPolicy:
    return _apply_policy_overrides(policy, overrides)


def apply_cli_policy_overrides(
    policy: ProviderExecutionPolicy,
    overrides: Mapping[str, Any] | Namespace | object | None,
) -> ProviderExecutionPolicy:
    return _apply_policy_overrides(policy, overrides)


def resolve_provider_execution_policy(
    provider: str,
    config_policy: Mapping[str, Any] | object | None = None,
    cli_overrides: Mapping[str, Any] | Namespace | object | None = None,
) -> ProviderExecutionPolicy:
    policy = get_builtin_provider_policy(provider)
    policy = apply_config_policy_overrides(policy, config_policy)
    return apply_cli_policy_overrides(policy, cli_overrides)


def _apply_policy_overrides(
    policy: ProviderExecutionPolicy,
    overrides: Mapping[str, Any] | Namespace | object | None,
) -> ProviderExecutionPolicy:
    raw_values = _coerce_override_mapping(overrides)
    update_values: dict[str, int] = {}
    for field_name in POLICY_OVERRIDE_FIELDS:
        value = raw_values.get(field_name)
        if value is None:
            continue
        update_values[field_name] = _validate_positive_int(field_name, value)
    if not update_values:
        return policy
    return replace(policy, **update_values)


def _coerce_override_mapping(overrides: Mapping[str, Any] | Namespace | object | None) -> dict[str, Any]:
    if overrides is None:
        return {}
    if isinstance(overrides, Namespace):
        return vars(overrides)
    if isinstance(overrides, Mapping):
        return dict(overrides)
    if hasattr(overrides, "model_dump"):
        return dict(overrides.model_dump())
    return {field_name: getattr(overrides, field_name, None) for field_name in POLICY_OVERRIDE_FIELDS}


def _validate_positive_int(field_name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than 0")
    return value


def _read_provider_limit(limit_path: Path) -> int | None:
    payload = _read_json_file(limit_path)
    if not isinstance(payload, dict):
        return None
    value = payload.get("max_concurrent_global")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _owned_directory_is_stale(
    lock_dir: Path,
    *,
    stale_owner_grace_seconds: float,
) -> bool:
    owner_path = lock_dir / OWNER_FILENAME
    owner_payload = _read_json_file(owner_path)
    if owner_payload is None:
        return _path_age_seconds(owner_path if owner_path.exists() else lock_dir) >= stale_owner_grace_seconds
    pid = owner_payload.get("pid")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return True
    return not _pid_is_running(pid)


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return None
    if not raw_text.strip():
        return None
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _write_json_atomically(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    temp_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temp_path, path)


def _path_age_seconds(path: Path) -> float:
    try:
        return max(0.0, time.time() - path.stat().st_mtime)
    except FileNotFoundError:
        return 0.0
    except OSError:
        return STALE_OWNER_GRACE_SECONDS


def _pid_is_running(pid: int) -> bool:
    if pid == os.getpid():
        return True
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        process_handle = kernel32.OpenProcess(0x1000, False, pid)
        if not process_handle:
            return ctypes.get_last_error() == 5
        try:
            exit_code = c_ulong()
            if not kernel32.GetExitCodeProcess(process_handle, byref(exit_code)):
                return True
            return exit_code.value == WINDOWS_PROCESS_STILL_ACTIVE
        finally:
            kernel32.CloseHandle(process_handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
