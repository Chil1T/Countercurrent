from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StageStatus(BaseModel):
    name: str
    status: str


class ChapterProgress(BaseModel):
    chapter_id: str
    status: str
    current_step: str | None = None
    completed_step_count: int = 0
    total_step_count: int = 0
    export_ready: bool = False


class CreateRunRequest(BaseModel):
    draft_id: str
    review_enabled: bool | None = None
    run_kind: Literal["chapter", "global"] = "chapter"


class RunSession(BaseModel):
    id: str
    draft_id: str
    course_id: str
    status: str
    run_kind: Literal["chapter", "global"] = "chapter"
    backend: str = "heuristic"
    hosted: bool = False
    base_url: str | None = None
    simple_model: str | None = None
    complex_model: str | None = None
    timeout_seconds: int | None = None
    target_output: str | None = None
    review_enabled: bool = False
    review_mode: str | None = None
    stages: list[StageStatus]
    chapter_progress: list[ChapterProgress] = Field(default_factory=list)
    last_error: str | None = None


class RunLogPreview(BaseModel):
    run_id: str
    available: bool
    cursor: int = 0
    content: str
    truncated: bool = False


class RunLogChunk(BaseModel):
    run_id: str
    cursor: int
    content: str
    complete: bool

class CourseResultsContext(BaseModel):
    course_id: str
    latest_run: RunSession | None = None

