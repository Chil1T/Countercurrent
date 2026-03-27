from __future__ import annotations

from dataclasses import dataclass
from threading import local
from typing import Any, Callable, TypeVar

from .llm import LLMBackend, LLMHTTPError, LLMNetworkError
from .provider_policy import ProviderExecutionPolicy

T = TypeVar("T")


@dataclass(frozen=True)
class RetryDecision:
    error_kind: str
    retry_reason: str | None
    should_retry: bool


class RetryingLLMBackend:
    def __init__(self, *, backend: LLMBackend, provider_policy: ProviderExecutionPolicy) -> None:
        self.backend = backend
        self.provider_policy = provider_policy
        self._call_metadata = local()

    def generate_json(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        return self._execute_with_retry(
            lambda: self.backend.generate_json(
                agent_name=agent_name,
                prompt=prompt,
                payload=payload,
                model_override=model_override,
            ),
            model_override=model_override,
        )

    def generate_text(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> str:
        return self._execute_with_retry(
            lambda: self.backend.generate_text(
                agent_name=agent_name,
                prompt=prompt,
                payload=payload,
                model_override=model_override,
            ),
            model_override=model_override,
        )

    def consume_last_call_metadata(self) -> dict[str, Any] | None:
        metadata = getattr(self._call_metadata, "value", None)
        self._call_metadata.value = None
        return metadata

    def _execute_with_retry(self, operation: Callable[[], T], *, model_override: str | None) -> T:
        attempts: list[dict[str, Any]] = []
        max_attempts = self.provider_policy.max_call_attempts

        for attempt_number in range(1, max_attempts + 1):
            try:
                result = operation()
                attempt_metadata = self._consume_inner_metadata()
                attempts.append(
                    self._normalize_attempt_metadata(
                        attempt_number=attempt_number,
                        metadata=attempt_metadata,
                        model_override=model_override,
                        error=None,
                        decision=None,
                        will_retry=False,
                    )
                )
                self._store_call_metadata(attempts)
                return result
            except Exception as error:
                decision = classify_retry_decision(error, self.provider_policy)
                will_retry = decision.should_retry and attempt_number < max_attempts
                attempt_metadata = self._consume_inner_metadata()
                attempts.append(
                    self._normalize_attempt_metadata(
                        attempt_number=attempt_number,
                        metadata=attempt_metadata,
                        model_override=model_override,
                        error=error,
                        decision=decision,
                        will_retry=will_retry,
                    )
                )
                if not will_retry:
                    self._store_call_metadata(attempts)
                    raise

        raise RuntimeError("Retry loop exited unexpectedly")

    def _consume_inner_metadata(self) -> dict[str, Any] | None:
        consume = getattr(self.backend, "consume_last_call_metadata", None)
        if not callable(consume):
            return None
        return consume()

    def _normalize_attempt_metadata(
        self,
        *,
        attempt_number: int,
        metadata: dict[str, Any] | None,
        model_override: str | None,
        error: Exception | None,
        decision: RetryDecision | None,
        will_retry: bool,
    ) -> dict[str, Any]:
        payload = dict(metadata or {})
        payload["attempt"] = attempt_number
        payload["provider"] = payload.get("provider") or self.provider_policy.provider
        payload["model"] = payload.get("model") or model_override
        payload["status"] = payload.get("status") or ("error" if error else "completed")
        payload["error"] = payload.get("error") or (str(error) if error else None)
        payload["error_kind"] = decision.error_kind if decision is not None else None
        payload["retry_reason"] = decision.retry_reason if decision is not None else None
        payload["will_retry"] = will_retry
        return payload

    def _store_call_metadata(self, attempts: list[dict[str, Any]]) -> None:
        final_attempt = attempts[-1]
        self._call_metadata.value = {
            "provider": final_attempt.get("provider"),
            "model": final_attempt.get("model"),
            "input_tokens": final_attempt.get("input_tokens"),
            "output_tokens": final_attempt.get("output_tokens"),
            "duration_ms": sum(int(item.get("duration_ms") or 0) for item in attempts),
            "status": final_attempt.get("status"),
            "error": final_attempt.get("error"),
            "attempt_count": len(attempts),
            "retry_history": [dict(item) for item in attempts],
            "last_error_kind": next((item["error_kind"] for item in reversed(attempts) if item.get("error_kind")), None),
            "attempts": [dict(item) for item in attempts],
        }


def classify_retry_decision(error: Exception, provider_policy: ProviderExecutionPolicy) -> RetryDecision:
    if isinstance(error, LLMHTTPError):
        error_kind = f"http_status:{error.status_code}"
        should_retry = error.status_code in provider_policy.transient_http_statuses
        retry_reason = f"transient_http_status:{error.status_code}" if should_retry else None
        return RetryDecision(error_kind=error_kind, retry_reason=retry_reason, should_retry=should_retry)
    if isinstance(error, LLMNetworkError):
        error_kind = f"network:{error.kind}"
        return RetryDecision(
            error_kind=error_kind,
            retry_reason=f"transient_network_error:{error.kind}",
            should_retry=True,
        )
    return RetryDecision(
        error_kind=f"exception:{type(error).__name__}",
        retry_reason=None,
        should_retry=False,
    )
