from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
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


def parse_json_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
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
            raise RuntimeError(f"LLM request failed: {error.code} {detail}") from error


@dataclass
class OpenAIResponsesBackend(HttpJsonBackend):
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
        raw = self._post_json(
            self.base_url,
            request_body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        text = self._extract_text(raw)
        return parse_json_text(text)

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


@dataclass
class OpenAICompatibleResponsesBackend(OpenAIResponsesBackend):
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
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
        }

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
        raw = self._post_json(
            self.base_url,
            request_body,
            headers={
                "x-api-key": api_key,
                "anthropic-version": self.anthropic_version,
                "Content-Type": "application/json",
            },
        )
        text = self._extract_text(raw)
        return parse_json_text(text)

    def _extract_text(self, response_json: dict[str, Any]) -> str:
        texts: list[str] = []
        for content in response_json.get("content", []):
            if content.get("type") == "text" and content.get("text"):
                texts.append(content["text"])
        if texts:
            return "\n".join(texts)
        raise RuntimeError("Anthropic response did not include text content.")
