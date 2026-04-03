from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from server.app.adapters.runtime_reader import RuntimeStateReader, resolve_required_chapter_steps
from server.app.models.review_summary import ReviewIssueDetail, ReviewReportSummary, ReviewSummary


class ArtifactService:
    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root
        self._runtime_reader = RuntimeStateReader(output_root)
        self._results_snapshot_root = output_root / "_gui" / "results-snapshots"

    def list_tree(self, course_id: str) -> dict[str, object] | None:
        course_dir = self._course_dir(course_id)
        if not course_dir.exists():
            return None

        nodes = []
        for path in sorted(course_dir.rglob("*")):
            if path.is_dir():
                continue
            relative = path.relative_to(course_dir).as_posix()
            if not self._is_public_artifact(relative):
                continue
            nodes.append(
                {
                    "path": relative,
                    "kind": self._detect_kind(path),
                    "size": path.stat().st_size,
                }
            )
        return {"course_id": course_id, "nodes": nodes}

    def read_content(self, course_id: str, relative_path: str) -> dict[str, str] | None:
        course_dir = self._course_dir(course_id).resolve()
        path = self._safe_file_path(course_id, relative_path)
        if path is None or not path.exists() or path.is_dir():
            return None
        normalized_relative = path.relative_to(course_dir).as_posix()
        if not self._is_public_artifact(normalized_relative):
            return None

        return {
            "path": normalized_relative,
            "kind": self._detect_kind(path),
            "content": path.read_text(encoding="utf-8"),
        }

    def build_review_summary(self, course_id: str) -> ReviewSummary | None:
        course_dir = self._course_dir(course_id)
        if not course_dir.exists():
            return None

        reports: list[ReviewReportSummary] = []
        for report_path in sorted(course_dir.rglob("review_report.json")):
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            reports.append(
                ReviewReportSummary(
                    path=report_path.relative_to(course_dir).as_posix(),
                    status=payload.get("status", "unknown"),
                    issues=[self._normalize_issue(issue) for issue in payload.get("issues", [])],
                )
            )

        return ReviewSummary(
            course_id=course_id,
            report_count=len(reports),
            issue_count=sum(len(report.issues) for report in reports),
            reports=reports,
        )

    @staticmethod
    def _normalize_issue(issue: Any) -> str | ReviewIssueDetail:
        if isinstance(issue, str):
            return issue
        if isinstance(issue, dict):
            known_fields = {
                "severity": issue.get("severity"),
                "issue_type": issue.get("issue_type"),
                "location": issue.get("location"),
                "fix_hint": issue.get("fix_hint"),
            }
            extra = {
                key: value
                for key, value in issue.items()
                if key not in {"severity", "issue_type", "location", "fix_hint"}
            }
            return ReviewIssueDetail(
                **known_fields,
                detail=extra or None,
            )
        return str(issue)

    def export_zip(
        self,
        course_id: str,
        *,
        completed_chapters_only: bool = False,
        final_outputs_only: bool = False,
    ) -> tuple[str, bytes] | None:
        course_dir = self._course_dir(course_id)
        if not course_dir.exists():
            return None

        export_ready_chapters = self._export_ready_chapters(course_id) if completed_chapters_only else None
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(course_dir.rglob("*")):
                if path.is_dir():
                    continue
                relative = path.relative_to(course_dir).as_posix()
                if not self._is_public_artifact(relative):
                    continue
                if not self._should_export_path(
                    relative,
                    completed_chapters_only=completed_chapters_only,
                    final_outputs_only=final_outputs_only,
                    export_ready_chapters=export_ready_chapters,
                ):
                    continue
                archive.write(path, arcname=f"{course_id}/{relative}")
        return (f"{course_id}.zip", buffer.getvalue())

    def list_results_snapshot(self, course_id: str) -> dict[str, object]:
        current_course_runs = self._list_snapshot_runs(course_id)
        historical_courses = []
        if self._results_snapshot_root.exists():
            for course_root in sorted(
                (path for path in self._results_snapshot_root.iterdir() if path.is_dir()),
                key=lambda path: self._course_sort_key(path.name),
                reverse=True,
            ):
                if course_root.name == course_id:
                    continue
                historical_courses.append(
                    {
                        "course_id": course_root.name,
                        "runs": self._list_snapshot_runs(course_root.name),
                    }
                )
        return {
            "current_course_id": course_id,
            "current_course_runs": current_course_runs,
            "historical_courses": historical_courses,
        }

    def list_global_results_snapshot(self) -> dict[str, object]:
        if not self._results_snapshot_root.exists():
            return {
                "current_course_id": None,
                "current_course_runs": [],
                "historical_courses": [],
            }

        course_ids = [path.name for path in self._results_snapshot_root.iterdir() if path.is_dir()]
        if not course_ids:
            return {
                "current_course_id": None,
                "current_course_runs": [],
                "historical_courses": [],
            }

        sorted_course_ids = sorted(course_ids, key=self._course_sort_key, reverse=True)
        current_course_id = sorted_course_ids[0]
        return {
            "current_course_id": current_course_id,
            "current_course_runs": self._list_snapshot_runs(current_course_id),
            "historical_courses": [
                {
                    "course_id": course_id,
                    "runs": self._list_snapshot_runs(course_id),
                }
                for course_id in sorted_course_ids[1:]
            ],
        }

    def read_results_snapshot_content(self, *, source_course_id: str, run_id: str, relative_path: str) -> dict[str, str] | None:
        path = self._safe_snapshot_file_path(source_course_id, run_id, relative_path)
        if path is None or not path.exists() or path.is_dir():
            return None
        return {
            "path": relative_path,
            "kind": self._detect_kind(path),
            "content": path.read_text(encoding="utf-8"),
        }

    def _course_dir(self, course_id: str) -> Path:
        return self._output_root / "courses" / course_id

    def _snapshot_course_dir(self, course_id: str) -> Path:
        return self._results_snapshot_root / course_id

    def _snapshot_run_dir(self, course_id: str, run_id: str) -> Path:
        return self._snapshot_course_dir(course_id) / run_id

    def _safe_file_path(self, course_id: str, relative_path: str) -> Path | None:
        course_dir = self._course_dir(course_id).resolve()
        target = (course_dir / relative_path).resolve()
        if target == course_dir or course_dir not in target.parents:
            return None
        return target

    def _safe_snapshot_file_path(self, course_id: str, run_id: str, relative_path: str) -> Path | None:
        run_dir = self._snapshot_run_dir(course_id, run_id).resolve()
        if not run_dir.exists():
            return None
        target = (run_dir / relative_path).resolve()
        if target == run_dir or run_dir not in target.parents:
            return None
        return target

    def _list_snapshot_runs(self, course_id: str) -> list[dict[str, object]]:
        course_root = self._snapshot_course_dir(course_id)
        if not course_root.exists():
            return []
        runs: list[dict[str, object]] = []
        for run_root in sorted(
            (path for path in course_root.iterdir() if path.is_dir()),
            key=lambda path: self._run_sort_key(course_id, path.name),
            reverse=True,
        ):
            chapters: list[dict[str, object]] = []
            chapters_root = run_root / "chapters"
            if chapters_root.exists():
                for chapter_root in sorted((path for path in chapters_root.iterdir() if path.is_dir()), key=lambda path: path.name):
                    notebooklm_dir = chapter_root / "notebooklm"
                    files = []
                    if notebooklm_dir.exists():
                        for path in sorted(notebooklm_dir.glob("*.md"), key=lambda candidate: candidate.name):
                            files.append(
                                {
                                    "path": path.relative_to(run_root).as_posix(),
                                    "kind": self._detect_kind(path),
                                    "size": path.stat().st_size,
                                }
                            )
                    if files:
                        chapters.append(
                            {
                                "chapter_id": chapter_root.name,
                                "files": files,
                            }
                        )
            runs.append({"run_id": run_root.name, "chapters": chapters})
        return runs

    def _course_sort_key(self, course_id: str) -> tuple[float, str]:
        runs = self._snapshot_course_dir(course_id)
        if not runs.exists():
            return (0.0, course_id)
        run_ids = [path.name for path in runs.iterdir() if path.is_dir()]
        if not run_ids:
            return (0.0, course_id)
        latest_run_id = max(run_ids, key=lambda run_id: self._run_sort_key(course_id, run_id))
        latest_run_key = self._run_sort_key(course_id, latest_run_id)
        return (latest_run_key[0], course_id)

    def _run_sort_key(self, course_id: str, run_id: str) -> tuple[float, str]:
        session_path = self._output_root / "_gui" / "runs" / run_id / "session.json"
        if session_path.exists():
            try:
                payload = json.loads(session_path.read_text(encoding="utf-8"))
                created_at = payload.get("created_at")
                if isinstance(created_at, str):
                    return (datetime.fromisoformat(created_at).timestamp(), run_id)
            except (OSError, json.JSONDecodeError, ValueError):
                pass

        run_root = self._snapshot_run_dir(course_id, run_id)
        if run_root.exists():
            return (run_root.stat().st_mtime, run_id)
        return (0.0, run_id)

    @staticmethod
    def _is_public_artifact(relative_path: str) -> bool:
        return relative_path != "runtime/llm_calls.jsonl"

    def _export_ready_chapters(self, course_id: str) -> set[str]:
        runtime = self._runtime_reader.read(course_id)
        if runtime is None:
            return set()
        required_steps = resolve_required_chapter_steps(runtime.target_output, runtime.review_enabled)
        if not required_steps:
            return set()
        return {
            chapter_id
            for chapter_id, chapter_state in runtime.chapter_states.items()
            if all(chapter_state.steps.get(step_name, {}).get("status") == "completed" for step_name in required_steps)
        }

    @staticmethod
    def _should_export_path(
        relative_path: str,
        *,
        completed_chapters_only: bool,
        final_outputs_only: bool,
        export_ready_chapters: set[str] | None,
    ) -> bool:
        parts = PurePosixPath(relative_path).parts
        chapter_id = ArtifactService._chapter_id_from_parts(parts)
        if final_outputs_only:
            if len(parts) < 4 or parts[0] != "chapters" or parts[2] != "notebooklm":
                return False
        if completed_chapters_only and chapter_id is not None:
            return export_ready_chapters is not None and chapter_id in export_ready_chapters
        return not completed_chapters_only or chapter_id is None

    @staticmethod
    def _chapter_id_from_parts(parts: tuple[str, ...]) -> str | None:
        if len(parts) >= 2 and parts[0] == "chapters":
            return parts[1]
        return None

    @staticmethod
    def _detect_kind(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".md":
            return "markdown"
        if suffix == ".json":
            return "json"
        return "text"
