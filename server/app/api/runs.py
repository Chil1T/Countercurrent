from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from server.app.application.runs import DraftNotReadyError, RunConflictError, RunConfigurationError, RunService
from server.app.models.run_session import CreateRunRequest, RunLogChunk, RunLogPreview, RunSession


def build_runs_router(service: RunService) -> APIRouter:
    router = APIRouter(tags=["runs"])

    @router.post("/runs", response_model=RunSession, status_code=status.HTTP_201_CREATED)
    def create_run(request: CreateRunRequest) -> RunSession:
        try:
            run = service.create_run(request)
        except DraftNotReadyError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RunConfigurationError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if run is None:
            raise HTTPException(status_code=404, detail="Course draft not found")
        return run

    @router.get("/runs/{run_id}", response_model=RunSession)
    def get_run(run_id: str) -> RunSession:
        run = service.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @router.get("/runs/{run_id}/log", response_model=RunLogPreview)
    def get_run_log(run_id: str) -> RunLogPreview:
        payload = service.get_run_log(run_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return payload

    @router.get("/runs/{run_id}/log/events")
    async def stream_run_log_events(run_id: str, cursor: int = Query(0, ge=0)):
        run = service.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")

        async def event_stream():
            current_cursor = cursor
            while True:
                chunk = service.get_run_log_chunk(run_id, cursor=current_cursor)
                if chunk is None:
                    break
                current_cursor = chunk.cursor
                if chunk.content or chunk.complete:
                    payload = json.dumps(chunk.model_dump(), ensure_ascii=False)
                    # Pad with 2KB of comment to bypass uvicorn/proxy ASGI buffering
                    padding = ": " + " " * 2048 + "\n"
                    yield f"{padding}event: run.log\ndata: {payload}\n\n"
                if chunk.complete:
                    break
                await asyncio.sleep(1)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    @router.post("/runs/{run_id}/resume", response_model=RunSession)
    def resume_run(run_id: str) -> RunSession:
        try:
            run = service.resume_run(run_id)
        except DraftNotReadyError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RunConfigurationError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RunConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @router.post("/runs/{run_id}/clean", response_model=RunSession)
    def clean_run(run_id: str) -> RunSession:
        try:
            run = service.clean_run(run_id)
        except RunConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @router.get("/runs/{run_id}/events")
    async def stream_run_events(run_id: str):
        run = service.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")

        async def event_stream():
            while True:
                current = service.get_run(run_id)
                if current is None:
                    break
                payload = json.dumps(current.model_dump(), ensure_ascii=False)
                # Pad with 2KB of comment to bypass uvicorn/proxy ASGI buffering
                padding = ": " + " " * 2048 + "\n"
                yield f"{padding}event: run.update\ndata: {payload}\n\n"
                if current.status in {"completed", "failed", "cleaned"}:
                    break
                await asyncio.sleep(1)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    return router
