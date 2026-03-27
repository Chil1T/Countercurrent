from __future__ import annotations

import json
import os
import shutil
import time
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
    def __init__(self, *, root_dir: Path, poll_interval_seconds: float = 0.01) -> None:
        self.root_dir = root_dir
        self.poll_interval_seconds = poll_interval_seconds

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
        return sum(1 for path in provider_dir.iterdir() if path.is_dir() and path.name.startswith("slot-"))

    def reset(self) -> None:
        if self.root_dir.exists():
            shutil.rmtree(self.root_dir)

    def _acquire_slot(self, policy: ProviderExecutionPolicy) -> Path:
        provider_dir = self.root_dir / policy.provider
        configured_limit = self._ensure_provider_limit(provider_dir, policy)
        owner_payload = self._build_owner_payload()

        while True:
            for slot_index in range(configured_limit):
                slot_dir = provider_dir / f"slot-{slot_index:02d}"
                try:
                    slot_dir.mkdir(parents=False, exist_ok=False)
                except (FileExistsError, PermissionError):
                    continue
                self._write_owner_payload(slot_dir, owner_payload)
                return slot_dir
            time.sleep(self.poll_interval_seconds)

    def _release_slot(self, slot_dir: Path) -> None:
        if not slot_dir.exists():
            return
        shutil.rmtree(slot_dir, ignore_errors=True)

    def _ensure_provider_limit(self, provider_dir: Path, policy: ProviderExecutionPolicy) -> int:
        provider_dir.mkdir(parents=True, exist_ok=True)
        limit_path = provider_dir / "limit.json"
        requested_limit = policy.max_concurrent_global
        payload = json.dumps({"max_concurrent_global": requested_limit}, ensure_ascii=False)

        while True:
            if limit_path.exists():
                current_limit = json.loads(limit_path.read_text(encoding="utf-8")).get("max_concurrent_global")
                if current_limit == requested_limit:
                    return requested_limit
                if self.active_permits(policy.provider) > 0:
                    raise RuntimeError(
                        "provider global concurrency limit cannot change while permits are active: "
                        f"{policy.provider} {current_limit} -> {requested_limit}"
                    )
                limit_path.write_text(payload, encoding="utf-8")
                return requested_limit
            try:
                with limit_path.open("x", encoding="utf-8") as handle:
                    handle.write(payload)
                return requested_limit
            except FileExistsError:
                continue

    def _build_owner_payload(self) -> dict[str, Any]:
        return {
            "pid": os.getpid(),
            "acquired_at": time.time(),
        }

    def _write_owner_payload(self, slot_dir: Path, payload: dict[str, Any]) -> None:
        (slot_dir / "owner.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def acquire_provider_permit(policy: ProviderExecutionPolicy, *, coordination_root: Path):
    return ProviderPermitRegistry(root_dir=coordination_root).acquire(policy)


def get_provider_active_permits(provider: str, *, coordination_root: Path) -> int:
    return ProviderPermitRegistry(root_dir=coordination_root).active_permits(provider)


def reset_provider_permit_registry(*, coordination_root: Path | None = None) -> None:
    if coordination_root is None:
        return
    ProviderPermitRegistry(root_dir=coordination_root).reset()


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
