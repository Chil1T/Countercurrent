from __future__ import annotations

import copy
import json
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Mapping, Protocol


class ChapterExecutionRuntime(Protocol):
    course_dir: Path
    review_enabled: bool
    writer_names: tuple[str, ...]
    writer_file_map: Mapping[str, str]

    def slim_course_blueprint(self) -> dict[str, Any]: ...

    def ingest_transcript(self, chapter_id: str, transcript_text: str) -> dict[str, Any]: ...

    def run_json_stage(self, stage_name: str, payload: dict[str, Any], *, scope: str) -> dict[str, Any]: ...

    def run_text_stage(self, stage_name: str, payload: dict[str, Any], *, scope: str) -> str: ...

    def write_json(self, path: Path, data: dict[str, Any]) -> None: ...

    def build_pack_payload(
        self,
        *,
        chapter_blueprint: dict[str, Any],
        normalized: dict[str, Any],
        topic_map: dict[str, Any],
        augmentation: dict[str, Any],
    ) -> dict[str, Any]: ...

    def build_writer_payload(
        self,
        *,
        chapter_blueprint: dict[str, Any],
        normalized: dict[str, Any],
        topic_map: dict[str, Any],
        augmentation: dict[str, Any],
        pack_plan: dict[str, Any],
    ) -> dict[str, Any]: ...

    def build_review_payload(
        self,
        *,
        chapter_blueprint: dict[str, Any],
        normalized: dict[str, Any],
        topic_map: dict[str, Any],
        augmentation: dict[str, Any],
        pack: dict[str, Any],
    ) -> dict[str, Any]: ...

    def sync_run_snapshot(self, *, chapter_id: str, notebooklm_dir: Path) -> None: ...


@dataclass(frozen=True)
class ChapterStageDefinition:
    name: str
    stage_kind: str
    relative_path: tuple[str, ...]
    require_blueprint: bool = True


@dataclass(frozen=True)
class PlannedChapterStep:
    definition: ChapterStageDefinition
    path: Path
    should_run: bool


@dataclass(frozen=True)
class ChapterExecutionPlan:
    chapter_id: str
    transcript_file: Path
    chapter_blueprint: dict[str, Any]
    chapter_dir: Path
    intermediate_dir: Path
    notebooklm_dir: Path
    review_path: Path
    steps: tuple[PlannedChapterStep, ...]

    @property
    def pending_steps(self) -> tuple[str, ...]:
        return tuple(step.definition.name for step in self.steps if step.should_run)


