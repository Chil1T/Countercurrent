from __future__ import annotations

from uuid import uuid4

from processagent.blueprint import build_course_id
from server.app.adapters.input_storage import DraftInputStorage
from server.app.application.templates import default_template_presets
from server.app.models.course_draft import (
    CourseDraft,
    CreateCourseDraftRequest,
    DetectedCourseSummary,
    InputSlot,
    SubtitleAssetInput,
)
from server.app.models.template_preset import DraftConfig, DraftConfigRequest


class CourseDraftService:
    def __init__(self, storage: DraftInputStorage) -> None:
        self._storage = storage
        self._drafts: dict[str, CourseDraft] = {}

    def create_draft(self, request: CreateCourseDraftRequest) -> CourseDraft:
        draft_id = f"draft-{uuid4().hex[:8]}"
        book_title = request.book_title.strip()
        subtitle_assets = self._resolve_subtitle_assets(request)
        if subtitle_assets:
            self._storage.persist_subtitle_assets(draft_id=draft_id, assets=subtitle_assets)

        draft = CourseDraft(
            id=draft_id,
            course_id=build_course_id(book_title),
            book_title=book_title,
            course_url=request.course_url,
            runtime_ready=bool(subtitle_assets),
            detected=DetectedCourseSummary(
                course_name=book_title,
                textbook_title=book_title,
                chapter_count=len(subtitle_assets) or None,
                asset_completeness=self._compute_asset_completeness(request),
            ),
            input_slots=self._build_input_slots(request),
        )
        self._drafts[draft.id] = draft
        self._storage.persist_draft(draft)
        return draft

    def get_draft(self, draft_id: str) -> CourseDraft | None:
        draft = self._drafts.get(draft_id)
        if draft is not None:
            return draft

        stored = self._storage.load_draft(draft_id)
        if stored is not None:
            self._drafts[draft_id] = stored
        return stored

    def get_runtime_input_dir(self, draft_id: str):
        if not self._storage.has_runtime_input(draft_id):
            return None
        return self._storage.input_dir(draft_id)

    def storage_input_dir(self, draft_id: str):
        return self._storage.input_dir(draft_id)

    def save_config(self, draft_id: str, request: DraftConfigRequest) -> DraftConfig | None:
        draft = self.get_draft(draft_id)
        if draft is None:
            return None

        template = next(
            (item for item in default_template_presets() if item.id == request.template_id),
            None,
        )
        if template is None:
            return None

        config = DraftConfig(
            draft_id=draft.id,
            template=template,
            content_density=request.content_density,
            review_mode=request.review_mode,
            review_enabled=request.review_enabled,
            export_package=request.export_package,
            provider=request.provider,
            base_url=request.base_url,
            simple_model=request.simple_model,
            complex_model=request.complex_model,
            timeout_seconds=request.timeout_seconds,
        )
        self._drafts[draft_id] = draft.model_copy(update={"config": config})
        self._storage.persist_draft(self._drafts[draft_id])
        return config

    @staticmethod
    def _compute_asset_completeness(request: CreateCourseDraftRequest) -> int:
        completeness = 20
        if request.course_url:
            completeness += 20
        if CourseDraftService._subtitle_asset_count(request) > 0:
            completeness += 40
        return completeness

    @staticmethod
    def _build_input_slots(request: CreateCourseDraftRequest) -> list[InputSlot]:
        subtitle_count = CourseDraftService._subtitle_asset_count(request)
        return [
            InputSlot(kind="course_link", label="课程链接", supported=True, count=1 if request.course_url else 0),
            InputSlot(kind="subtitle", label="字幕", supported=True, count=subtitle_count),
            InputSlot(kind="audio_video", label="音视频", supported=False, count=0),
            InputSlot(kind="courseware", label="课件", supported=False, count=0),
            InputSlot(kind="textbook", label="教材", supported=True, count=1 if request.book_title else 0),
        ]

    @staticmethod
    def _resolve_subtitle_assets(request: CreateCourseDraftRequest) -> list[SubtitleAssetInput]:
        if request.subtitle_assets:
            return [asset for asset in request.subtitle_assets if asset.content.strip()]
        if request.subtitle_text and request.subtitle_text.strip():
            return [SubtitleAssetInput(filename="chapter-01.md", content=request.subtitle_text)]
        return []

    @staticmethod
    def _subtitle_asset_count(request: CreateCourseDraftRequest) -> int:
        return len(CourseDraftService._resolve_subtitle_assets(request))
