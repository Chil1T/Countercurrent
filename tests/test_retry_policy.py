import threading
import unittest
from typing import Any

from processagent.provider_policy import ProviderExecutionPolicy


class ScriptedLLMBackend:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0
        self._metadata = threading.local()

    def generate_json(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            self._metadata.value = {
                "provider": "openai",
                "model": model_override or "model-x",
                "input_tokens": 10,
                "output_tokens": None,
                "duration_ms": 1,
                "status": "error",
                "error": str(outcome),
            }
            raise outcome
        self._metadata.value = {
            "provider": "openai",
            "model": model_override or "model-x",
            "input_tokens": 10,
            "output_tokens": 5,
            "duration_ms": 1,
            "status": "completed",
            "error": None,
        }
        return outcome

    def generate_text(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> str:
        response = self.generate_json(agent_name, prompt, payload, model_override=model_override)
        return str(response)

    def consume_last_call_metadata(self) -> dict[str, Any] | None:
        metadata = getattr(self._metadata, "value", None)
        self._metadata.value = None
        return metadata


class RetryingLLMBackendTest(unittest.TestCase):
    def _policy(self, *, max_call_attempts: int = 3) -> ProviderExecutionPolicy:
        return ProviderExecutionPolicy(
            provider="openai",
            max_concurrent_per_run=1,
            max_concurrent_global=1,
            transient_http_statuses=(408, 429, 500, 502, 503, 504),
            max_call_attempts=max_call_attempts,
            max_resume_attempts=1,
        )

    def test_transient_http_status_retries_until_success(self) -> None:
        from processagent.llm import LLMHTTPError
        from processagent.retrying_llm import RetryingLLMBackend

        backend = ScriptedLLMBackend(
            [
                LLMHTTPError(status_code=429, detail="busy"),
                LLMHTTPError(status_code=503, detail="overloaded"),
                {"status": "ok"},
            ]
        )
        wrapped = RetryingLLMBackend(backend=backend, provider_policy=self._policy(), sleep=lambda _seconds: None)

        response = wrapped.generate_json("curriculum_anchor", "prompt", {"chapter": 1})
        metadata = wrapped.consume_last_call_metadata()

        self.assertEqual(response, {"status": "ok"})
        self.assertEqual(backend.calls, 3)
        self.assertEqual(metadata["attempt_count"], 3)
        self.assertEqual([item["status"] for item in metadata["retry_history"]], ["error", "error", "completed"])
        self.assertEqual(metadata["last_error_kind"], "http_status:503")

    def test_transient_errors_sleep_with_exponential_backoff(self) -> None:
        from processagent.llm import LLMHTTPError
        from processagent.retrying_llm import RetryingLLMBackend

        backend = ScriptedLLMBackend(
            [
                LLMHTTPError(status_code=429, detail="busy"),
                LLMHTTPError(status_code=503, detail="overloaded"),
                {"status": "ok"},
            ]
        )
        sleep_calls: list[float] = []
        wrapped = RetryingLLMBackend(
            backend=backend,
            provider_policy=self._policy(),
            sleep=sleep_calls.append,
            initial_backoff_seconds=0.25,
        )

        response = wrapped.generate_json("curriculum_anchor", "prompt", {"chapter": 1})

        self.assertEqual(response, {"status": "ok"})
        self.assertEqual(backend.calls, 3)
        self.assertEqual(sleep_calls, [0.25, 0.5])

    def test_transient_network_error_retries(self) -> None:
        from processagent.llm import LLMNetworkError
        from processagent.retrying_llm import RetryingLLMBackend

        backend = ScriptedLLMBackend(
            [
                LLMNetworkError(kind="timeout", message="timed out"),
                {"status": "ok"},
            ]
        )
        wrapped = RetryingLLMBackend(backend=backend, provider_policy=self._policy(), sleep=lambda _seconds: None)

        wrapped.generate_json("curriculum_anchor", "prompt", {"chapter": 1})
        metadata = wrapped.consume_last_call_metadata()

        self.assertEqual(backend.calls, 2)
        self.assertEqual(metadata["attempt_count"], 2)
        self.assertEqual(metadata["retry_history"][0]["error_kind"], "network:timeout")

    def test_permanent_error_does_not_retry(self) -> None:
        from processagent.llm import LLMHTTPError
        from processagent.retrying_llm import RetryingLLMBackend

        backend = ScriptedLLMBackend([LLMHTTPError(status_code=400, detail="bad request")])
        sleep_calls: list[float] = []
        wrapped = RetryingLLMBackend(
            backend=backend,
            provider_policy=self._policy(),
            sleep=sleep_calls.append,
        )

        with self.assertRaises(LLMHTTPError):
            wrapped.generate_json("curriculum_anchor", "prompt", {"chapter": 1})

        metadata = wrapped.consume_last_call_metadata()
        self.assertEqual(backend.calls, 1)
        self.assertEqual(sleep_calls, [])
        self.assertEqual(metadata["attempt_count"], 1)
        self.assertEqual(metadata["last_error_kind"], "http_status:400")

    def test_exhausted_attempts_raise_after_limit(self) -> None:
        from processagent.llm import LLMHTTPError
        from processagent.retrying_llm import RetryingLLMBackend

        backend = ScriptedLLMBackend(
            [
                LLMHTTPError(status_code=429, detail="busy"),
                LLMHTTPError(status_code=429, detail="still busy"),
                LLMHTTPError(status_code=429, detail="give up"),
            ]
        )
        wrapped = RetryingLLMBackend(
            backend=backend,
            provider_policy=self._policy(max_call_attempts=3),
            sleep=lambda _seconds: None,
        )

        with self.assertRaises(LLMHTTPError):
            wrapped.generate_json("curriculum_anchor", "prompt", {"chapter": 1})

        metadata = wrapped.consume_last_call_metadata()
        self.assertEqual(backend.calls, 3)
        self.assertEqual(metadata["attempt_count"], 3)
        self.assertEqual(metadata["retry_history"][-1]["will_retry"], False)


if __name__ == "__main__":
    unittest.main()
