from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from processagent.cli import normalize_base_url
from processagent.pipeline import WRITER_STAGE_SETS
from server.app.adapters.cli_runner import CourseRunSpec
from server.app.adapters.gui_config_store import GuiConfigStore
from server.app.adapters.runtime_reader import RuntimeSnapshot, RuntimeStateReader
from server.app.application.course_drafts import CourseDraftService
from server.app.models.gui_runtime_config import ProviderName
from server.app.models.run_session import CreateRunRequest, RunLogChunk, RunLogPreview, RunSession, StageStatus

CHAPTER_STAGE_PREFIX = [
    "build_blueprint",
    "ingest",
    "curriculum_anchor",
    "gap_fill",
    "pack_plan",
]

GLOBAL_STAGE_NAMES = [
    "build_global_glossary",
    "build_interview_index",
]


def _active_writer_names(target_output: str | None) -> list[str]:
    profile = target_output or "standard_knowledge_pack"
    return list(WRITER_STAGE_SETS.get(profile, WRITER_STAGE_SETS["standard_knowledge_pack"]))


def _stage_names_for(run_kind: Literal["chapter", "global"], review_enabled: bool, target_output: str | None) -> list[str]:
    if run_kind == "global":
        return GLOBAL_STAGE_NAMES
    stage_names = list(CHAPTER_STAGE_PREFIX) + _active_writer_names(target_output)
    if review_enabled:
        stage_names.append("review")
    return stage_names


class DraftNotReadyError(RuntimeError):
    pass


class RunConflictError(RuntimeError):
    pass


class RunConfigurationError(RuntimeError):
    pass


@dataclass
class _RunRecord:
    session: RunSession
    last_command: Literal["run-course", "resume-course", "clean-course", "build-global"] = "run-course"


@dataclass(frozen=True)
class _ResolvedRuntimeConfig:
    backend: ProviderName
    hosted: bool
    base_url: str | None
    model: str | None
    simple_model: str | None
    complex_model: str | None
    timeout_seconds: int | None
    env_overrides: dict[str, str]


