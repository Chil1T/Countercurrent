from __future__ import annotations

import json
from pathlib import Path

from server.app.models.gui_runtime_config import GuiRuntimeConfig


class GuiConfigStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> GuiRuntimeConfig:
        if not self._path.exists():
            return GuiRuntimeConfig()
        return GuiRuntimeConfig.model_validate(json.loads(self._path.read_text(encoding="utf-8")))

    def save(self, config: GuiRuntimeConfig) -> GuiRuntimeConfig:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(config.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return config
