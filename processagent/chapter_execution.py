from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Callable


@dataclass(frozen=True)
class ChapterExecutionPlan:
    chapter_id: str
    transcript_file: Path
    chapter_blueprint: dict[str, Any]
    chapter_dir: Path
    intermediate_dir: Path
    notebooklm_dir: Path
    review_path: Path
    writer_names: tuple[str, ...]
    pending_steps: tuple[str, ...]
    review_enabled: bool


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
    def __init__(self, *, runner: Any, runtime_state_guard: RuntimeStateMutationGuard) -> None:
        self.runner = runner
        self.runtime_state_guard = runtime_state_guard

    def plan(self, *, transcript_file: Path, chapter_blueprint: dict[str, Any]) -> ChapterExecutionPlan:
        chapter_id = chapter_blueprint["chapter_id"]
        chapter_dir = self.runner.course_dir / "chapters" / chapter_id
        intermediate_dir = chapter_dir / "intermediate"
        notebooklm_dir = chapter_dir / "notebooklm"
        review_path = chapter_dir / "review_report.json"
        writer_names = self.runner._active_writer_names()

        pending_steps: list[str] = []
        upstream_invalidated = False

        for step_name, path, require_blueprint in self._step_specs(
            chapter_id=chapter_id,
            intermediate_dir=intermediate_dir,
            notebooklm_dir=notebooklm_dir,
            review_path=review_path,
            writer_names=writer_names,
        ):
            if upstream_invalidated or not self.runtime_state_guard.step_is_valid(
                scope=chapter_id,
                step_name=step_name,
                required_paths=(path,),
                require_blueprint=require_blueprint,
            ):
                pending_steps.append(step_name)
                upstream_invalidated = True

        return ChapterExecutionPlan(
            chapter_id=chapter_id,
            transcript_file=transcript_file,
            chapter_blueprint=chapter_blueprint,
            chapter_dir=chapter_dir,
            intermediate_dir=intermediate_dir,
            notebooklm_dir=notebooklm_dir,
            review_path=review_path,
            writer_names=writer_names,
            pending_steps=tuple(pending_steps),
            review_enabled=self.runner.config.enable_review,
        )

    def _step_specs(
        self,
        *,
        chapter_id: str,
        intermediate_dir: Path,
        notebooklm_dir: Path,
        review_path: Path,
        writer_names: tuple[str, ...],
    ) -> list[tuple[str, Path, bool]]:
        specs: list[tuple[str, Path, bool]] = [
            ("ingest", intermediate_dir / "normalized_transcript.json", False),
            ("curriculum_anchor", intermediate_dir / "topic_anchor_map.json", True),
            ("gap_fill", intermediate_dir / "augmentation_candidates.json", True),
            ("pack_plan", intermediate_dir / "pack_plan.json", True),
        ]
        for writer_name in writer_names:
            file_name = self.runner.pack_writer_files[writer_name]
            specs.append((writer_name, notebooklm_dir / file_name, True))
        if self.runner.config.enable_review:
            specs.append(("review", review_path, True))
        return specs


