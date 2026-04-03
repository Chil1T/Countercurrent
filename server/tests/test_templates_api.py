import unittest
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from server.app.main import create_app


class TemplateApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_root = Path(self.temp_dir.name) / "out"
        self.gui_config_path = Path(self.temp_dir.name) / "gui-config.json"
        self.client = TestClient(create_app(output_root=self.output_root, gui_config_path=self.gui_config_path))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_list_templates_returns_default_presets(self) -> None:
        response = self.client.get("/templates")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([item["id"] for item in payload], [
            "standard-knowledge-pack",
            "lecture-deep-dive",
            "interview-focus",
        ])
        self.assertIn("01-精讲.md", payload[0]["expected_outputs"])

    def test_save_course_draft_config_persists_selected_template(self) -> None:
        create_response = self.client.post(
            "/course-drafts",
            json={"book_title": "Operating System Concepts"},
        )
        draft_id = create_response.json()["id"]

        response = self.client.post(
            f"/course-drafts/{draft_id}/config",
            json={
                "template_id": "lecture-deep-dive",
                "content_density": "dense",
                "review_mode": "light",
                "export_package": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["draft_id"], draft_id)
        self.assertEqual(payload["template"]["id"], "lecture-deep-dive")
        self.assertEqual(payload["content_density"], "dense")
        self.assertEqual(payload["review_mode"], "light")
        self.assertTrue(payload["export_package"])

    def test_gui_runtime_config_round_trips_provider_defaults(self) -> None:
        save_response = self.client.put(
            "/gui-runtime-config",
            json={
                "default_provider": "openai_compatible",
                "providers": {
                    "openai": {
                        "api_key": "sk-openai",
                        "base_url": "https://api.openai.com/v1",
                        "simple_model": "gpt-5.4-mini",
                        "complex_model": "gpt-5.4",
                        "timeout_seconds": 180,
                    },
                    "openai_compatible": {
                        "api_key": "sk-router",
                        "base_url": "https://openrouter.ai/api/v1",
                        "simple_model": "openai/gpt-4.1-mini",
                        "complex_model": "openai/gpt-4.1",
                        "timeout_seconds": 240,
                    },
                    "anthropic": {
                        "api_key": "sk-ant",
                        "base_url": "https://api.anthropic.com/v1",
                        "simple_model": "claude-3-5-haiku-latest",
                        "complex_model": "claude-sonnet-4-20250514",
                        "timeout_seconds": 300,
                    },
                },
            },
        )

        self.assertEqual(save_response.status_code, 200)
        payload = save_response.json()
        self.assertEqual(payload["default_provider"], "openai_compatible")
        self.assertEqual(payload["providers"]["openai_compatible"]["simple_model"], "openai/gpt-4.1-mini")

        get_response = self.client.get("/gui-runtime-config")

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["providers"]["anthropic"]["complex_model"], "claude-sonnet-4-20250514")

    def test_gui_runtime_config_rejects_invalid_provider_policy_values(self) -> None:
        invalid_payloads = (
            {
                "provider_policies": {
                    "openai": {
                        "max_call_attempts": 0,
                    }
                }
            },
            {
                "provider_policies": {
                    "openai": {
                        "max_call_attempts": True,
                    }
                }
            },
            {
                "provider_policies": {
                    "openai": {
                        "max_call_attempts": "2",
                    }
                }
            },
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.put(
                    "/gui-runtime-config",
                    json={
                        "default_provider": "openai",
                        "providers": {
                            "openai": {},
                            "openai_compatible": {},
                            "anthropic": {},
                        },
                        **payload,
                    },
                )

                self.assertEqual(response.status_code, 422)

    def test_save_course_draft_config_persists_runtime_overrides(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={"book_title": "Operating System Concepts"},
        ).json()["id"]

        response = self.client.post(
            f"/course-drafts/{draft_id}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "light",
                "review_mode": "light",
                "export_package": True,
                "provider": "anthropic",
                "base_url": "https://api.anthropic.com/v1",
                "simple_model": "claude-3-5-haiku-latest",
                "complex_model": "claude-sonnet-4-20250514",
                "timeout_seconds": 180,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["provider"], "anthropic")
        self.assertEqual(payload["base_url"], "https://api.anthropic.com/v1")
        self.assertEqual(payload["simple_model"], "claude-3-5-haiku-latest")
        self.assertEqual(payload["complex_model"], "claude-sonnet-4-20250514")
        self.assertEqual(payload["timeout_seconds"], 180)
