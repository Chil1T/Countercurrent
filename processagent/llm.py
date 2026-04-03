from __future__ import annotations

import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from threading import local
from typing import Any, Protocol


class LLMBackend(Protocol):
    def generate_json(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        ...

    def generate_text(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> str:
        ...


class LLMHTTPError(RuntimeError):
    def __init__(self, *, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"LLM request failed: {status_code} {detail}")


class LLMNetworkError(RuntimeError):
    def __init__(self, *, kind: str, message: str) -> None:
        self.kind = kind
        self.message = message
        super().__init__(message)


def parse_json_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise json.JSONDecodeError("Could not extract a JSON object from blank model output", stripped, 0)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", stripped, flags=re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char not in "[{":
            continue
        try:
            parsed, _end = decoder.raw_decode(stripped[index:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("Could not extract a JSON object from model output", stripped, 0)


@dataclass
class HttpJsonBackend:
    timeout_seconds: int = 120
    _call_metadata: Any = field(default_factory=local, init=False, repr=False)

    def _post_json(self, url: str, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise LLMHTTPError(status_code=error.code, detail=detail) from error
        except urllib.error.URLError as error:
            raise _coerce_network_error(error.reason if error.reason is not None else error) from error
        except TimeoutError as error:
            raise LLMNetworkError(kind="timeout", message=str(error)) from error
        except ConnectionResetError as error:
            raise LLMNetworkError(kind="connection_reset", message=str(error)) from error
        except OSError as error:
            if _is_transient_network_os_error(error):
                raise _coerce_network_error(error) from error
            raise

    def consume_last_call_metadata(self) -> dict[str, Any] | None:
        metadata = getattr(self._call_metadata, "value", None)
        self._call_metadata.value = None
        return metadata

    def _usage_from_response(self, response_json: dict[str, Any]) -> tuple[int | None, int | None]:
        usage = response_json.get("usage", {})
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        if input_tokens is None:
            input_tokens = usage.get("prompt_tokens")
        if output_tokens is None:
            output_tokens = usage.get("completion_tokens")
        return input_tokens, output_tokens

    def _store_last_call_metadata(
        self,
        *,
        provider: str,
        model: str | None,
        response_json: dict[str, Any] | None,
        duration_ms: int,
        status: str,
        error: str | None = None,
    ) -> None:
        input_tokens, output_tokens = (None, None)
        if response_json is not None:
            input_tokens, output_tokens = self._usage_from_response(response_json)
        self._call_metadata.value = {
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
            "status": status,
            "error": error,
        }


@dataclass
class OpenAIResponsesBackend(HttpJsonBackend):
    provider_name: str = "openai"
    model: str = "gpt-5.4-mini"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = "https://api.openai.com/v1/responses"
    timeout_seconds: int = 120

    def generate_json(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"{self.api_key_env} is required for the openai backend. "
                "Use --backend heuristic or --backend stub for offline runs."
            )

        request_body = self._build_request_body(prompt, payload, model_override=model_override)
        started_at = time.perf_counter()
        response_json: dict[str, Any] | None = None
        try:
            response_json = self._post_json(
                self.base_url,
                request_body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            text = self._extract_text(response_json)
            parsed = parse_json_text(text)
        except Exception as error:
            self._store_last_call_metadata(
                provider=self.provider_name,
                model=model_override or self.model,
                response_json=response_json,
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                status="error",
                error=str(error),
            )
            raise
        self._store_last_call_metadata(
            provider=self.provider_name,
            model=model_override or self.model,
            response_json=response_json,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            status="completed",
        )
        return parsed

    def generate_text(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> str:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"{self.api_key_env} is required for the openai backend. "
                "Use --backend heuristic or --backend stub for offline runs."
            )

        request_body = self._build_text_request_body(prompt, payload, model_override=model_override)
        started_at = time.perf_counter()
        response_json: dict[str, Any] | None = None
        try:
            response_json = self._post_json(
                self.base_url,
                request_body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            text = self._extract_text(response_json).strip()
        except Exception as error:
            self._store_last_call_metadata(
                provider=self.provider_name,
                model=model_override or self.model,
                response_json=response_json,
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                status="error",
                error=str(error),
            )
            raise
        self._store_last_call_metadata(
            provider=self.provider_name,
            model=model_override or self.model,
            response_json=response_json,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            status="completed",
        )
        return text

    def _build_request_body(
        self,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        return {
            "model": model_override or self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": json.dumps(payload, ensure_ascii=False)}],
                },
            ],
        }

    def _build_text_request_body(
        self,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        return self._build_request_body(prompt, payload, model_override=model_override)

    def _extract_text(self, response_json: dict[str, Any]) -> str:
        if isinstance(response_json.get("output_text"), str):
            return response_json["output_text"]

        outputs = response_json.get("output", [])
        texts: list[str] = []
        for item in outputs:
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    texts.append(text)
        if texts:
            return "\n".join(texts)
        raise RuntimeError("OpenAI response did not include text output.")


def _coerce_network_error(error: BaseException) -> LLMNetworkError:
    if isinstance(error, TimeoutError):
        return LLMNetworkError(kind="timeout", message=str(error))
    if isinstance(error, ConnectionResetError):
        return LLMNetworkError(kind="connection_reset", message=str(error))
    if isinstance(error, socket.timeout):
        return LLMNetworkError(kind="timeout", message=str(error))
    if isinstance(error, OSError):
        kind = _network_os_error_kind(error)
        if kind is not None:
            return LLMNetworkError(kind=kind, message=str(error))
    return LLMNetworkError(kind="urlopen", message=str(error))


def _is_transient_network_os_error(error: OSError) -> bool:
    if isinstance(error, socket.timeout):
        return True
    if isinstance(error, ConnectionResetError):
        return True
    return _network_os_error_kind(error) is not None


def _network_os_error_kind(error: OSError) -> str | None:
    if getattr(error, "errno", None) == 104 or getattr(error, "winerror", None) == 10054:
        return "connection_reset"
    if getattr(error, "errno", None) == 110 or getattr(error, "winerror", None) == 10060:
        return "timeout"
    if getattr(error, "errno", None) == 111 or getattr(error, "winerror", None) == 10061:
        return "connection_error"
    return None


@dataclass
class OpenAICompatibleResponsesBackend(OpenAIResponsesBackend):
    provider_name: str = "openai_compatible"
    model: str = "openai/gpt-4.1-mini"
    api_key_env: str = "OPENAI_COMPATIBLE_API_KEY"
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    timeout_seconds: int = 120

    def _uses_chat_completions(self) -> bool:
        return self.base_url.rstrip("/").endswith("/chat/completions")

    def _build_request_body(
        self,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        if not self._uses_chat_completions():
            return super()._build_request_body(prompt, payload, model_override=model_override)
        return {
            "model": model_override or self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self._ensure_json_instruction(prompt),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            "response_format": {"type": "json_object"},
        }

    def _build_text_request_body(
        self,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        if not self._uses_chat_completions():
            return super()._build_text_request_body(prompt, payload, model_override=model_override)
        return {
            "model": model_override or self.model,
            "messages": [
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
        }

    @staticmethod
    def _ensure_json_instruction(prompt: str) -> str:
        if "json" in prompt.lower():
            return prompt
        return f"{prompt}\n\nReturn a JSON object."

    def _extract_text(self, response_json: dict[str, Any]) -> str:
        if not self._uses_chat_completions():
            return super()._extract_text(response_json)

        choices = response_json.get("choices", [])
        texts: list[str] = []
        for choice in choices:
            message = choice.get("message", {})
            content = message.get("content")
            if isinstance(content, str) and content:
                texts.append(content)
            elif isinstance(content, list):
                for item in content:
                    if item.get("type") == "text" and item.get("text"):
                        texts.append(item["text"])
        if texts:
            return "\n".join(texts)
        raise RuntimeError("OpenAI-compatible chat completions response did not include text content.")


@dataclass
class AnthropicMessagesBackend(HttpJsonBackend):
    model: str = "claude-sonnet-4-20250514"
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: str = "https://api.anthropic.com/v1/messages"
    anthropic_version: str = "2023-06-01"
    max_tokens: int = 4096
    timeout_seconds: int = 120

    def generate_json(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"{self.api_key_env} is required for the anthropic backend. "
                "Use --backend heuristic or --backend stub for offline runs."
            )

        request_body = {
            "model": model_override or self.model,
            "max_tokens": self.max_tokens,
            "system": prompt,
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                }
            ],
        }
        started_at = time.perf_counter()
        response_json: dict[str, Any] | None = None
        try:
            response_json = self._post_json(
                self.base_url,
                request_body,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": self.anthropic_version,
                    "Content-Type": "application/json",
                },
            )
            text = self._extract_text(response_json)
            parsed = parse_json_text(text)
        except Exception as error:
            self._store_last_call_metadata(
                provider="anthropic",
                model=model_override or self.model,
                response_json=response_json,
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                status="error",
                error=str(error),
            )
            raise
        self._store_last_call_metadata(
            provider="anthropic",
            model=model_override or self.model,
            response_json=response_json,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            status="completed",
        )
        return parsed

    def generate_text(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> str:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"{self.api_key_env} is required for the anthropic backend. "
                "Use --backend heuristic or --backend stub for offline runs."
            )

        request_body = {
            "model": model_override or self.model,
            "max_tokens": self.max_tokens,
            "system": prompt,
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                }
            ],
        }
        started_at = time.perf_counter()
        response_json: dict[str, Any] | None = None
        try:
            response_json = self._post_json(
                self.base_url,
                request_body,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": self.anthropic_version,
                    "Content-Type": "application/json",
                },
            )
            text = self._extract_text(response_json).strip()
        except Exception as error:
            self._store_last_call_metadata(
                provider="anthropic",
                model=model_override or self.model,
                response_json=response_json,
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                status="error",
                error=str(error),
            )
            raise
        self._store_last_call_metadata(
            provider="anthropic",
            model=model_override or self.model,
            response_json=response_json,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            status="completed",
        )
        return text

    def _extract_text(self, response_json: dict[str, Any]) -> str:
        texts: list[str] = []
        for content in response_json.get("content", []):
            if content.get("type") == "text" and content.get("text"):
                texts.append(content["text"])
        if texts:
            return "\n".join(texts)
        raise RuntimeError("Anthropic response did not include text content.")
