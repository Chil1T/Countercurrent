from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from server.app.models.template_preset import DraftConfig


class InputSlot(BaseModel):
    kind: str
    label: str
    supported: bool
    count: int = 0


class DetectedCourseSummary(BaseModel):
    course_name: str
    textbook_title: str
    chapter_count: int | None = None
    asset_completeness: int = Field(ge=0, le=100)


class SubtitleAssetInput(BaseModel):
    filename: str
    content: str


class CourseDraft(BaseModel):
    id: str
    course_id: str
    book_title: str
    course_url: str | None = None
    runtime_ready: bool = False
    detected: DetectedCourseSummary
    input_slots: list[InputSlot]
    config: DraftConfig | None = None


class CreateCourseDraftRequest(BaseModel):
    book_title: str
    course_url: str | None = None
    subtitle_text: str | None = None
    subtitle_assets: list[SubtitleAssetInput] | None = None

    @field_validator("book_title")
    @classmethod
    def validate_book_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("book_title must not be blank")
        return normalized
