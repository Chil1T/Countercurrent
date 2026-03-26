from __future__ import annotations

from pydantic import BaseModel
from server.app.models.gui_runtime_config import ProviderName


class TemplatePreset(BaseModel):
    id: str
    name: str
    description: str
    expected_outputs: list[str]


class DraftConfigRequest(BaseModel):
    template_id: str
    content_density: str
    review_mode: str
    review_enabled: bool = False
    export_package: bool = True
    provider: ProviderName | None = None
    base_url: str | None = None
    simple_model: str | None = None
    complex_model: str | None = None
    timeout_seconds: int | None = None


class DraftConfig(BaseModel):
    draft_id: str
    template: TemplatePreset
    content_density: str
    review_mode: str
    review_enabled: bool = False
    export_package: bool
    provider: ProviderName | None = None
    base_url: str | None = None
    simple_model: str | None = None
    complex_model: str | None = None
    timeout_seconds: int | None = None
