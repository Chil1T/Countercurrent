import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from server.app.main import create_app


class ArtifactsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_root = Path(self.temp_dir.name) / "out"
        self.course_id = "database-system-concepts-demo1234"
        course_dir = self.output_root / "courses" / self.course_id
        (course_dir / "chapters" / "chapter-01" / "notebooklm").mkdir(parents=True, exist_ok=True)
        (course_dir / "global").mkdir(parents=True, exist_ok=True)

        (course_dir / "course_blueprint.json").write_text(
            json.dumps({"course_id": self.course_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (course_dir / "runtime_state.json").write_text(
            json.dumps({"course_id": self.course_id, "last_error": None}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (course_dir / "runtime").mkdir(parents=True, exist_ok=True)
        (course_dir / "runtime" / "llm_calls.jsonl").write_text(
            '{"stage":"gap_fill","input_tokens":10,"output_tokens":20}\n',
            encoding="utf-8",
        )
        (course_dir / "chapters" / "chapter-01" / "notebooklm" / "01-精讲.md").write_text(
            "# Chapter 01\n\nKnowledge pack preview.",
            encoding="utf-8",
        )
        (course_dir / "chapters" / "chapter-01" / "review_report.json").write_text(
            json.dumps({"status": "warning", "issues": ["Need tighter definitions"]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (course_dir / "global" / "global_glossary.md").write_text(
            "# Glossary\n\n- tuple",
            encoding="utf-8",
        )

        self.client = TestClient(create_app(output_root=self.output_root))

    def _write_runtime_state(
        self,
        *,
        review_enabled: bool,
        chapters: dict[str, dict[str, object]],
        target_output: str = "interview_knowledge_base",
    ) -> None:
        course_dir = self.output_root / "courses" / self.course_id
        (course_dir / "course_blueprint.json").write_text(
            json.dumps(
                {
                    "course_id": self.course_id,
                    "chapters": [
                        {"chapter_id": chapter_id, "title": chapter_id}
                        for chapter_id in chapters
                    ],
                    "policy": {
                        "target_output": target_output,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (course_dir / "runtime_state.json").write_text(
            json.dumps(
                {
                    "course_id": self.course_id,
                    "run_identity": {
                        "review_enabled": review_enabled,
                        "target_output": target_output,
                    },
                    "chapters": chapters,
                    "last_error": None,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _archive_names(response) -> list[str]:
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        return sorted(archive.namelist())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_run_record(
        self,
        *,
        run_id: str,
        course_id: str,
        created_at: str,
        run_kind: str = "chapter",
    ) -> None:
        run_dir = self.output_root / "_gui" / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "session.json").write_text(
            json.dumps(
                {
                    "session": {
                        "id": run_id,
                        "draft_id": f"draft-{course_id}",
                        "course_id": course_id,
                        "created_at": created_at,
                        "status": "completed",
                        "run_kind": run_kind,
                        "backend": "heuristic",
                        "hosted": False,
                        "base_url": None,
                        "simple_model": None,
                        "complex_model": None,
                        "timeout_seconds": None,
                        "target_output": "interview_knowledge_base",
                        "review_enabled": False,
                        "review_mode": None,
                        "stages": [],
                        "chapter_progress": [],
                        "snapshot_complete": True,
                        "last_error": None,
                    },
                    "last_command": None,
                    "auto_resume_attempt_count": 0,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _write_snapshot_file(
        self,
        *,
        course_id: str,
        run_id: str,
        chapter_id: str,
        filename: str,
        content: str,
    ) -> None:
        snapshot_dir = (
            self.output_root
            / "_gui"
            / "results-snapshots"
            / course_id
            / run_id
            / "chapters"
            / chapter_id
            / "notebooklm"
        )
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        (snapshot_dir / filename).write_text(content, encoding="utf-8")

    def test_artifact_tree_lists_runtime_files(self) -> None:
        response = self.client.get(f"/courses/{self.course_id}/artifacts/tree")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["course_id"], self.course_id)
        paths = [node["path"] for node in payload["nodes"]]
        self.assertIn("course_blueprint.json", paths)
        self.assertIn("chapters/chapter-01/notebooklm/01-精讲.md", paths)
        self.assertIn("global/global_glossary.md", paths)
        self.assertNotIn("runtime/llm_calls.jsonl", paths)

    def test_artifact_content_returns_markdown_preview(self) -> None:
        response = self.client.get(
            f"/courses/{self.course_id}/artifacts/content",
            params={"path": "chapters/chapter-01/notebooklm/01-精讲.md"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["kind"], "markdown")
        self.assertIn("Knowledge pack preview.", payload["content"])

    def test_review_summary_aggregates_review_reports(self) -> None:
        response = self.client.get(f"/courses/{self.course_id}/review-summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["course_id"], self.course_id)
        self.assertEqual(payload["report_count"], 1)
        self.assertEqual(payload["issue_count"], 1)
        self.assertEqual(payload["reports"][0]["path"], "chapters/chapter-01/review_report.json")

    def test_artifact_content_hides_internal_llm_call_log(self) -> None:
        response = self.client.get(
            f"/courses/{self.course_id}/artifacts/content",
            params={"path": "runtime/llm_calls.jsonl"},
        )

        self.assertEqual(response.status_code, 404)

    def test_artifact_content_hides_internal_llm_call_log_after_path_normalization(self) -> None:
        response = self.client.get(
            f"/courses/{self.course_id}/artifacts/content",
            params={"path": "runtime/../runtime/llm_calls.jsonl"},
        )

        self.assertEqual(response.status_code, 404)

    def test_review_summary_accepts_structured_issue_objects(self) -> None:
        course_dir = self.output_root / "courses" / self.course_id
        (course_dir / "chapters" / "chapter-01" / "review_report.json").write_text(
            json.dumps(
                {
                    "status": "approved",
                    "issues": [
                        {
                            "severity": "medium",
                            "issue_type": "unsupported_expansion",
                            "location": "knowledge_pack.files.01-精讲.md",
                            "fix_hint": "Trim unsupported detail.",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        response = self.client.get(f"/courses/{self.course_id}/review-summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["report_count"], 1)
        self.assertEqual(payload["issue_count"], 1)
        self.assertEqual(payload["reports"][0]["issues"][0]["severity"], "medium")

    def test_global_results_snapshot_selects_latest_course_and_orders_runs_by_created_at(self) -> None:
        self._write_run_record(
            run_id="run-alpha-older",
            course_id="course-alpha",
            created_at="2026-04-02T08:00:00+00:00",
        )
        self._write_run_record(
            run_id="run-alpha-newer",
            course_id="course-alpha",
            created_at="2026-04-02T10:00:00+00:00",
        )
        self._write_run_record(
            run_id="run-beta-latest",
            course_id="course-beta",
            created_at="2026-04-02T12:00:00+00:00",
        )
        self._write_snapshot_file(
            course_id="course-alpha",
            run_id="run-alpha-older",
            chapter_id="chapter-01",
            filename="01-alpha-old.md",
            content="# Alpha old",
        )
        self._write_snapshot_file(
            course_id="course-alpha",
            run_id="run-alpha-newer",
            chapter_id="chapter-01",
            filename="01-alpha-new.md",
            content="# Alpha new",
        )
        self._write_snapshot_file(
            course_id="course-beta",
            run_id="run-beta-latest",
            chapter_id="chapter-01",
            filename="01-beta-latest.md",
            content="# Beta latest",
        )

        response = self.client.get("/results-snapshot")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["current_course_id"], "course-beta")
        self.assertEqual([run["run_id"] for run in payload["current_course_runs"]], ["run-beta-latest"])
        self.assertEqual([course["course_id"] for course in payload["historical_courses"]], ["course-alpha"])
        self.assertEqual(
            [run["run_id"] for run in payload["historical_courses"][0]["runs"]],
            ["run-alpha-newer", "run-alpha-older"],
        )

    def test_global_results_snapshot_content_reads_historical_course_markdown(self) -> None:
        self._write_run_record(
            run_id="run-history-001",
            course_id="course-history",
            created_at="2026-04-01T08:00:00+00:00",
        )
        self._write_snapshot_file(
            course_id="course-history",
            run_id="run-history-001",
            chapter_id="chapter-02",
            filename="01-history.md",
            content="# History course",
        )

        response = self.client.get(
            "/results-snapshot/content",
            params={
                "source_course_id": "course-history",
                "run_id": "run-history-001",
                "path": "chapters/chapter-02/notebooklm/01-history.md",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["path"], "chapters/chapter-02/notebooklm/01-history.md")
        self.assertIn("History course", payload["content"])

    def test_global_results_snapshot_content_rejects_snapshot_root_traversal(self) -> None:
        escape_root = self.output_root / "_gui" / "escape-course" / "escape-run"
        escape_root.mkdir(parents=True, exist_ok=True)
        secret_path = escape_root / "escaped.md"
        secret_path.write_text("top-secret", encoding="utf-8")

        response = self.client.get(
            "/results-snapshot/content",
            params={
                "source_course_id": "..\\escape-course",
                "run_id": "escape-run",
                "path": "escaped.md",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_global_results_snapshot_orders_runs_by_nested_session_created_at(self) -> None:
        self._write_run_record(
            run_id="run-current-latest",
            course_id="course-current",
            created_at="2026-04-01T12:00:00+00:00",
        )
        self._write_run_record(
            run_id="run-history-older",
            course_id="course-history",
            created_at="2026-04-01T08:00:00+00:00",
        )
        self._write_run_record(
            run_id="run-history-newer",
            course_id="course-history",
            created_at="2026-04-01T10:00:00+00:00",
        )
        self._write_snapshot_file(
            course_id="course-current",
            run_id="run-current-latest",
            chapter_id="chapter-01",
            filename="01-current.md",
            content="# current",
        )
        self._write_snapshot_file(
            course_id="course-history",
            run_id="run-history-older",
            chapter_id="chapter-01",
            filename="01-older.md",
            content="# older",
        )
        self._write_snapshot_file(
            course_id="course-history",
            run_id="run-history-newer",
            chapter_id="chapter-01",
            filename="01-newer.md",
            content="# newer",
        )
        older_snapshot = (
            self.output_root
            / "_gui"
            / "results-snapshots"
            / "course-history"
            / "run-history-older"
        )
        newer_snapshot = (
            self.output_root
            / "_gui"
            / "results-snapshots"
            / "course-history"
            / "run-history-newer"
        )
        older_snapshot.touch()
        newer_snapshot.touch()
        # Simulate a rewritten older snapshot directory whose filesystem mtime is newer
        older_snapshot.touch()

        response = self.client.get("/results-snapshot")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["current_course_id"], "course-current")
        historical = next(course for course in payload["historical_courses"] if course["course_id"] == "course-history")
        self.assertEqual(
            [run["run_id"] for run in historical["runs"]],
            ["run-history-newer", "run-history-older"],
        )

    def test_export_zip_streams_course_bundle(self) -> None:
        response = self.client.get(f"/courses/{self.course_id}/export")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertEqual(response.headers["cache-control"], "no-store, max-age=0")
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        self.assertIn(f"{self.course_id}/course_blueprint.json", archive.namelist())
        self.assertIn(
            f"{self.course_id}/chapters/chapter-01/notebooklm/01-精讲.md",
            archive.namelist(),
        )
        self.assertNotIn(
            f"{self.course_id}/runtime/llm_calls.jsonl",
            archive.namelist(),
        )

    def test_export_zip_supports_unicode_course_id_in_download_header(self) -> None:
        unicode_course_id = "数据结构概论-b4cd2e08"
        course_dir = self.output_root / "courses" / unicode_course_id
        course_dir.mkdir(parents=True, exist_ok=True)
        (course_dir / "course_blueprint.json").write_text(
            json.dumps({"course_id": unicode_course_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        response = self.client.get(f"/courses/{unicode_course_id}/export")

        self.assertEqual(response.status_code, 200)
        content_disposition = response.headers["content-disposition"]
        self.assertIn("attachment;", content_disposition)
        self.assertIn("filename*=UTF-8''", content_disposition)
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        self.assertIn(f"{unicode_course_id}/course_blueprint.json", archive.namelist())

    def test_export_zip_completed_chapters_only_uses_strict_export_ready_semantics(self) -> None:
        course_dir = self.output_root / "courses" / self.course_id
        (course_dir / "chapters" / "chapter-01" / "intermediate").mkdir(parents=True, exist_ok=True)
        (course_dir / "chapters" / "chapter-02" / "notebooklm").mkdir(parents=True, exist_ok=True)
        (course_dir / "chapters" / "chapter-02" / "intermediate").mkdir(parents=True, exist_ok=True)
        (course_dir / "chapters" / "chapter-01" / "intermediate" / "pack_plan.json").write_text(
            json.dumps({"status": "completed"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (course_dir / "chapters" / "chapter-02" / "notebooklm" / "02-精讲.md").write_text(
            "# Chapter 02\n\nPartial output.",
            encoding="utf-8",
        )
        (course_dir / "chapters" / "chapter-02" / "intermediate" / "pack_plan.json").write_text(
            json.dumps({"status": "partial"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._write_runtime_state(
            review_enabled=True,
            chapters={
                "chapter-01": {
                    "steps": {
                        "ingest": {"status": "completed"},
                        "curriculum_anchor": {"status": "completed"},
                        "gap_fill": {"status": "completed"},
                        "pack_plan": {"status": "completed"},
                        "write_lecture_note": {"status": "completed"},
                        "write_terms": {"status": "completed"},
                        "write_interview_qa": {"status": "completed"},
                        "write_cross_links": {"status": "completed"},
                        "review": {"status": "completed"},
                    }
                },
                "chapter-02": {
                    "steps": {
                        "ingest": {"status": "completed"},
                        "curriculum_anchor": {"status": "completed"},
                        "gap_fill": {"status": "completed"},
                        "pack_plan": {"status": "completed"},
                        "write_lecture_note": {"status": "completed"},
                        "write_terms": {"status": "completed"},
                        "write_interview_qa": {"status": "completed"},
                        "write_cross_links": {"status": "completed"},
                    }
                },
            },
        )

        response = self.client.get(
            f"/courses/{self.course_id}/export",
            params={"completed_chapters_only": "true"},
        )

        self.assertEqual(response.status_code, 200)
        archive_names = self._archive_names(response)
        self.assertIn(f"{self.course_id}/course_blueprint.json", archive_names)
        self.assertIn(f"{self.course_id}/chapters/chapter-01/notebooklm/01-精讲.md", archive_names)
        self.assertIn(f"{self.course_id}/chapters/chapter-01/intermediate/pack_plan.json", archive_names)
        self.assertNotIn(f"{self.course_id}/chapters/chapter-02/notebooklm/02-精讲.md", archive_names)
        self.assertNotIn(f"{self.course_id}/chapters/chapter-02/intermediate/pack_plan.json", archive_names)

    def test_export_zip_final_outputs_only_limits_archive_to_notebooklm_outputs(self) -> None:
        course_dir = self.output_root / "courses" / self.course_id
        (course_dir / "chapters" / "chapter-01" / "intermediate").mkdir(parents=True, exist_ok=True)
        (course_dir / "chapters" / "chapter-02" / "notebooklm").mkdir(parents=True, exist_ok=True)
        (course_dir / "chapters" / "chapter-02" / "intermediate").mkdir(parents=True, exist_ok=True)
        (course_dir / "chapters" / "chapter-01" / "intermediate" / "pack_plan.json").write_text(
            json.dumps({"status": "completed"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (course_dir / "chapters" / "chapter-02" / "notebooklm" / "02-精讲.md").write_text(
            "# Chapter 02\n\nPartial output.",
            encoding="utf-8",
        )
        (course_dir / "chapters" / "chapter-02" / "intermediate" / "pack_plan.json").write_text(
            json.dumps({"status": "partial"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        response = self.client.get(
            f"/courses/{self.course_id}/export",
            params={"final_outputs_only": "true"},
        )

        self.assertEqual(response.status_code, 200)
        archive_names = self._archive_names(response)
        self.assertEqual(
            archive_names,
            [
                f"{self.course_id}/chapters/chapter-01/notebooklm/01-精讲.md",
                f"{self.course_id}/chapters/chapter-02/notebooklm/02-精讲.md",
            ],
        )

    def test_export_zip_combines_completed_chapter_and_final_output_filters(self) -> None:
        course_dir = self.output_root / "courses" / self.course_id
        (course_dir / "chapters" / "chapter-02" / "notebooklm").mkdir(parents=True, exist_ok=True)
        (course_dir / "chapters" / "chapter-02" / "notebooklm" / "02-精讲.md").write_text(
            "# Chapter 02\n\nPartial output.",
            encoding="utf-8",
        )
        self._write_runtime_state(
            review_enabled=True,
            chapters={
                "chapter-01": {
                    "steps": {
                        "ingest": {"status": "completed"},
                        "curriculum_anchor": {"status": "completed"},
                        "gap_fill": {"status": "completed"},
                        "pack_plan": {"status": "completed"},
                        "write_lecture_note": {"status": "completed"},
                        "write_terms": {"status": "completed"},
                        "write_interview_qa": {"status": "completed"},
                        "write_cross_links": {"status": "completed"},
                        "review": {"status": "completed"},
                    }
                },
                "chapter-02": {
                    "steps": {
                        "ingest": {"status": "completed"},
                        "curriculum_anchor": {"status": "completed"},
                        "gap_fill": {"status": "completed"},
                        "pack_plan": {"status": "completed"},
                        "write_lecture_note": {"status": "completed"},
                        "write_terms": {"status": "completed"},
                        "write_interview_qa": {"status": "completed"},
                        "write_cross_links": {"status": "completed"},
                    }
                },
            },
        )

        response = self.client.get(
            f"/courses/{self.course_id}/export",
            params={
                "completed_chapters_only": "true",
                "final_outputs_only": "true",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._archive_names(response),
            [f"{self.course_id}/chapters/chapter-01/notebooklm/01-精讲.md"],
        )

    def test_results_snapshot_lists_current_and_historical_course_outputs(self) -> None:
        historical_course_id = "operating-systems-demo4321"
        current_snapshot = (
            self.output_root
            / "_gui"
            / "results-snapshots"
            / self.course_id
            / "run-current-001"
            / "chapters"
            / "chapter-01"
            / "notebooklm"
        )
        historical_snapshot = (
            self.output_root
            / "_gui"
            / "results-snapshots"
            / historical_course_id
            / "run-history-001"
            / "chapters"
            / "chapter-02"
            / "notebooklm"
        )
        current_snapshot.mkdir(parents=True, exist_ok=True)
        historical_snapshot.mkdir(parents=True, exist_ok=True)
        (current_snapshot / "01-精讲.md").write_text("# Current\n", encoding="utf-8")
        (historical_snapshot / "01-精讲.md").write_text("# Historical\n", encoding="utf-8")

        response = self.client.get(f"/courses/{self.course_id}/results-snapshot")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["current_course_id"], self.course_id)
        self.assertEqual(payload["current_course_runs"][0]["run_id"], "run-current-001")
        self.assertEqual(
            payload["current_course_runs"][0]["chapters"][0]["files"][0]["path"],
            "chapters/chapter-01/notebooklm/01-精讲.md",
        )
        self.assertEqual(payload["historical_courses"][0]["course_id"], historical_course_id)
        self.assertEqual(payload["historical_courses"][0]["runs"][0]["run_id"], "run-history-001")

    def test_results_snapshot_content_reads_historical_course_markdown(self) -> None:
        historical_course_id = "operating-systems-demo4321"
        historical_snapshot = (
            self.output_root
            / "_gui"
            / "results-snapshots"
            / historical_course_id
            / "run-history-001"
            / "chapters"
            / "chapter-02"
            / "notebooklm"
        )
        historical_snapshot.mkdir(parents=True, exist_ok=True)
        (historical_snapshot / "01-精讲.md").write_text("# Historical\n\nKnowledge pack.", encoding="utf-8")

        response = self.client.get(
            f"/courses/{self.course_id}/results-snapshot/content",
            params={
                "source_course_id": historical_course_id,
                "run_id": "run-history-001",
                "path": "chapters/chapter-02/notebooklm/01-精讲.md",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["path"], "chapters/chapter-02/notebooklm/01-精讲.md")
        self.assertEqual(payload["kind"], "markdown")
        self.assertIn("Knowledge pack.", payload["content"])
