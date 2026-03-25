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

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

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
