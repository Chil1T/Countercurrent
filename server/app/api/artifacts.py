from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from server.app.application.artifacts import ArtifactService
from server.app.models.review_summary import ReviewSummary


def build_artifacts_router(service: ArtifactService) -> APIRouter:
    router = APIRouter(tags=["artifacts"])

    @router.get("/courses/{course_id}/artifacts/tree")
    def get_artifact_tree(course_id: str):
        payload = service.list_tree(course_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Course artifacts not found")
        return payload

    @router.get("/courses/{course_id}/artifacts/content")
    def get_artifact_content(course_id: str, path: str = Query(...)):
        payload = service.read_content(course_id, path)
        if payload is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return payload

    @router.get("/courses/{course_id}/review-summary", response_model=ReviewSummary)
    def get_review_summary(course_id: str) -> ReviewSummary:
        payload = service.build_review_summary(course_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Course artifacts not found")
        return payload

    @router.get("/courses/{course_id}/results-snapshot")
    def get_results_snapshot(course_id: str):
        return service.list_results_snapshot(course_id)

    @router.get("/courses/{course_id}/results-snapshot/content")
    def get_results_snapshot_content(
        course_id: str,
        run_id: str = Query(...),
        path: str = Query(...),
        source_course_id: str | None = Query(None),
    ):
        payload = service.read_results_snapshot_content(
            source_course_id=source_course_id or course_id,
            run_id=run_id,
            relative_path=path,
        )
        if payload is None:
            raise HTTPException(status_code=404, detail="Snapshot artifact not found")
        return payload

    @router.get("/courses/{course_id}/export")
    def export_course(
        course_id: str,
        completed_chapters_only: bool = Query(False),
        final_outputs_only: bool = Query(False),
    ):
        payload = service.export_zip(
            course_id,
            completed_chapters_only=completed_chapters_only,
            final_outputs_only=final_outputs_only,
        )
        if payload is None:
            raise HTTPException(status_code=404, detail="Course artifacts not found")
        filename, content = payload
        encoded_filename = quote(filename)
        return Response(
            content=content,
            media_type="application/zip",
            headers={
                "Cache-Control": "no-store, max-age=0",
                "Content-Disposition": (
                    f'attachment; filename="course-export.zip"; filename*=UTF-8\'\'{encoded_filename}'
                ),
            },
        )

    return router