class RunService:
    def __init__(
        self,
        course_drafts: CourseDraftService,
        runner,
        runtime_reader: RuntimeStateReader,
        output_root: Path,
        gui_config_store: GuiConfigStore,
    ) -> None:
        self._course_drafts = course_drafts
        self._runner = runner
        self._runtime_reader = runtime_reader
        self._output_root = output_root
        self._gui_config_store = gui_config_store
        self._run_state_root = output_root / "_gui" / "runs"
        self._runs: dict[str, _RunRecord] = {}

    def create_run(self, request: CreateRunRequest) -> RunSession | None:
        draft = self._course_drafts.get_draft(request.draft_id)
        if draft is None:
            return None

        runtime_config = self._resolve_runtime_config(draft)
        review_mode, target_output, default_review_enabled = self._resolve_runtime_policy(draft)
        review_enabled = request.review_enabled if request.review_enabled is not None else default_review_enabled
        run_kind = request.run_kind
        command: Literal["run-course", "build-global"] = "build-global" if run_kind == "global" else "run-course"
        input_dir = None
        if run_kind == "chapter":
            input_dir = self._course_drafts.get_runtime_input_dir(request.draft_id)
            if input_dir is None:
                raise DraftNotReadyError("Course draft is not ready to run")

        session = RunSession(
            id=f"run-{uuid4().hex[:8]}",
            draft_id=draft.id,
            course_id=draft.course_id,
            status="created",
            run_kind=run_kind,
            backend=runtime_config.backend,
            hosted=runtime_config.hosted,
            base_url=runtime_config.base_url,
            simple_model=runtime_config.simple_model,
            complex_model=runtime_config.complex_model,
            timeout_seconds=runtime_config.timeout_seconds,
            target_output=target_output,
            review_enabled=review_enabled if run_kind == "chapter" else False,
            review_mode=review_mode,
            stages=[
                StageStatus(name=name, status="pending")
                for name in _stage_names_for(
                    run_kind,
                    review_enabled if run_kind == "chapter" else False,
                    target_output,
                )
            ],
            last_error=None,
        )
        self._runs[session.id] = _RunRecord(session=session, last_command=command)
        self._start_process(record=self._runs[session.id], command=command, book_title=draft.book_title, input_dir=input_dir)
        self._persist_record(self._runs[session.id])
        return self.get_run(session.id)

    def resume_run(self, run_id: str) -> RunSession | None:
        record = self._runs.get(run_id) or self._load_record(run_id)
        if record is None:
            return None
        self._runs[run_id] = record
        self._ensure_mutable(record.session.id)
        draft = self._course_drafts.get_draft(record.session.draft_id)
        if draft is None:
            return None
        runtime_config = self._resolve_runtime_config(draft)
        record.session = record.session.model_copy(
            update={
                "backend": runtime_config.backend,
                "hosted": runtime_config.hosted,
                "base_url": runtime_config.base_url,
                "simple_model": runtime_config.simple_model,
                "complex_model": runtime_config.complex_model,
                "timeout_seconds": runtime_config.timeout_seconds,
                "last_error": None,
            }
        )
        input_dir = None
        command: Literal["resume-course", "build-global"] = "resume-course"
        if record.session.run_kind == "chapter":
            input_dir = self._course_drafts.get_runtime_input_dir(record.session.draft_id)
            if input_dir is None:
                raise DraftNotReadyError("Course draft is not ready to run")
        else:
            command = "build-global"
        self._start_process(record=record, command=command, book_title=draft.book_title, input_dir=input_dir)
        self._persist_record(record)
        return self.get_run(run_id)

    def clean_run(self, run_id: str) -> RunSession | None:
        record = self._runs.get(run_id) or self._load_record(run_id)
        if record is None:
            return None
        self._runs[run_id] = record
        self._ensure_mutable(record.session.id)
        draft = self._course_drafts.get_draft(record.session.draft_id)
        if draft is None:
            return None
        input_dir = self._course_drafts.get_runtime_input_dir(record.session.draft_id) or self._course_drafts.storage_input_dir(
            record.session.draft_id
        )
        self._start_process(record=record, command="clean-course", book_title=draft.book_title, input_dir=input_dir)
        self._persist_record(record)
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> RunSession | None:
        record = self._runs.get(run_id) or self._load_record(run_id)
        if record is None:
            return None
        self._runs[run_id] = record

        snapshot = self._runner.snapshot(run_id)
        runtime = self._runtime_reader.read(record.session.course_id)
        status = self._resolve_status(record=record, snapshot=snapshot, runtime=runtime)
        snapshot_error = self._snapshot_value(snapshot, "last_error")
        if status in {"running", "completed", "cleaned"} and snapshot_error is None:
            last_error = None
        else:
            last_error = snapshot_error or (runtime.last_error if runtime else None)
        stages = self._map_stages(
            runtime=runtime,
            run_status=status,
            last_command=record.last_command,
            run_kind=record.session.run_kind,
            review_enabled=record.session.review_enabled,
            target_output=record.session.target_output,
        )
        updated = record.session.model_copy(
            update={
                "status": status,
                "stages": stages,
                "last_error": last_error,
            }
        )
        record.session = updated
        self._persist_record(record)
        return updated

    def get_run_log(self, run_id: str, max_chars: int = 4000) -> RunLogPreview | None:
        record = self._runs.get(run_id) or self._load_record(run_id)
        if record is None:
            return None
        self._runs[run_id] = record

        snapshot = self._runner.snapshot(run_id)
        log_path = self._resolve_log_path(run_id, snapshot)
        if not log_path:
            return RunLogPreview(run_id=run_id, available=False, cursor=0, content="", truncated=False)

        path = Path(log_path)
        if not path.exists() or path.is_dir():
            return RunLogPreview(run_id=run_id, available=False, cursor=0, content="", truncated=False)

        content = path.read_text(encoding="utf-8")
        truncated = len(content) > max_chars
        preview = content[-max_chars:] if truncated else content
        return RunLogPreview(
            run_id=run_id,
            available=True,
            cursor=len(content),
            content=preview,
            truncated=truncated,
        )

    def get_run_log_chunk(self, run_id: str, cursor: int = 0) -> RunLogChunk | None:
        record = self._runs.get(run_id) or self._load_record(run_id)
        if record is None:
            return None
        self._runs[run_id] = record

        snapshot = self._runner.snapshot(run_id)
        runtime = self._runtime_reader.read(record.session.course_id)
        log_path = self._resolve_log_path(run_id, snapshot)
        if not log_path:
            return RunLogChunk(run_id=run_id, cursor=cursor, content="", complete=False)

        path = Path(log_path)
        if not path.exists() or path.is_dir():
            return RunLogChunk(run_id=run_id, cursor=cursor, content="", complete=False)

        content = path.read_text(encoding="utf-8")
        next_cursor = min(max(cursor, 0), len(content))
        chunk = content[next_cursor:]
        return RunLogChunk(
            run_id=run_id,
            cursor=len(content),
            content=chunk,
            complete=self._resolve_status(record=record, snapshot=snapshot, runtime=runtime) in {"completed", "failed", "cleaned"},
        )

    def _map_stages(
        self,
        runtime: RuntimeSnapshot | None,
        run_status: str,
        last_command: str,
        run_kind: Literal["chapter", "global"],
        review_enabled: bool,
        target_output: str | None,
    ) -> list[StageStatus]:
        stage_names = _stage_names_for(run_kind, review_enabled, target_output)
        if last_command == "clean-course" and run_status in {"running", "cleaned"}:
            return [StageStatus(name=name, status="pending") for name in stage_names]

        statuses = {name: "pending" for name in stage_names}
        if run_kind == "chapter" and runtime is not None and runtime.blueprint_ready and "build_blueprint" in statuses:
            statuses["build_blueprint"] = "completed"

        if run_kind == "chapter" and runtime is not None and runtime.chapter_count > 0:
            for step_name, completed_count in runtime.completed_steps.items():
                if step_name not in statuses:
                    continue
                if completed_count >= runtime.chapter_count:
                    statuses[step_name] = "completed"
                elif completed_count > 0:
                    statuses[step_name] = "running"

        if run_kind == "global" and runtime is not None:
            for step_name, completed in runtime.global_steps.items():
                if step_name not in statuses:
                    continue
                if completed:
                    statuses[step_name] = "completed"

        if run_status in {"running", "failed"}:
            pending = next((name for name in stage_names if statuses[name] == "pending"), None)
            if pending is not None:
                statuses[pending] = "failed" if run_status == "failed" else "running"

        return [StageStatus(name=name, status=statuses[name]) for name in stage_names]

    @staticmethod
    def _snapshot_value(snapshot, key: str):
        if snapshot is None:
            return None
        if isinstance(snapshot, dict):
            return snapshot.get(key)
        return getattr(snapshot, key, None)

    def _resolve_log_path(self, run_id: str, snapshot) -> Path | None:
        log_path = self._snapshot_value(snapshot, "log_path")
        if log_path:
            return Path(log_path)
        fallback_path = self._record_path(run_id).parent / "process.log"
        if fallback_path.exists() and fallback_path.is_file():
            return fallback_path
        return None

    def _resolve_status(self, record: _RunRecord, snapshot, runtime: RuntimeSnapshot | None) -> str:
        runner_status = self._snapshot_value(snapshot, "status")
        if record.last_command == "clean-course":
            if runner_status == "failed":
                return "failed"
            if runner_status == "running":
                return "running"
            if runner_status == "completed":
                return "cleaned"
            return record.session.status
        if runner_status is None:
            if runtime is not None and self._runtime_is_complete(
                runtime=runtime,
                run_kind=record.session.run_kind,
                review_enabled=record.session.review_enabled,
                target_output=record.session.target_output,
            ):
                return "completed"
            if runtime is not None and runtime.last_error:
                return "failed"
            return record.session.status
        return runner_status

    @staticmethod
    def _runtime_is_complete(
        runtime: RuntimeSnapshot,
        run_kind: Literal["chapter", "global"],
        review_enabled: bool,
        target_output: str | None,
    ) -> bool:
        if run_kind == "global":
            return all(runtime.global_steps.get(name, False) for name in GLOBAL_STAGE_NAMES)
        if runtime.chapter_count == 0:
            return False
        required_steps = [
            "ingest",
            "curriculum_anchor",
            "gap_fill",
            "pack_plan",
            *_active_writer_names(target_output),
        ]
        if review_enabled:
            required_steps.append("review")
        return all(runtime.completed_steps.get(step_name, 0) >= runtime.chapter_count for step_name in required_steps)

    def _ensure_mutable(self, run_id: str) -> None:
        snapshot = self._runner.snapshot(run_id)
        if self._snapshot_value(snapshot, "status") == "running":
            raise RunConflictError("Run is already in progress")

    def _start_process(
        self,
        *,
        record: _RunRecord,
        command: Literal["run-course", "resume-course", "clean-course", "build-global"],
        book_title: str,
        input_dir: Path | None,
    ) -> None:
        record.last_command = command
        is_clean = command == "clean-course"
        self._runner.start(
            CourseRunSpec(
                run_id=record.session.id,
                command=command,
                book_title=book_title,
                input_dir=input_dir,
                output_dir=self._output_root,
                backend="heuristic" if is_clean else record.session.backend,
                base_url=None if is_clean else record.session.base_url,
                model=None if is_clean else (record.session.complex_model or record.session.simple_model),
                simple_model=None if is_clean else record.session.simple_model,
                complex_model=None if is_clean else record.session.complex_model,
                timeout_seconds=None if is_clean else record.session.timeout_seconds,
                env_overrides={} if is_clean else self._build_env_overrides(record.session.backend),
                review_enabled=False if is_clean else record.session.review_enabled,
                review_mode=None if (is_clean or not record.session.review_enabled) else record.session.review_mode,
                target_output=None if is_clean else record.session.target_output,
            )
        )

    @staticmethod
    def _resolve_runtime_policy(draft) -> tuple[str | None, str | None, bool]:
        config = getattr(draft, "config", None)
        if config is None:
            return None, None, False
        review_mode = config.review_mode
        target_output = {
            "standard-knowledge-pack": "standard_knowledge_pack",
            "lecture-deep-dive": "lecture_deep_dive",
            "interview-focus": "interview_knowledge_base",
        }.get(config.template.id)
        return review_mode, target_output, config.review_enabled

    def _resolve_runtime_config(self, draft) -> _ResolvedRuntimeConfig:
        draft_config = getattr(draft, "config", None)
        gui_config = self._gui_config_store.load()
        backend = (getattr(draft_config, "provider", None) or gui_config.default_provider or "heuristic")
        if backend == "heuristic":
            return _ResolvedRuntimeConfig(
                backend="heuristic",
                hosted=False,
                base_url=None,
                model=None,
                simple_model=None,
                complex_model=None,
                timeout_seconds=None,
                env_overrides={},
            )

        provider_defaults = getattr(gui_config.providers, backend)
        api_key = (provider_defaults.api_key or "").strip()
        if not api_key:
            raise RunConfigurationError(f"API key is required for backend: {backend}")

        base_url = self._first_nonempty(getattr(draft_config, "base_url", None), provider_defaults.base_url)
        if base_url is not None:
            try:
                base_url = normalize_base_url(backend, base_url)
            except SystemExit as error:
                raise RunConfigurationError(str(error)) from error
        simple_model = self._first_nonempty(getattr(draft_config, "simple_model", None), provider_defaults.simple_model)
        complex_model = self._first_nonempty(getattr(draft_config, "complex_model", None), provider_defaults.complex_model)
        timeout_seconds = getattr(draft_config, "timeout_seconds", None)
        if timeout_seconds is None:
            timeout_seconds = provider_defaults.timeout_seconds
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise RunConfigurationError("timeout_seconds must be greater than 0")
        if simple_model is None:
            simple_model = complex_model
        if complex_model is None:
            complex_model = simple_model

        return _ResolvedRuntimeConfig(
            backend=backend,
            hosted=True,
            base_url=base_url,
            model=complex_model or simple_model,
            simple_model=simple_model,
            complex_model=complex_model,
            timeout_seconds=timeout_seconds,
            env_overrides=self._build_env_overrides(backend),
        )

    def _build_env_overrides(self, backend: str) -> dict[str, str]:
        if backend == "heuristic":
            return {}
        provider_defaults = getattr(self._gui_config_store.load().providers, backend)
        api_key = (provider_defaults.api_key or "").strip()
        if not api_key:
            return {}
        env_key = {
            "openai": "OPENAI_API_KEY",
            "openai_compatible": "OPENAI_COMPATIBLE_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }[backend]
        return {env_key: api_key}

    @staticmethod
    def _first_nonempty(*values: str | None) -> str | None:
        for value in values:
            if value is not None and str(value).strip():
                return value
        return None

    def _record_path(self, run_id: str) -> Path:
        return self._run_state_root / run_id / "session.json"

    def _persist_record(self, record: _RunRecord) -> None:
        path = self._record_path(record.session.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "session": record.session.model_dump(),
                    "last_command": record.last_command,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _load_record(self, run_id: str) -> _RunRecord | None:
        path = self._record_path(run_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _RunRecord(
            session=RunSession.model_validate(payload["session"]),
            last_command=payload.get("last_command", "run-course"),
        )
