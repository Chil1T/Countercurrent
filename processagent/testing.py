from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass
class StubLLMBackend:
    responses: dict[str, dict[str, Any]]
    calls: list[dict[str, Any]] | None = None

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
                "payload": copy.deepcopy(payload),
                "model_override": model_override,
            }
        )
        if agent_name not in self.responses:
            raise KeyError(f"Stub response for agent '{agent_name}' is not configured.")
        return copy.deepcopy(self.responses[agent_name])
