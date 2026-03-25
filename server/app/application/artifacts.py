from __future__ import annotations

import io
import json
import zipfile
from typing import Any
from pathlib import Path

from server.app.models.review_summary import ReviewIssueDetail, ReviewReportSummary, ReviewSummary


class ArtifactService:
    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root

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
        if not self._is_public_artifact(relative_path):
            return None
        path = self._safe_file_path(course_id, relative_path)
        if path is None or not path.exists() or path.is_dir():
            return None

        return {
            "path": relative_path,
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

    def export_zip(self, course_id: str) -> tuple[str, bytes] | None:
        course_dir = self._course_dir(course_id)
        if not course_dir.exists():
            return None

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(course_dir.rglob("*")):
                if path.is_dir():
                    continue
                relative = path.relative_to(course_dir).as_posix()
                if not self._is_public_artifact(relative):
                    continue
                archive.write(path, arcname=f"{course_id}/{relative}")
        return (f"{course_id}.zip", buffer.getvalue())

    def _course_dir(self, course_id: str) -> Path:
        return self._output_root / "courses" / course_id

    def _safe_file_path(self, course_id: str, relative_path: str) -> Path | None:
        course_dir = self._course_dir(course_id).resolve()
        target = (course_dir / relative_path).resolve()
        if target == course_dir or course_dir not in target.parents:
            return None
        return target

    @staticmethod
    def _is_public_artifact(relative_path: str) -> bool:
        return relative_path != "runtime/llm_calls.jsonl"

    @staticmethod
    def _detect_kind(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".md":
            return "markdown"
        if suffix == ".json":
            return "json"
        return "text"
