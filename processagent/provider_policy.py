from __future__ import annotations

from argparse import Namespace
from contextlib import contextmanager
from dataclasses import dataclass, replace
from threading import BoundedSemaphore, Lock
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


@dataclass
class _ProviderPermitState:
    limit: int
    semaphore: BoundedSemaphore
    active_permits: int = 0


class ProviderPermitRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._states: dict[str, _ProviderPermitState] = {}

    @contextmanager
    def acquire(self, policy: ProviderExecutionPolicy):
        state = self._get_or_create_state(policy)
        state.semaphore.acquire()
        with self._lock:
            state.active_permits += 1
        try:
            yield
        finally:
            with self._lock:
                state.active_permits -= 1
            state.semaphore.release()

    def active_permits(self, provider: str) -> int:
        with self._lock:
            state = self._states.get(provider)
            if state is None:
                return 0
            return state.active_permits

    def reset(self) -> None:
        with self._lock:
            self._states.clear()

    def _get_or_create_state(self, policy: ProviderExecutionPolicy) -> _ProviderPermitState:
        with self._lock:
            state = self._states.get(policy.provider)
            if state is None or (state.limit != policy.max_concurrent_global and state.active_permits == 0):
                state = _ProviderPermitState(
                    limit=policy.max_concurrent_global,
                    semaphore=BoundedSemaphore(policy.max_concurrent_global),
                )
                self._states[policy.provider] = state
                return state
            if state.limit != policy.max_concurrent_global:
                raise RuntimeError(
                    "provider global concurrency limit cannot change while permits are active: "
                    f"{policy.provider} {state.limit} -> {policy.max_concurrent_global}"
                )
            return state


_GLOBAL_PROVIDER_PERMIT_REGISTRY = ProviderPermitRegistry()


def acquire_provider_permit(policy: ProviderExecutionPolicy):
    return _GLOBAL_PROVIDER_PERMIT_REGISTRY.acquire(policy)


def get_provider_active_permits(provider: str) -> int:
    return _GLOBAL_PROVIDER_PERMIT_REGISTRY.active_permits(provider)


def reset_provider_permit_registry() -> None:
    _GLOBAL_PROVIDER_PERMIT_REGISTRY.reset()


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