class RuntimeStateMutationGuard:
    def __init__(
        self,
        *,
        runtime_state_path: Path,
        runtime_state: dict[str, Any],
        blueprint_hash: str,
        now_iso_factory: Callable[[], str],
        pipeline_signature: str = "pipeline-v4",
    ) -> None:
        self.runtime_state_path = runtime_state_path
        self.runtime_state = runtime_state
        self.blueprint_hash = blueprint_hash
        self.now_iso_factory = now_iso_factory
        self.pipeline_signature = pipeline_signature
        self._lock = Lock()

    def persist(self) -> None:
        with self._lock:
            self._write_runtime_state(self.runtime_state)

    def load_step_json(
        self,
        *,
        chapter_id: str,
        step_name: str,
        path: Path,
        require_blueprint: bool = True,
    ) -> dict[str, Any] | None:
        if not self.step_is_valid(
            scope=chapter_id,
            step_name=step_name,
            required_paths=(path,),
            require_blueprint=require_blueprint,
        ):
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_step_text(
        self,
        *,
        chapter_id: str,
        step_name: str,
        path: Path,
        require_blueprint: bool = True,
    ) -> str | None:
        if not self.step_is_valid(
            scope=chapter_id,
            step_name=step_name,
            required_paths=(path,),
            require_blueprint=require_blueprint,
        ):
            return None
        return path.read_text(encoding="utf-8")

    def step_is_valid(
        self,
        *,
        scope: str,
        step_name: str,
        required_paths: tuple[Path, ...],
        require_blueprint: bool,
    ) -> bool:
        record = self.get_step_record(scope, step_name)
        if record is None:
            return False
        if not all(path.exists() for path in required_paths):
            return False
        if record.get("pipeline_signature") != self.pipeline_signature:
            return False
        if require_blueprint and record.get("blueprint_hash") != self.blueprint_hash:
            return False
        return record.get("status") == "completed"

    def get_step_record(self, scope: str, step_name: str) -> dict[str, Any] | None:
        if scope == "global":
            return self.runtime_state.get("global", {}).get(step_name)
        return self.runtime_state.get("chapters", {}).get(scope, {}).get("steps", {}).get(step_name)

    def clear_step_record(self, scope: str, step_name: str) -> None:
        def mutate(state: dict[str, Any]) -> None:
            if scope == "global":
                state.setdefault("global", {}).pop(step_name, None)
            else:
                chapter_state = state.setdefault("chapters", {}).setdefault(scope, {"steps": {}})
                chapter_state.setdefault("steps", {}).pop(step_name, None)

        self._mutate(mutate)

    def mark_step_complete(self, scope: str, step_name: str, require_blueprint: bool = True) -> None:
        payload = {
            "status": "completed",
            "updated_at": self.now_iso_factory(),
            "blueprint_hash": self.blueprint_hash if require_blueprint else None,
            "pipeline_signature": self.pipeline_signature,
        }

        def mutate(state: dict[str, Any]) -> None:
            if scope == "global":
                state.setdefault("global", {})[step_name] = payload
            else:
                chapter_state = state.setdefault("chapters", {}).setdefault(scope, {"steps": {}})
                chapter_state.setdefault("steps", {})[step_name] = payload
            state["last_error"] = None

        self._mutate(mutate)

    def _mutate(self, mutator: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            state = self._load_latest_runtime_state()
            mutator(state)
            self._replace_runtime_state(state)
            self._write_runtime_state(self.runtime_state)

    def _load_latest_runtime_state(self) -> dict[str, Any]:
        if self.runtime_state_path.exists():
            return json.loads(self.runtime_state_path.read_text(encoding="utf-8"))
        return copy.deepcopy(self.runtime_state)

    def _replace_runtime_state(self, state: dict[str, Any]) -> None:
        self.runtime_state.clear()
        self.runtime_state.update(state)

    def _write_runtime_state(self, state: dict[str, Any]) -> None:
        self.runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.runtime_state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class ChapterExecutionPlanner:
    def __init__(self, *, runtime: ChapterExecutionRuntime, runtime_state_guard: RuntimeStateMutationGuard) -> None:
        self.runtime = runtime
        self.runtime_state_guard = runtime_state_guard

    def plan(self, *, transcript_file: Path, chapter_blueprint: dict[str, Any]) -> ChapterExecutionPlan:
        chapter_id = chapter_blueprint["chapter_id"]
        chapter_dir = self.runtime.course_dir / "chapters" / chapter_id
        intermediate_dir = chapter_dir / "intermediate"
        notebooklm_dir = chapter_dir / "notebooklm"
        review_path = chapter_dir / "review_report.json"

        steps: list[PlannedChapterStep] = []
        upstream_invalidated = False
        for definition in build_chapter_stage_definitions(
            writer_names=self.runtime.writer_names,
            writer_file_map=self.runtime.writer_file_map,
            review_enabled=self.runtime.review_enabled,
        ):
            path = chapter_dir.joinpath(*definition.relative_path)
            should_run = upstream_invalidated or not self.runtime_state_guard.step_is_valid(
                scope=chapter_id,
                step_name=definition.name,
                required_paths=(path,),
                require_blueprint=definition.require_blueprint,
            )
            steps.append(
                PlannedChapterStep(
                    definition=definition,
                    path=path,
                    should_run=should_run,
                )
            )
            if should_run:
                upstream_invalidated = True

        return ChapterExecutionPlan(
            chapter_id=chapter_id,
            transcript_file=transcript_file,
            chapter_blueprint=chapter_blueprint,
            chapter_dir=chapter_dir,
            intermediate_dir=intermediate_dir,
            notebooklm_dir=notebooklm_dir,
            review_path=review_path,
            steps=tuple(steps),
        )


class ChapterWorker:
    def __init__(self, *, runtime: ChapterExecutionRuntime, runtime_state_guard: RuntimeStateMutationGuard) -> None:
        self.runtime = runtime
        self.runtime_state_guard = runtime_state_guard

    def run(self, plan: ChapterExecutionPlan) -> None:
        plan.intermediate_dir.mkdir(parents=True, exist_ok=True)
        plan.notebooklm_dir.mkdir(parents=True, exist_ok=True)
        step_results: dict[str, Any] = {}

        for step in plan.steps:
            if step.should_run:
                result = self._execute_step(plan, step, step_results)
                self._persist_step_output(plan, step, result)
                self.runtime_state_guard.mark_step_complete(
                    plan.chapter_id,
                    step.definition.name,
                    require_blueprint=step.definition.require_blueprint,
                )
            else:
                result = self._load_completed_step(plan, step)
            step_results[step.definition.name] = result

        if not self.runtime.review_enabled:
            if plan.review_path.exists():
                plan.review_path.unlink()
            self.runtime_state_guard.clear_step_record(plan.chapter_id, "review")

        self.runtime.sync_run_snapshot(chapter_id=plan.chapter_id, notebooklm_dir=plan.notebooklm_dir)

    def _execute_step(
        self,
        plan: ChapterExecutionPlan,
        step: PlannedChapterStep,
        step_results: dict[str, Any],
    ) -> dict[str, Any] | str:
        name = step.definition.name
        if name == "ingest":
            return self.runtime.ingest_transcript(
                chapter_id=plan.chapter_id,
                transcript_text=plan.transcript_file.read_text(encoding="utf-8"),
            )
        if name == "curriculum_anchor":
            return self.runtime.run_json_stage(
                "curriculum_anchor",
                {
                    "course_blueprint": self.runtime.slim_course_blueprint(),
                    "chapter_blueprint": plan.chapter_blueprint,
                    "normalized_transcript": step_results["ingest"],
                },
                scope=plan.chapter_id,
            )
        if name == "gap_fill":
            return self.runtime.run_json_stage(
                "gap_fill",
                {
                    "course_blueprint": self.runtime.slim_course_blueprint(),
                    "chapter_blueprint": plan.chapter_blueprint,
                    "normalized_transcript": step_results["ingest"],
                    "topic_anchor_map": step_results["curriculum_anchor"],
                },
                scope=plan.chapter_id,
            )
        if name == "pack_plan":
            return self.runtime.run_json_stage(
                "pack_plan",
                self.runtime.build_pack_payload(
                    chapter_blueprint=plan.chapter_blueprint,
                    normalized=step_results["ingest"],
                    topic_map=step_results["curriculum_anchor"],
                    augmentation=step_results["gap_fill"],
                ),
                scope=plan.chapter_id,
            )
        if name in self.runtime.writer_names:
            return self.runtime.run_text_stage(
                name,
                self.runtime.build_writer_payload(
                    chapter_blueprint=plan.chapter_blueprint,
                    normalized=step_results["ingest"],
                    topic_map=step_results["curriculum_anchor"],
                    augmentation=step_results["gap_fill"],
                    pack_plan=step_results["pack_plan"],
                ),
                scope=plan.chapter_id,
            )
        if name == "review":
            return self.runtime.run_json_stage(
                "review",
                self.runtime.build_review_payload(
                    chapter_blueprint=plan.chapter_blueprint,
                    normalized=step_results["ingest"],
                    topic_map=step_results["curriculum_anchor"],
                    augmentation=step_results["gap_fill"],
                    pack=self._build_pack(step_results),
                ),
                scope=plan.chapter_id,
            )
        raise KeyError(f"Unsupported chapter step: {name}")

    def _persist_step_output(
        self,
        plan: ChapterExecutionPlan,
        step: PlannedChapterStep,
        result: dict[str, Any] | str,
    ) -> None:
        if step.definition.stage_kind in {"ingest", "json", "review"}:
            if not isinstance(result, dict):
                raise TypeError(f"Expected JSON result for step {step.definition.name}")
            self.runtime.write_json(step.path, result)
            return
        if not isinstance(result, str):
            raise TypeError(f"Expected text result for step {step.definition.name}")
        step.path.parent.mkdir(parents=True, exist_ok=True)
        step.path.write_text(result, encoding="utf-8")

    def _load_completed_step(
        self,
        plan: ChapterExecutionPlan,
        step: PlannedChapterStep,
    ) -> dict[str, Any] | str:
        if step.definition.stage_kind in {"ingest", "json", "review"}:
            value = self.runtime_state_guard.load_step_json(
                chapter_id=plan.chapter_id,
                step_name=step.definition.name,
                path=step.path,
                require_blueprint=step.definition.require_blueprint,
            )
        else:
            value = self.runtime_state_guard.load_step_text(
                chapter_id=plan.chapter_id,
                step_name=step.definition.name,
                path=step.path,
                require_blueprint=step.definition.require_blueprint,
            )
        if value is None:
            raise RuntimeError(f"Missing checkpoint for {plan.chapter_id}:{step.definition.name}")
        return value

    def _build_pack(self, step_results: dict[str, Any]) -> dict[str, Any]:
        files = {
            self.runtime.writer_file_map[writer_name]: step_results[writer_name]
            for writer_name in self.runtime.writer_names
            if writer_name in step_results
        }
        return {"files": files}


class ChapterExecutionScheduler:
    def __init__(self, *, worker: ChapterWorker, max_concurrent_chapters: int) -> None:
        self.worker = worker
        self.max_concurrent_chapters = max(1, max_concurrent_chapters)

    def run(self, plans: tuple[ChapterExecutionPlan, ...]) -> None:
        if not plans:
            return
        if self.max_concurrent_chapters == 1 or len(plans) == 1:
            for plan in plans:
                self.worker.run(plan)
            return

        executor = ThreadPoolExecutor(max_workers=self.max_concurrent_chapters)
        futures = [executor.submit(self.worker.run, plan) for plan in plans]
        try:
            done, pending = wait(futures, return_when=FIRST_EXCEPTION)
            for future in done:
                error = future.exception()
                if error is not None:
                    for pending_future in pending:
                        pending_future.cancel()
                    raise error
            for future in pending:
                future.result()
        finally:
            executor.shutdown(wait=True, cancel_futures=True)


def build_chapter_stage_definitions(
    *,
    writer_names: tuple[str, ...],
    writer_file_map: Mapping[str, str],
    review_enabled: bool,
) -> tuple[ChapterStageDefinition, ...]:
    definitions = [
        ChapterStageDefinition(
            name="ingest",
            stage_kind="ingest",
            relative_path=("intermediate", "normalized_transcript.json"),
            require_blueprint=False,
        ),
        ChapterStageDefinition(
            name="curriculum_anchor",
            stage_kind="json",
            relative_path=("intermediate", "topic_anchor_map.json"),
        ),
        ChapterStageDefinition(
            name="gap_fill",
            stage_kind="json",
            relative_path=("intermediate", "augmentation_candidates.json"),
        ),
        ChapterStageDefinition(
            name="pack_plan",
            stage_kind="json",
            relative_path=("intermediate", "pack_plan.json"),
        ),
    ]
    for writer_name in writer_names:
        definitions.append(
            ChapterStageDefinition(
                name=writer_name,
                stage_kind="writer",
                relative_path=("notebooklm", writer_file_map[writer_name]),
            )
        )
    if review_enabled:
        definitions.append(
            ChapterStageDefinition(
                name="review",
                stage_kind="review",
                relative_path=("review_report.json",),
            )
        )
    return tuple(definitions)
