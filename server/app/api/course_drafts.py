from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from server.app.application.course_drafts import CourseDraftService
from server.app.models.course_draft import CourseDraft, CreateCourseDraftRequest, SubtitleAssetInput


def build_course_drafts_router(service: CourseDraftService) -> APIRouter:
    router = APIRouter(tags=["course-drafts"])

    @router.post("/course-drafts", response_model=CourseDraft, status_code=status.HTTP_201_CREATED)
    async def create_course_draft(request: Request) -> CourseDraft:
        content_type = request.headers.get("content-type", "")
        try:
            if "multipart/form-data" in content_type:
                payload = await _parse_multipart_create_request(request)
            else:
                payload = CreateCourseDraftRequest.model_validate(await request.json())
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc
        return service.create_draft(payload)

    @router.get("/course-drafts/{draft_id}", response_model=CourseDraft)
    def get_course_draft(draft_id: str) -> CourseDraft:
        draft = service.get_draft(draft_id)
        if draft is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course draft not found")
        return draft

    return router


async def _parse_multipart_create_request(request: Request) -> CreateCourseDraftRequest:
    form = await request.form()
    upload_items = form.getlist("subtitle_files")
    subtitle_assets: list[SubtitleAssetInput] = []
    for item in upload_items:
        filename = getattr(item, "filename", "")
        if not filename:
            continue
        content = (await item.read()).decode("utf-8")
        await item.close()
        if not content.strip():
            continue
        subtitle_assets.append(SubtitleAssetInput(filename=filename, content=content))

    return CreateCourseDraftRequest(
        book_title=str(form.get("book_title", "")),
        course_url=str(form.get("course_url")) if form.get("course_url") else None,
        subtitle_assets=subtitle_assets or None,
    )
