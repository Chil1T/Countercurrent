import tempfile
import unittest
from pathlib import Path
import io

from fastapi.testclient import TestClient

from server.app.main import create_app
from processagent.blueprint import build_course_id


class CourseDraftApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_root = Path(self.temp_dir.name) / "out"
        self.client = TestClient(create_app(output_root=self.output_root))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_course_draft_returns_detected_summary(self) -> None:
        response = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Database System Concepts",
                "course_url": "https://example.com/courses/db-101",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["book_title"], "Database System Concepts")
        self.assertEqual(payload["course_url"], "https://example.com/courses/db-101")
        self.assertEqual(payload["course_id"], build_course_id("Database System Concepts"))
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(payload["detected"]["textbook_title"], "Database System Concepts")
        self.assertEqual(payload["detected"]["course_name"], "Database System Concepts")
        self.assertEqual(payload["detected"]["asset_completeness"], 40)
        self.assertEqual([slot["kind"] for slot in payload["input_slots"]], [
            "course_link",
            "subtitle",
            "audio_video",
            "courseware",
            "textbook",
        ])
        self.assertTrue(payload["input_slots"][0]["supported"])
        self.assertFalse(payload["input_slots"][2]["supported"])

    def test_create_course_draft_normalizes_book_title_before_deriving_course_id(self) -> None:
        response = self.client.post(
            "/course-drafts",
            json={
                "book_title": "  Database System Concepts  ",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["book_title"], "Database System Concepts")
        self.assertEqual(payload["detected"]["course_name"], "Database System Concepts")
        self.assertEqual(payload["course_id"], build_course_id("Database System Concepts"))

    def test_create_course_draft_rejects_blank_book_title(self) -> None:
        response = self.client.post(
            "/course-drafts",
            json={
                "book_title": "   ",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_get_course_draft_returns_saved_draft(self) -> None:
        create_response = self.client.post(
            "/course-drafts",
            json={"book_title": "Distributed Systems"},
        )
        draft_id = create_response.json()["id"]

        response = self.client.get(f"/course-drafts/{draft_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], draft_id)
        self.assertEqual(payload["book_title"], "Distributed Systems")
        self.assertIsNone(payload["course_url"])

    def test_get_course_draft_includes_saved_config(self) -> None:
        create_response = self.client.post(
            "/course-drafts",
            json={"book_title": "Distributed Systems"},
        )
        draft_id = create_response.json()["id"]

        save_response = self.client.post(
            f"/course-drafts/{draft_id}/config",
            json={
                "template_id": "lecture-deep-dive",
                "content_density": "dense",
                "review_mode": "standard",
                "export_package": True,
            },
        )
        self.assertEqual(save_response.status_code, 200)

        response = self.client.get(f"/course-drafts/{draft_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["config"]["draft_id"], draft_id)
        self.assertEqual(payload["config"]["template"]["id"], "lecture-deep-dive")
        self.assertEqual(payload["config"]["content_density"], "dense")
        self.assertEqual(payload["config"]["review_mode"], "standard")
        self.assertTrue(payload["config"]["export_package"])

    def test_get_course_draft_restores_saved_draft_after_service_restart(self) -> None:
        create_response = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Reliable and Secure Systems",
                "course_url": "https://example.com/reliable-systems",
                "subtitle_assets": [
                    {
                        "filename": "chapter-01.md",
                        "content": "# 第1章\n\n系统可靠性导论。",
                    }
                ],
            },
        )
        draft_id = create_response.json()["id"]
        self.client.post(
            f"/course-drafts/{draft_id}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "dense",
                "review_mode": "standard",
                "export_package": True,
            },
        )

        restarted_client = TestClient(create_app(output_root=self.output_root))
        response = restarted_client.get(f"/course-drafts/{draft_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], draft_id)
        self.assertEqual(payload["book_title"], "Reliable and Secure Systems")
        self.assertTrue(payload["runtime_ready"])
        self.assertEqual(payload["config"]["template"]["id"], "interview-focus")

    def test_create_course_draft_persists_subtitle_input_for_runtime(self) -> None:
        response = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Database Internals",
                "subtitle_text": "# 第1章 关系模型\n\n本节介绍关系模型与范式。",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["runtime_ready"])
        self.assertEqual(payload["detected"]["asset_completeness"], 60)
        subtitle_slot = next(slot for slot in payload["input_slots"] if slot["kind"] == "subtitle")
        self.assertEqual(subtitle_slot["count"], 1)

        subtitle_path = (
            self.output_root
            / "_gui"
            / "drafts"
            / payload["id"]
            / "input"
            / "chapter-01.md"
        )
        self.assertTrue(subtitle_path.exists())
        self.assertIn("关系模型", subtitle_path.read_text(encoding="utf-8"))

    def test_create_course_draft_persists_multiple_subtitle_assets(self) -> None:
        response = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Distributed Systems",
                "subtitle_assets": [
                    {
                        "filename": "chapter-01-intro.md",
                        "content": "# 第1章 导论\n\n介绍系统模型。",
                    },
                    {
                        "filename": "chapter-02-clock.md",
                        "content": "# 第2章 时钟\n\n介绍逻辑时钟。",
                    },
                ],
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["runtime_ready"])
        subtitle_slot = next(slot for slot in payload["input_slots"] if slot["kind"] == "subtitle")
        self.assertEqual(subtitle_slot["count"], 2)

        input_dir = self.output_root / "_gui" / "drafts" / payload["id"] / "input"
        self.assertTrue((input_dir / "chapter-01-intro.md").exists())
        self.assertTrue((input_dir / "chapter-02-clock.md").exists())

    def test_create_course_draft_rejects_duplicate_subtitle_filenames_after_normalization(self) -> None:
        response = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Distributed Systems",
                "subtitle_assets": [
                    {
                        "filename": "week1/chapter-01.md",
                        "content": "# 第1章 导论\n\n介绍系统模型。",
                    },
                    {
                        "filename": "chapter-01.md",
                        "content": "# 第1章 补充\n\n重复文件名。",
                    },
                ],
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("Duplicate subtitle filename", response.json()["detail"])

    def test_create_course_draft_accepts_multipart_subtitle_uploads(self) -> None:
        response = self.client.post(
            "/course-drafts",
            data={
                "book_title": "Operating Systems",
                "course_url": "https://example.com/os",
            },
            files=[
                ("subtitle_files", ("chapter-01-process.md", io.BytesIO("# 第1章 进程\n\n介绍进程抽象。".encode("utf-8")), "text/markdown")),
                ("subtitle_files", ("chapter-02-thread.md", io.BytesIO("# 第2章 线程\n\n介绍线程与调度。".encode("utf-8")), "text/markdown")),
            ],
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["runtime_ready"])
        self.assertEqual(payload["detected"]["chapter_count"], 2)
        subtitle_slot = next(slot for slot in payload["input_slots"] if slot["kind"] == "subtitle")
        self.assertEqual(subtitle_slot["count"], 2)
        input_dir = self.output_root / "_gui" / "drafts" / payload["id"] / "input"
        self.assertTrue((input_dir / "chapter-01-process.md").exists())
        self.assertTrue((input_dir / "chapter-02-thread.md").exists())