class ChapterWorker:
    def __init__(self, *, runner: Any, runtime_state_guard: RuntimeStateMutationGuard) -> None:
        self.runner = runner
        self.runtime_state_guard = runtime_state_guard

    def run(self, plan: ChapterExecutionPlan) -> None:
        plan.intermediate_dir.mkdir(parents=True, exist_ok=True)
        plan.notebooklm_dir.mkdir(parents=True, exist_ok=True)
        pending_steps = set(plan.pending_steps)

        normalized_path = plan.intermediate_dir / "normalized_transcript.json"
        if "ingest" in pending_steps:
            normalized = self.runner.ingest_agent.run(
                chapter_id=plan.chapter_id,
                transcript_text=plan.transcript_file.read_text(encoding="utf-8"),
            )
            self.runner._write_json(normalized_path, normalized)
            self.runtime_state_guard.mark_step_complete(plan.chapter_id, "ingest", require_blueprint=False)
        else:
            normalized = self._require_json(
                chapter_id=plan.chapter_id,
                step_name="ingest",
                path=normalized_path,
                require_blueprint=False,
            )

        topic_map_path = plan.intermediate_dir / "topic_anchor_map.json"
        if "curriculum_anchor" in pending_steps:
            topic_map = self.runner._run_agent(
                "curriculum_anchor",
                {
                    "course_blueprint": self.runner._slim_course_blueprint(),
                    "chapter_blueprint": plan.chapter_blueprint,
                    "normalized_transcript": normalized,
                },
                scope=plan.chapter_id,
            )
            self.runner._write_json(topic_map_path, topic_map)
            self.runtime_state_guard.mark_step_complete(plan.chapter_id, "curriculum_anchor")
        else:
            topic_map = self._require_json(
                chapter_id=plan.chapter_id,
                step_name="curriculum_anchor",
                path=topic_map_path,
            )

        augmentation_path = plan.intermediate_dir / "augmentation_candidates.json"
        if "gap_fill" in pending_steps:
            augmentation = self.runner._run_agent(
                "gap_fill",
                {
                    "course_blueprint": self.runner._slim_course_blueprint(),
                    "chapter_blueprint": plan.chapter_blueprint,
                    "normalized_transcript": normalized,
                    "topic_anchor_map": topic_map,
                },
                scope=plan.chapter_id,
            )
            self.runner._write_json(augmentation_path, augmentation)
            self.runtime_state_guard.mark_step_complete(plan.chapter_id, "gap_fill")
        else:
            augmentation = self._require_json(
                chapter_id=plan.chapter_id,
                step_name="gap_fill",
                path=augmentation_path,
            )

        pack_plan_payload = self.runner._build_pack_payload(
            chapter_blueprint=plan.chapter_blueprint,
            normalized=normalized,
            topic_map=topic_map,
            augmentation=augmentation,
        )
        pack_plan_path = plan.intermediate_dir / "pack_plan.json"
        if "pack_plan" in pending_steps:
            pack_plan = self.runner._run_agent("pack_plan", pack_plan_payload, scope=plan.chapter_id)
            self.runner._write_json(pack_plan_path, pack_plan)
            self.runtime_state_guard.mark_step_complete(plan.chapter_id, "pack_plan")
        else:
            pack_plan = self._require_json(
                chapter_id=plan.chapter_id,
                step_name="pack_plan",
                path=pack_plan_path,
            )

        pack_files: dict[str, str] = {}
        writer_payload = self.runner._build_writer_payload(
            chapter_blueprint=plan.chapter_blueprint,
            normalized=normalized,
            topic_map=topic_map,
            augmentation=augmentation,
            pack_plan=pack_plan,
        )
        for writer_name in plan.writer_names:
            file_name = self.runner.pack_writer_files[writer_name]
            output_path = plan.notebooklm_dir / file_name
            if writer_name in pending_steps:
                content = self.runner._run_text_agent(
                    writer_name,
                    writer_payload,
                    scope=plan.chapter_id,
                )
                output_path.write_text(content, encoding="utf-8")
                self.runtime_state_guard.mark_step_complete(plan.chapter_id, writer_name)
            else:
                content = self._require_text(
                    chapter_id=plan.chapter_id,
                    step_name=writer_name,
                    path=output_path,
                )
            pack_files[file_name] = content

        pack = {"files": pack_files}
        if plan.review_enabled:
            if "review" in pending_steps:
                review = self.runner._run_agent(
                    "review",
                    self.runner._build_review_payload(
                        chapter_blueprint=plan.chapter_blueprint,
                        normalized=normalized,
                        topic_map=topic_map,
                        augmentation=augmentation,
                        pack=pack,
                    ),
                    scope=plan.chapter_id,
                )
                self.runner._write_json(plan.review_path, review)
                self.runtime_state_guard.mark_step_complete(plan.chapter_id, "review")
            else:
                self._require_json(
                    chapter_id=plan.chapter_id,
                    step_name="review",
                    path=plan.review_path,
                )
        else:
            if plan.review_path.exists():
                plan.review_path.unlink()
            self.runtime_state_guard.clear_step_record(plan.chapter_id, "review")

    def _require_json(
        self,
        *,
        chapter_id: str,
        step_name: str,
        path: Path,
        require_blueprint: bool = True,
    ) -> dict[str, Any]:
        value = self.runtime_state_guard.load_step_json(
            chapter_id=chapter_id,
            step_name=step_name,
            path=path,
            require_blueprint=require_blueprint,
        )
        if value is None:
            raise RuntimeError(f"Missing checkpoint for {chapter_id}:{step_name}")
        return value

    def _require_text(
        self,
        *,
        chapter_id: str,
        step_name: str,
        path: Path,
        require_blueprint: bool = True,
    ) -> str:
        value = self.runtime_state_guard.load_step_text(
            chapter_id=chapter_id,
            step_name=step_name,
            path=path,
            require_blueprint=require_blueprint,
        )
        if value is None:
            raise RuntimeError(f"Missing checkpoint for {chapter_id}:{step_name}")
        return value
