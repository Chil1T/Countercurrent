from __future__ import annotations

from fastapi import APIRouter, HTTPException

from server.app.adapters.gui_config_store import GuiConfigStore
from server.app.application.course_drafts import CourseDraftService
from server.app.application.templates import default_template_presets
from server.app.models.gui_runtime_config import GuiRuntimeConfig
from server.app.models.template_preset import DraftConfig, DraftConfigRequest


def build_templates_router(service: CourseDraftService, gui_config_store: GuiConfigStore) -> APIRouter:
    router = APIRouter(tags=["templates"])

    @router.get("/templates")
    def list_templates():
        return default_template_presets()

    @router.get("/gui-runtime-config", response_model=GuiRuntimeConfig)
    def get_gui_runtime_config() -> GuiRuntimeConfig:
        return gui_config_store.load()

    @router.put("/gui-runtime-config", response_model=GuiRuntimeConfig)
    def save_gui_runtime_config(request: GuiRuntimeConfig) -> GuiRuntimeConfig:
        return gui_config_store.save(request)

    @router.post("/course-drafts/{draft_id}/config", response_model=DraftConfig)
    def save_course_draft_config(draft_id: str, request: DraftConfigRequest) -> DraftConfig:
        saved = service.save_config(draft_id=draft_id, request=request)
        if saved is None:
            raise HTTPException(status_code=404, detail="Course draft not found")
        return saved

    return router
