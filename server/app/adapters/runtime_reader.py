from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from processagent.pipeline import WRITER_STAGE_SETS

CHAPTER_BASE_STEPS = (
    "ingest",
    "curriculum_anchor",
    "gap_fill",
    "pack_plan",
)
OPTIONAL_CHAPTER_STEPS = (
    "write_lecture_note",
    "write_terms",
    "write_interview_qa",
    "write_cross_links",
    "write_open_questions",
    "review",
)


@dataclass(frozen=True)
class ChapterRuntimeSnapshot:
    chapter_id: str
    steps: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class RuntimeSnapshot:
    chapter_count: int
    completed_steps: dict[str, int]
    blueprint_ready: bool
    global_steps: dict[str, bool]
    last_error: dict[str, Any] | str | None
    last_error_kind: str | None
    chapter_states: dict[str, ChapterRuntimeSnapshot]
    target_output: str | None
    review_enabled: bool


class RuntimeStateReader:
    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root

    def read(self, course_id: str) -> RuntimeSnapshot | None:
        course_dir = self._output_root / "courses" / course_id
        blueprint_path = course_dir / "course_blueprint.json"
        runtime_path = course_dir / "runtime_state.json"
        if not blueprint_path.exists() or not runtime_path.exists():
            return None

        blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        runtime_chapters = runtime.get("chapters", {})
        run_identity = runtime.get("run_identity", {})
        target_output = run_identity.get("target_output") or blueprint.get("policy", {}).get("target_output")
        review_enabled = bool(run_identity.get("review_enabled", False))
        writer_steps = WRITER_STAGE_SETS.get(target_output or "interview_knowledge_base", WRITER_STAGE_SETS["interview_knowledge_base"])
        tracked_steps = (*CHAPTER_BASE_STEPS, *writer_steps)
        if review_enabled:
            tracked_steps = (*tracked_steps, "review")
        completed_steps = {step_name: 0 for step_name in (*CHAPTER_BASE_STEPS, *OPTIONAL_CHAPTER_STEPS)}
        chapter_states: dict[str, ChapterRuntimeSnapshot] = {}

        ordered_chapter_ids = self._ordered_chapter_ids(blueprint, runtime_chapters)
        for chapter_id in ordered_chapter_ids:
            chapter_state = runtime_chapters.get(chapter_id, {})
            steps = chapter_state.get("steps", {})
            normalized_steps = {
                step_name: dict(step_payload)
                for step_name, step_payload in steps.items()
                if isinstance(step_payload, dict)
            }
            chapter_states[chapter_id] = ChapterRuntimeSnapshot(chapter_id=chapter_id, steps=normalized_steps)
            for step_name in tracked_steps:
                if normalized_steps.get(step_name, {}).get("status") == "completed":
                    completed_steps[step_name] = completed_steps.get(step_name, 0) + 1

        last_error = runtime.get("last_error")
        last_error_kind = self._resolve_last_error_kind(last_error, chapter_states)
        return RuntimeSnapshot(
            chapter_count=len(ordered_chapter_ids),
            completed_steps=completed_steps,
            blueprint_ready=True,
            global_steps={
                "build_global_glossary": runtime.get("global", {}).get("build_global_glossary", {}).get("status") == "completed",
                "build_interview_index": runtime.get("global", {}).get("build_interview_index", {}).get("status") == "completed",
            },
            last_error=last_error,
            last_error_kind=last_error_kind,
            chapter_states=chapter_states,
            target_output=target_output,
            review_enabled=review_enabled,
        )

    @staticmethod
    def _ordered_chapter_ids(blueprint: dict[str, Any], runtime_chapters: dict[str, Any]) -> list[str]:
        ordered = [
            chapter.get("chapter_id")
            for chapter in blueprint.get("chapters", [])
            if isinstance(chapter, dict) and chapter.get("chapter_id")
        ]
        for chapter_id in runtime_chapters:
            if chapter_id not in ordered:
                ordered.append(chapter_id)
        return ordered

    @staticmethod
    def _resolve_last_error_kind(
        last_error: dict[str, Any] | str | None,
        chapter_states: dict[str, ChapterRuntimeSnapshot],
    ) -> str | None:
        if isinstance(last_error, dict):
            kind = last_error.get("last_error_kind")
            if kind:
                return str(kind)
            scope = last_error.get("scope")
            step = last_error.get("step")
            if scope and step:
                return chapter_states.get(str(scope), ChapterRuntimeSnapshot(chapter_id=str(scope), steps={})).steps.get(
                    str(step),
                    {},
                ).get("last_error_kind")
        return None
