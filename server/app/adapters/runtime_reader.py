from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeSnapshot:
    chapter_count: int
    completed_steps: dict[str, int]
    blueprint_ready: bool
    global_steps: dict[str, bool]
    last_error: str | None


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
        completed_steps = {
            "ingest": 0,
            "curriculum_anchor": 0,
            "gap_fill": 0,
            "pack_plan": 0,
            "write_lecture_note": 0,
            "write_terms": 0,
            "write_interview_qa": 0,
            "write_cross_links": 0,
            "write_open_questions": 0,
            "review": 0,
        }

        for chapter_state in runtime_chapters.values():
            steps = chapter_state.get("steps", {})
            for step_name in completed_steps:
                if steps.get(step_name, {}).get("status") == "completed":
                    completed_steps[step_name] += 1

        return RuntimeSnapshot(
            chapter_count=len(runtime_chapters),
            completed_steps=completed_steps,
            blueprint_ready=True,
            global_steps={
                "build_global_glossary": runtime.get("global", {}).get("build_global_glossary", {}).get("status") == "completed",
                "build_interview_index": runtime.get("global", {}).get("build_interview_index", {}).get("status") == "completed",
            },
            last_error=runtime.get("last_error"),
        )
