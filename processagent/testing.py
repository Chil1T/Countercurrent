from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from threading import local
from typing import Any


@dataclass
class StubLLMBackend:
    responses: dict[str, Any]
    calls: list[dict[str, Any]] | None = None
    _call_metadata: Any = None

    def __post_init__(self) -> None:
        self._call_metadata = local()

    def generate_json(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        if self.calls is None:
            self.calls = []
        self.calls.append(
            {
                "agent_name": agent_name,
                "response_type": "json",
                "payload": copy.deepcopy(payload),
                "model_override": model_override,
            }
        )
        response = self._resolve_json_response(agent_name)
        self._call_metadata.value = {
            "provider": "stub",
            "model": model_override,
            "input_tokens": self._estimate_tokens(payload),
            "output_tokens": self._estimate_tokens(response),
            "duration_ms": 0,
            "status": "completed",
            "error": None,
        }
        return copy.deepcopy(response)

    def generate_text(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> str:
        if self.calls is None:
            self.calls = []
        self.calls.append(
            {
                "agent_name": agent_name,
                "response_type": "text",
                "payload": copy.deepcopy(payload),
                "model_override": model_override,
            }
        )
        response = self._resolve_text_response(agent_name)
        self._call_metadata.value = {
            "provider": "stub",
            "model": model_override,
            "input_tokens": self._estimate_tokens(payload),
            "output_tokens": self._estimate_tokens(response),
            "duration_ms": 0,
            "status": "completed",
            "error": None,
        }
        return str(response)

    def consume_last_call_metadata(self) -> dict[str, Any] | None:
        metadata = getattr(self._call_metadata, "value", None)
        self._call_metadata.value = None
        return metadata

    def _estimate_tokens(self, value: dict[str, Any] | str) -> int:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        return max(1, len(text.encode("utf-8")) // 4)

    def _resolve_json_response(self, agent_name: str) -> dict[str, Any]:
        if agent_name in self.responses:
            response = self.responses[agent_name]
            if not isinstance(response, dict):
                raise TypeError(f"Stub response for agent '{agent_name}' must be a JSON object.")
            return response
        if agent_name == "pack_plan" and "compose_pack" in self.responses:
            compose_pack = self.responses["compose_pack"]
            files = compose_pack.get("files", {}) if isinstance(compose_pack, dict) else {}
            return {
                "writer_profile": "legacy-compose-pack",
                "files": [
                    {"stage": "write_lecture_note", "file_name": "01-精讲.md", "goal": "章节精讲"},
                    {"stage": "write_terms", "file_name": "02-术语与定义.md", "goal": "术语与定义"},
                    {"stage": "write_interview_qa", "file_name": "03-面试问答.md", "goal": "面试问答"},
                    {"stage": "write_cross_links", "file_name": "04-跨章关联.md", "goal": "跨章关联"},
                    {"stage": "write_open_questions", "file_name": "05-疑点与待核.md", "goal": "疑点与待核"},
                ],
                "available_files": sorted(files.keys()),
            }
        raise KeyError(f"Stub response for agent '{agent_name}' is not configured.")

    def _resolve_text_response(self, agent_name: str) -> str:
        if agent_name in self.responses:
            response = self.responses[agent_name]
            if isinstance(response, str):
                return response
            raise TypeError(f"Stub response for agent '{agent_name}' must be text.")

        compose_pack = self.responses.get("compose_pack")
        if isinstance(compose_pack, dict):
            legacy_file_map = {
                "write_lecture_note": "01-精讲.md",
                "write_terms": "02-术语与定义.md",
                "write_interview_qa": "03-面试问答.md",
                "write_cross_links": "04-跨章关联.md",
                "write_open_questions": "05-疑点与待核.md",
            }
            file_name = legacy_file_map.get(agent_name)
            if file_name:
                files = compose_pack.get("files", {})
                if file_name in files:
                    return str(files[file_name])

        canonicalize = self.responses.get("canonicalize")
        if isinstance(canonicalize, dict):
            if agent_name == "build_global_glossary":
                return str(canonicalize.get("global_glossary", ""))
            if agent_name == "build_interview_index":
                return str(canonicalize.get("interview_index", ""))

        raise KeyError(f"Stub response for agent '{agent_name}' is not configured.")
