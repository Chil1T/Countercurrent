from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.app.adapters.cli_runner import LocalProcessRunner
from server.app.adapters.gui_config_store import GuiConfigStore
from server.app.adapters.input_storage import DraftInputStorage
from server.app.adapters.runtime_reader import RuntimeStateReader
from server.app.api.artifacts import build_artifacts_router
from server.app.api.course_drafts import build_course_drafts_router
from server.app.api.runs import build_runs_router
from server.app.api.templates import build_templates_router
from server.app.application.artifacts import ArtifactService
from server.app.application.course_drafts import CourseDraftService
from server.app.application.runs import RunService


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_gui_config_path() -> Path:
    return Path.home() / ".codex" / "databaseleaning" / "gui-config.json"


def create_app(
    output_root: Path | None = None,
    workspace_root: Path | None = None,
    gui_config_path: Path | None = None,
    run_runner=None,
) -> FastAPI:
    repo_root = _default_repo_root()
    resolved_output_root = output_root or (repo_root / "out")
    resolved_workspace_root = workspace_root or repo_root
    resolved_gui_config_path = gui_config_path or _default_gui_config_path()
    app = FastAPI(title="databaseleaning-gui-api")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    course_draft_service = CourseDraftService(storage=DraftInputStorage(resolved_output_root))
    gui_config_store = GuiConfigStore(resolved_gui_config_path)
    run_service = RunService(
        course_drafts=course_draft_service,
        runner=run_runner or LocalProcessRunner(
            workspace_root=resolved_workspace_root,
            log_root=resolved_output_root / "_gui" / "runs",
        ),
        runtime_reader=RuntimeStateReader(resolved_output_root),
        output_root=resolved_output_root,
        gui_config_store=gui_config_store,
    )
    artifact_service = ArtifactService(output_root=resolved_output_root)
    app.include_router(build_course_drafts_router(course_draft_service))
    app.include_router(build_templates_router(course_draft_service, gui_config_store))
    app.include_router(build_runs_router(run_service))
    app.include_router(build_artifacts_router(artifact_service))

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "databaseleaning-gui-api"}

    return app


app = create_app()
