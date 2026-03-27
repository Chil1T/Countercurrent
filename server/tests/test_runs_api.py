import json
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from server.app.main import create_app
from processagent.blueprint import build_course_id
from server.app.adapters.gui_config_store import GuiConfigStore
from server.app.adapters.input_storage import DraftInputStorage
from server.app.adapters.runtime_reader import RuntimeStateReader
from server.app.application.course_drafts import CourseDraftService
from server.app.application.runs import RunService


class StubRunner:
    def __init__(self) -> None:
        self.started_specs: list[dict[str, str]] = []
        self.snapshots: dict[str, dict[str, str | None]] = {}

    def start(self, spec):
        self.started_specs.append(
            {
                "run_id": spec.run_id,
                "command": spec.command,
                "book_title": spec.book_title,
                "input_dir": str(spec.input_dir),
                "output_dir": str(spec.output_dir),
                "backend": spec.backend,
                "base_url": spec.base_url or "",
                "model": spec.model or "",
                "simple_model": spec.simple_model or "",
                "complex_model": spec.complex_model or "",
                "timeout_seconds": str(spec.timeout_seconds or ""),
                "max_concurrent_per_run": str(getattr(spec, "max_concurrent_per_run", "") or ""),
                "max_concurrent_global": str(getattr(spec, "max_concurrent_global", "") or ""),
                "max_call_attempts": str(getattr(spec, "max_call_attempts", "") or ""),
                "max_resume_attempts": str(getattr(spec, "max_resume_attempts", "") or ""),
                "env_overrides": json.dumps(spec.env_overrides or {}, ensure_ascii=False, sort_keys=True),
                "review_enabled": str(bool(getattr(spec, "review_enabled", False))).lower(),
                "review_mode": spec.review_mode or "",
                "target_output": spec.target_output or "",
            }
        )
        default_status = "completed" if spec.command == "clean-course" else "running"
        self.snapshots[spec.run_id] = {"status": default_status, "last_error": None}

    def snapshot(self, run_id: str):
        return self.snapshots.get(run_id)


class SlowStubRunner(StubRunner):
    def __init__(self, delay_seconds: float = 0.1) -> None:
        super().__init__()
        self.delay_seconds = delay_seconds

    def start(self, spec):
        time.sleep(self.delay_seconds)
        super().start(spec)


class RunsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_root = Path(self.temp_dir.name) / "out"
        self.gui_config_path = Path(self.temp_dir.name) / "gui-config.json"
        self.runner = StubRunner()
        self.client = TestClient(
            create_app(output_root=self.output_root, run_runner=self.runner, gui_config_path=self.gui_config_path)
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _configure_openai_runtime(self, max_resume_attempts: int = 2) -> None:
        self.client.put(
            "/gui-runtime-config",
            json={
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "api_key": "sk-openai",
                        "base_url": "https://api.openai.com/v1",
                        "simple_model": "gpt-5.4-mini",
                        "complex_model": "gpt-5.4",
                        "timeout_seconds": 180,
                    },
                    "openai_compatible": {},
                    "anthropic": {},
                },
                "provider_policies": {
                    "openai": {
                        "max_concurrent_per_run": 2,
                        "max_concurrent_global": 7,
                        "max_call_attempts": 3,
                        "max_resume_attempts": max_resume_attempts,
                    }
                },
            },
        )

    def _write_runtime_files(
        self,
        *,
        course_id: str,
        course_name: str,
        chapters: dict[str, dict[str, object]],
        last_error: dict[str, object] | None = None,
        global_steps: dict[str, dict[str, object]] | None = None,
    ) -> None:
        course_dir = self.output_root / "courses" / course_id
        course_dir.mkdir(parents=True, exist_ok=True)
        (course_dir / "course_blueprint.json").write_text(
            json.dumps(
                {
                    "course_id": course_id,
                    "course_name": course_name,
                    "blueprint_hash": "hash",
                    "chapters": [
                        {"chapter_id": chapter_id, "title": chapter_id}
                        for chapter_id in chapters
                    ],
                    "policy": {
                        "target_output": "interview_knowledge_base",
                        "review_mode": "standard",
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
                    "course_id": course_id,
                    "blueprint_hash": "hash",
                    "run_identity": {
                        "review_enabled": False,
                        "review_mode": "standard",
                        "target_output": "interview_knowledge_base",
                    },
                    "chapters": chapters,
                    "global": global_steps or {},
                    "last_error": last_error,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def test_create_run_returns_conflict_when_draft_is_not_runtime_ready(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={"book_title": "Computer Networks"},
        ).json()["id"]

        response = self.client.post("/runs", json={"draft_id": draft_id})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Course draft is not ready to run")

    def test_create_run_starts_runner_for_runtime_ready_draft(self) -> None:
        draft_response = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        )
        draft_payload = draft_response.json()

        response = self.client.post("/runs", json={"draft_id": draft_payload["id"]})

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["draft_id"], draft_payload["id"])
        self.assertEqual(payload["course_id"], build_course_id("Computer Networks"))
        self.assertEqual(payload["status"], "running")
        self.assertEqual(payload["target_output"], "interview_knowledge_base")
        self.assertEqual([stage["name"] for stage in payload["stages"]], [
            "build_blueprint",
            "ingest",
            "curriculum_anchor",
            "gap_fill",
            "pack_plan",
            "write_lecture_note",
            "write_terms",
            "write_interview_qa",
            "write_cross_links",
        ])
        self.assertEqual(self.runner.started_specs[0]["command"], "run-course")
        self.assertEqual(self.runner.started_specs[0]["backend"], "heuristic")
        self.assertEqual(self.runner.started_specs[0]["model"], "")
        self.assertEqual(self.runner.started_specs[0]["review_enabled"], "false")
        self.assertEqual(self.runner.started_specs[0]["review_mode"], "")
        self.assertEqual(self.runner.started_specs[0]["target_output"], "interview_knowledge_base")
        self.assertTrue(self.runner.started_specs[0]["input_dir"].endswith(f"{draft_payload['id']}\\input"))

    def test_create_run_rejects_parallel_run_for_same_course_output(self) -> None:
        first_draft = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()
        second_draft = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第2章 传输层\n\n本节介绍端到端通信。",
            },
        ).json()

        first_response = self.client.post("/runs", json={"draft_id": first_draft["id"]})
        second_response = self.client.post("/runs", json={"draft_id": second_draft["id"]})

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 409)
        self.assertIn("already in progress", second_response.json()["detail"])
        self.assertEqual(len(self.runner.started_specs), 1)

    def test_create_run_maps_saved_template_config_into_runner_spec(self) -> None:
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()
        self.client.post(
            f"/course-drafts/{draft_payload['id']}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "light",
                "review_mode": "standard",
                "export_package": True,
            },
        )

        response = self.client.post("/runs", json={"draft_id": draft_payload["id"]})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.runner.started_specs[-1]["review_mode"], "")
        self.assertEqual(self.runner.started_specs[-1]["review_enabled"], "false")
        self.assertEqual(self.runner.started_specs[-1]["target_output"], "interview_knowledge_base")

    def test_create_run_uses_course_default_review_enabled(self) -> None:
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()
        self.client.post(
            f"/course-drafts/{draft_payload['id']}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "light",
                "review_mode": "standard",
                "review_enabled": True,
                "export_package": True,
            },
        )

        response = self.client.post("/runs", json={"draft_id": draft_payload["id"]})

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertIn("review", [stage["name"] for stage in payload["stages"]])
        self.assertEqual(self.runner.started_specs[-1]["review_enabled"], "true")
        self.assertEqual(self.runner.started_specs[-1]["review_mode"], "standard")

    def test_create_run_allows_per_run_review_override(self) -> None:
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()
        self.client.post(
            f"/course-drafts/{draft_payload['id']}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "light",
                "review_mode": "standard",
                "review_enabled": False,
                "export_package": True,
            },
        )

        response = self.client.post("/runs", json={"draft_id": draft_payload["id"], "review_enabled": True})

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["review_enabled"])
        self.assertEqual(self.runner.started_specs[-1]["review_enabled"], "true")
        self.assertEqual(self.runner.started_specs[-1]["review_mode"], "standard")

    def test_create_global_run_uses_manual_consolidation_stage_track(self) -> None:
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()

        response = self.client.post("/runs", json={"draft_id": draft_payload["id"], "run_kind": "global"})

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["run_kind"], "global")
        self.assertEqual([stage["name"] for stage in payload["stages"]], [
            "build_global_glossary",
            "build_interview_index",
        ])
        self.assertEqual(self.runner.started_specs[-1]["command"], "build-global")

    def test_create_run_uses_global_hosted_backend_defaults(self) -> None:
        self.client.put(
            "/gui-runtime-config",
            json={
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "api_key": "sk-openai",
                        "base_url": "https://api.openai.com/v1",
                        "simple_model": "gpt-5.4-mini",
                        "complex_model": "gpt-5.4",
                        "timeout_seconds": 180,
                    },
                    "openai_compatible": {},
                    "anthropic": {},
                },
            },
        )
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()
        self.client.post(
            f"/course-drafts/{draft_payload['id']}/config",
            json={
                "template_id": "standard-knowledge-pack",
                "content_density": "balanced",
                "review_mode": "light",
                "export_package": True,
            },
        )

        response = self.client.post("/runs", json={"draft_id": draft_payload["id"]})

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["backend"], "openai")
        self.assertTrue(payload["hosted"])
        self.assertEqual(payload["base_url"], "https://api.openai.com/v1/responses")
        self.assertEqual(payload["simple_model"], "gpt-5.4-mini")
        self.assertEqual(payload["complex_model"], "gpt-5.4")
        self.assertEqual(self.runner.started_specs[-1]["backend"], "openai")
        self.assertEqual(self.runner.started_specs[-1]["base_url"], "https://api.openai.com/v1/responses")
        self.assertEqual(self.runner.started_specs[-1]["model"], "gpt-5.4")
        self.assertEqual(self.runner.started_specs[-1]["simple_model"], "gpt-5.4-mini")
        self.assertEqual(self.runner.started_specs[-1]["complex_model"], "gpt-5.4")
        self.assertEqual(self.runner.started_specs[-1]["timeout_seconds"], "180")
        self.assertIn("OPENAI_API_KEY", self.runner.started_specs[-1]["env_overrides"])

    def test_create_run_passes_gui_provider_policy_defaults_into_runner_spec(self) -> None:
        self.client.put(
            "/gui-runtime-config",
            json={
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "api_key": "sk-openai",
                        "base_url": "https://api.openai.com/v1",
                        "simple_model": "gpt-5.4-mini",
                        "complex_model": "gpt-5.4",
                        "timeout_seconds": 180,
                    },
                    "openai_compatible": {},
                    "anthropic": {},
                },
                "provider_policies": {
                    "openai": {
                        "max_concurrent_per_run": 2,
                        "max_concurrent_global": 7,
                        "max_call_attempts": 4,
                        "max_resume_attempts": 3,
                    }
                },
            },
        )
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()

        response = self.client.post("/runs", json={"draft_id": draft_payload["id"]})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.runner.started_specs[-1]["backend"], "openai")
        self.assertEqual(self.runner.started_specs[-1]["max_concurrent_per_run"], "2")
        self.assertEqual(self.runner.started_specs[-1]["max_concurrent_global"], "7")
        self.assertEqual(self.runner.started_specs[-1]["max_call_attempts"], "4")
        self.assertEqual(self.runner.started_specs[-1]["max_resume_attempts"], "3")

    def test_create_run_prefers_course_level_provider_override(self) -> None:
        self.client.put(
            "/gui-runtime-config",
            json={
                "default_provider": "openai",
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
                        "base_url": "https://openrouter.ai/api/v1/chat/completions",
                        "simple_model": "openai/gpt-4.1-mini",
                        "complex_model": "openai/gpt-4.1",
                        "timeout_seconds": 240,
                    },
                    "anthropic": {},
                },
            },
        )
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()
        self.client.post(
            f"/course-drafts/{draft_payload['id']}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "light",
                "review_mode": "standard",
                "export_package": True,
                "provider": "openai_compatible",
                "base_url": "https://openrouter.ai/api/v1/chat/completions",
                "simple_model": "openai/gpt-4.1-mini",
                "complex_model": "openai/gpt-4.1",
                "timeout_seconds": 240,
            },
        )

        response = self.client.post("/runs", json={"draft_id": draft_payload["id"]})

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["backend"], "openai_compatible")
        self.assertEqual(payload["base_url"], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(payload["simple_model"], "openai/gpt-4.1-mini")
        self.assertEqual(payload["complex_model"], "openai/gpt-4.1")
        self.assertEqual(self.runner.started_specs[-1]["backend"], "openai_compatible")
        self.assertIn("OPENAI_COMPATIBLE_API_KEY", self.runner.started_specs[-1]["env_overrides"])

    def test_create_run_rejects_hosted_backend_without_api_key(self) -> None:
        self.client.put(
            "/gui-runtime-config",
            json={
                "default_provider": "anthropic",
                "providers": {
                    "openai": {},
                    "openai_compatible": {},
                    "anthropic": {
                        "api_key": "",
                        "base_url": "https://api.anthropic.com/v1",
                        "simple_model": "claude-3-5-haiku-latest",
                        "complex_model": "claude-sonnet-4-20250514",
                        "timeout_seconds": 180,
                    },
                },
            },
        )
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()

        response = self.client.post("/runs", json={"draft_id": draft_payload["id"]})

        self.assertEqual(response.status_code, 409)
        self.assertIn("API key", response.json()["detail"])

    def test_create_run_rejects_invalid_hosted_base_url_before_starting_runner(self) -> None:
        self.client.put(
            "/gui-runtime-config",
            json={
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "api_key": "sk-openai",
                        "base_url": "notaurl",
                        "simple_model": "gpt-5.4-mini",
                        "complex_model": "gpt-5.4",
                        "timeout_seconds": 180,
                    },
                    "openai_compatible": {},
                    "anthropic": {},
                },
            },
        )
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()

        response = self.client.post("/runs", json={"draft_id": draft_payload["id"]})

        self.assertEqual(response.status_code, 409)
        self.assertIn("Invalid --base-url", response.json()["detail"])
        self.assertEqual(len(self.runner.started_specs), 0)

    def test_get_run_refreshes_stage_status_from_runtime_state(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Organization",
                "subtitle_text": "# 第1章 数据表示\n\n本节介绍二进制编码。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]

        course_dir = self.output_root / "courses" / course_id
        course_dir.mkdir(parents=True, exist_ok=True)
        (course_dir / "course_blueprint.json").write_text(
            json.dumps(
                {
                    "course_id": course_id,
                    "course_name": "Computer Organization",
                    "chapters": [
                        {"chapter_id": "chapter-01", "title": "chapter-01"},
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (course_dir / "runtime_state.json").write_text(
            json.dumps(
                {
                    "course_id": course_id,
                    "chapters": {
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
                                "write_open_questions": {"status": "completed"},
                                "review": {"status": "completed"},
                            }
                        }
                    },
                    "global": {
                        "build_global_glossary": {"status": "completed"},
                        "build_interview_index": {"status": "completed"},
                    },
                    "last_error": None,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.runner.snapshots[run_id] = {"status": "completed", "last_error": None}

        response = self.client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], run_id)
        self.assertEqual(payload["draft_id"], draft_id)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["course_id"], course_id)
        self.assertEqual([stage["status"] for stage in payload["stages"]], [
            "completed",
            "completed",
            "completed",
            "completed",
            "completed",
            "completed",
            "completed",
            "completed",
            "completed",
        ])

    def test_get_run_auto_resumes_transient_failure_when_resume_budget_remains(self) -> None:
        self._configure_openai_runtime(max_resume_attempts=2)
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Distributed Systems",
                "subtitle_text": "# 第1章 概览\n\n本节介绍系统故障与恢复。",
            },
        ).json()
        self.client.post(
            f"/course-drafts/{draft_payload['id']}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "balanced",
                "review_mode": "standard",
                "export_package": True,
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "simple_model": "gpt-5.4-mini",
                "complex_model": "gpt-5.4",
                "timeout_seconds": 180,
            },
        )
        run_payload = self.client.post("/runs", json={"draft_id": draft_payload["id"]}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]
        self._write_runtime_files(
            course_id=course_id,
            course_name="Distributed Systems",
            chapters={
                "chapter-01": {
                    "steps": {
                        "ingest": {"status": "completed"},
                        "curriculum_anchor": {
                            "status": "failed",
                            "attempt_count": 3,
                            "last_error_kind": "http_status:429",
                            "retry_history": [
                                {"attempt": 1, "status": "error", "error_kind": "http_status:429", "will_retry": True},
                                {"attempt": 2, "status": "error", "error_kind": "http_status:429", "will_retry": True},
                                {"attempt": 3, "status": "error", "error_kind": "http_status:429", "will_retry": False},
                            ],
                        },
                    }
                }
            },
            last_error={"scope": "chapter-01", "step": "curriculum_anchor", "last_error_kind": "http_status:429"},
        )
        self.runner.snapshots[run_id] = {"status": "failed", "last_error": "provider overloaded"}

        response = self.client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "running")
        self.assertEqual(self.runner.started_specs[-1]["command"], "resume-course")
        self.assertEqual(len(self.runner.started_specs), 2)

    def test_get_run_does_not_auto_resume_permanent_failure(self) -> None:
        self._configure_openai_runtime(max_resume_attempts=2)
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Distributed Systems",
                "subtitle_text": "# 第1章 概览\n\n本节介绍系统故障与恢复。",
            },
        ).json()
        self.client.post(
            f"/course-drafts/{draft_payload['id']}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "balanced",
                "review_mode": "standard",
                "export_package": True,
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "simple_model": "gpt-5.4-mini",
                "complex_model": "gpt-5.4",
                "timeout_seconds": 180,
            },
        )
        run_payload = self.client.post("/runs", json={"draft_id": draft_payload["id"]}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]
        self._write_runtime_files(
            course_id=course_id,
            course_name="Distributed Systems",
            chapters={
                "chapter-01": {
                    "steps": {
                        "ingest": {"status": "completed"},
                        "curriculum_anchor": {
                            "status": "failed",
                            "attempt_count": 1,
                            "last_error_kind": "http_status:400",
                            "retry_history": [
                                {"attempt": 1, "status": "error", "error_kind": "http_status:400", "will_retry": False},
                            ],
                        },
                    }
                }
            },
            last_error={"scope": "chapter-01", "step": "curriculum_anchor", "last_error_kind": "http_status:400"},
        )
        self.runner.snapshots[run_id] = {"status": "failed", "last_error": "bad request"}

        response = self.client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(len(self.runner.started_specs), 1)

    def test_get_run_returns_failed_without_auto_resume_when_provider_config_is_missing_after_restart(self) -> None:
        self._configure_openai_runtime(max_resume_attempts=2)
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Distributed Systems",
                "subtitle_text": "# 第1章 概览\n\n本节介绍系统故障与恢复。",
            },
        ).json()
        self.client.post(
            f"/course-drafts/{draft_payload['id']}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "balanced",
                "review_mode": "standard",
                "export_package": True,
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "simple_model": "gpt-5.4-mini",
                "complex_model": "gpt-5.4",
                "timeout_seconds": 180,
            },
        )
        run_payload = self.client.post("/runs", json={"draft_id": draft_payload["id"]}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]
        self._write_runtime_files(
            course_id=course_id,
            course_name="Distributed Systems",
            chapters={
                "chapter-01": {
                    "steps": {
                        "ingest": {"status": "completed"},
                        "curriculum_anchor": {
                            "status": "failed",
                            "attempt_count": 3,
                            "last_error_kind": "http_status:429",
                            "retry_history": [
                                {"attempt": 1, "status": "error", "error_kind": "http_status:429", "will_retry": True},
                                {"attempt": 2, "status": "error", "error_kind": "http_status:429", "will_retry": True},
                                {"attempt": 3, "status": "error", "error_kind": "http_status:429", "will_retry": False},
                            ],
                        },
                    }
                }
            },
            last_error={"scope": "chapter-01", "step": "curriculum_anchor", "last_error_kind": "http_status:429"},
        )
        self.client.put(
            "/gui-runtime-config",
            json={
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "api_key": "",
                        "base_url": "https://api.openai.com/v1",
                        "simple_model": "gpt-5.4-mini",
                        "complex_model": "gpt-5.4",
                        "timeout_seconds": 180,
                    },
                    "openai_compatible": {},
                    "anthropic": {},
                },
                "provider_policies": {
                    "openai": {
                        "max_concurrent_per_run": 2,
                        "max_concurrent_global": 7,
                        "max_call_attempts": 3,
                        "max_resume_attempts": 2,
                    }
                },
            },
        )

        restarted_runner = StubRunner()
        restarted_client = TestClient(
            create_app(output_root=self.output_root, run_runner=restarted_runner, gui_config_path=self.gui_config_path)
        )

        response = restarted_client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(restarted_runner.started_specs, [])

    def test_get_run_exposes_multi_chapter_progress_while_keeping_legacy_stage_track(self) -> None:
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Operating Systems",
                "subtitle_text": "# 第1章 进程\n\n本节介绍进程与线程。",
            },
        ).json()
        run_payload = self.client.post("/runs", json={"draft_id": draft_payload["id"]}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]
        self._write_runtime_files(
            course_id=course_id,
            course_name="Operating Systems",
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
                    }
                },
                "chapter-02": {
                    "steps": {
                        "ingest": {"status": "completed"},
                        "curriculum_anchor": {"status": "running"},
                    }
                },
            },
        )
        self.runner.snapshots[run_id] = {"status": "running", "last_error": None}

        response = self.client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "running")
        self.assertIn("stages", payload)
        self.assertEqual([stage["name"] for stage in payload["stages"]], [
            "build_blueprint",
            "ingest",
            "curriculum_anchor",
            "gap_fill",
            "pack_plan",
            "write_lecture_note",
            "write_terms",
            "write_interview_qa",
            "write_cross_links",
        ])
        self.assertEqual(payload["chapter_progress"], [
            {
                "chapter_id": "chapter-01",
                "status": "completed",
                "current_step": None,
                "completed_step_count": 8,
                "total_step_count": 8,
                "export_ready": True,
            },
            {
                "chapter_id": "chapter-02",
                "status": "running",
                "current_step": "curriculum_anchor",
                "completed_step_count": 1,
                "total_step_count": 8,
                "export_ready": False,
            },
        ])

    def test_get_run_keeps_stage_aggregate_aligned_with_blueprint_chapter_population(self) -> None:
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Operating Systems",
                "subtitle_text": "# 第1章 进程\n\n本节介绍进程与线程。",
            },
        ).json()
        run_payload = self.client.post("/runs", json={"draft_id": draft_payload["id"]}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]
        course_dir = self.output_root / "courses" / course_id
        course_dir.mkdir(parents=True, exist_ok=True)
        (course_dir / "course_blueprint.json").write_text(
            json.dumps(
                {
                    "course_id": course_id,
                    "course_name": "Operating Systems",
                    "blueprint_hash": "hash",
                    "chapters": [
                        {"chapter_id": "chapter-01", "title": "chapter-01"},
                        {"chapter_id": "chapter-02", "title": "chapter-02"},
                    ],
                    "policy": {
                        "target_output": "interview_knowledge_base",
                        "review_mode": "standard",
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
                    "course_id": course_id,
                    "blueprint_hash": "hash",
                    "run_identity": {
                        "review_enabled": False,
                        "review_mode": "standard",
                        "target_output": "interview_knowledge_base",
                    },
                    "chapters": {
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
                            }
                        }
                    },
                    "global": {},
                    "last_error": None,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.runner.snapshots[run_id] = {"status": "running", "last_error": None}

        response = self.client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        stage_statuses = {stage["name"]: stage["status"] for stage in payload["stages"]}
        self.assertEqual(stage_statuses["build_blueprint"], "completed")
        self.assertEqual(stage_statuses["ingest"], "running")
        self.assertEqual(stage_statuses["curriculum_anchor"], "running")
        self.assertEqual(stage_statuses["gap_fill"], "running")
        self.assertEqual(stage_statuses["pack_plan"], "running")
        self.assertEqual(stage_statuses["write_lecture_note"], "running")
        self.assertEqual(stage_statuses["write_terms"], "running")
        self.assertEqual(stage_statuses["write_interview_qa"], "running")
        self.assertEqual(stage_statuses["write_cross_links"], "running")
        self.assertEqual(payload["chapter_progress"], [
            {
                "chapter_id": "chapter-01",
                "status": "completed",
                "current_step": None,
                "completed_step_count": 8,
                "total_step_count": 8,
                "export_ready": True,
            },
            {
                "chapter_id": "chapter-02",
                "status": "running",
                "current_step": "ingest",
                "completed_step_count": 0,
                "total_step_count": 8,
                "export_ready": False,
            },
        ])

    def test_get_run_stops_auto_resume_when_resume_budget_is_exhausted_after_restart(self) -> None:
        self._configure_openai_runtime(max_resume_attempts=1)
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Distributed Systems",
                "subtitle_text": "# 第1章 概览\n\n本节介绍系统故障与恢复。",
            },
        ).json()
        self.client.post(
            f"/course-drafts/{draft_payload['id']}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "balanced",
                "review_mode": "standard",
                "export_package": True,
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "simple_model": "gpt-5.4-mini",
                "complex_model": "gpt-5.4",
                "timeout_seconds": 180,
            },
        )
        run_payload = self.client.post("/runs", json={"draft_id": draft_payload["id"]}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]
        failed_runtime = {
            "chapter-01": {
                "steps": {
                    "ingest": {"status": "completed"},
                    "curriculum_anchor": {
                        "status": "failed",
                        "attempt_count": 3,
                        "last_error_kind": "network:timeout",
                        "retry_history": [
                            {"attempt": 1, "status": "error", "error_kind": "network:timeout", "will_retry": True},
                            {"attempt": 2, "status": "error", "error_kind": "network:timeout", "will_retry": True},
                            {"attempt": 3, "status": "error", "error_kind": "network:timeout", "will_retry": False},
                        ],
                    },
                }
            }
        }
        last_error = {"scope": "chapter-01", "step": "curriculum_anchor", "last_error_kind": "network:timeout"}
        self._write_runtime_files(
            course_id=course_id,
            course_name="Distributed Systems",
            chapters=failed_runtime,
            last_error=last_error,
        )
        self.runner.snapshots[run_id] = {"status": "failed", "last_error": "timed out"}

        first_response = self.client.get(f"/runs/{run_id}")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_response.json()["status"], "running")
        self.assertEqual(self.runner.started_specs[-1]["command"], "resume-course")

        self._write_runtime_files(
            course_id=course_id,
            course_name="Distributed Systems",
            chapters=failed_runtime,
            last_error=last_error,
        )
        self.runner.snapshots[run_id] = {"status": "failed", "last_error": "timed out again"}

        restarted_runner = StubRunner()
        restarted_client = TestClient(
            create_app(output_root=self.output_root, run_runner=restarted_runner, gui_config_path=self.gui_config_path)
        )

        response = restarted_client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(restarted_runner.started_specs, [])

    def test_get_run_stops_auto_resume_when_resume_budget_is_exhausted(self) -> None:
        self._configure_openai_runtime(max_resume_attempts=1)
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Distributed Systems",
                "subtitle_text": "# 第1章 概览\n\n本节介绍系统故障与恢复。",
            },
        ).json()
        self.client.post(
            f"/course-drafts/{draft_payload['id']}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "balanced",
                "review_mode": "standard",
                "export_package": True,
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "simple_model": "gpt-5.4-mini",
                "complex_model": "gpt-5.4",
                "timeout_seconds": 180,
            },
        )
        run_payload = self.client.post("/runs", json={"draft_id": draft_payload["id"]}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]
        failed_runtime = {
            "chapter-01": {
                "steps": {
                    "ingest": {"status": "completed"},
                    "curriculum_anchor": {
                        "status": "failed",
                        "attempt_count": 3,
                        "last_error_kind": "http_status:429",
                        "retry_history": [
                            {"attempt": 1, "status": "error", "error_kind": "http_status:429", "will_retry": True},
                            {"attempt": 2, "status": "error", "error_kind": "http_status:429", "will_retry": True},
                            {"attempt": 3, "status": "error", "error_kind": "http_status:429", "will_retry": False},
                        ],
                    },
                }
            }
        }
        last_error = {"scope": "chapter-01", "step": "curriculum_anchor", "last_error_kind": "http_status:429"}
        self._write_runtime_files(
            course_id=course_id,
            course_name="Distributed Systems",
            chapters=failed_runtime,
            last_error=last_error,
        )
        self.runner.snapshots[run_id] = {"status": "failed", "last_error": "provider overloaded"}

        first_response = self.client.get(f"/runs/{run_id}")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_response.json()["status"], "running")
        self.assertEqual(self.runner.started_specs[-1]["command"], "resume-course")

        self._write_runtime_files(
            course_id=course_id,
            course_name="Distributed Systems",
            chapters=failed_runtime,
            last_error=last_error,
        )
        self.runner.snapshots[run_id] = {"status": "failed", "last_error": "provider overloaded again"}

        response = self.client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "failed")
        self.assertEqual(len(self.runner.started_specs), 2)

    def test_resume_run_restarts_runner_with_resume_command(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        self.runner.snapshots[run_id] = {
            "status": "failed",
            "last_error": "pipeline interrupted",
        }

        response = self.client.post(f"/runs/{run_id}/resume")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], run_id)
        self.assertEqual(payload["status"], "running")
        self.assertEqual(self.runner.started_specs[-1]["command"], "resume-course")

    def test_resume_run_restores_persisted_record_before_restarting_runner(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        self.runner.snapshots[run_id] = {
            "status": "failed",
            "last_error": "pipeline interrupted",
        }

        replacement_runner = StubRunner()
        restart_client = TestClient(
            create_app(output_root=self.output_root, run_runner=replacement_runner, gui_config_path=self.gui_config_path)
        )

        response = restart_client.post(f"/runs/{run_id}/resume")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], run_id)
        self.assertEqual(replacement_runner.started_specs[-1]["command"], "resume-course")

    def test_get_run_log_restores_persisted_record_and_process_log_after_restart(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]

        log_path = self.output_root / "_gui" / "runs" / run_id / "process.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("line one\nline two\n", encoding="utf-8")

        restart_client = TestClient(
            create_app(output_root=self.output_root, run_runner=StubRunner(), gui_config_path=self.gui_config_path)
        )

        response = restart_client.get(f"/runs/{run_id}/log")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["content"], "line one\nline two\n")
        self.assertEqual(payload["cursor"], len("line one\nline two\n"))

    def test_resume_run_refreshes_provider_routing_but_keeps_frozen_pipeline_identity(self) -> None:
        self.client.put(
            "/gui-runtime-config",
            json={
                "default_provider": "openai",
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
                        "base_url": "https://openrouter.ai/api/v1/chat/completions",
                        "simple_model": "openai/gpt-4.1-mini",
                        "complex_model": "openai/gpt-4.1",
                        "timeout_seconds": 240,
                    },
                    "anthropic": {},
                },
                "provider_policies": {
                    "openai": {
                        "max_concurrent_per_run": 2,
                        "max_concurrent_global": 7,
                        "max_call_attempts": 4,
                        "max_resume_attempts": 3,
                    }
                },
            },
        )
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        self.client.post(
            f"/course-drafts/{draft_id}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "light",
                "review_mode": "standard",
                "review_enabled": True,
                "export_package": True,
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "simple_model": "gpt-5.4-mini",
                "complex_model": "gpt-5.4",
                "timeout_seconds": 180,
            },
        )
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        self.runner.snapshots[run_id] = {
            "status": "failed",
            "last_error": "pipeline interrupted",
        }
        self.client.put(
            "/gui-runtime-config",
            json={
                "default_provider": "openai",
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
                        "base_url": "https://openrouter.ai/api/v1/chat/completions",
                        "simple_model": "openai/gpt-4.1-mini",
                        "complex_model": "openai/gpt-4.1",
                        "timeout_seconds": 240,
                    },
                    "anthropic": {},
                },
                "provider_policies": {
                    "openai_compatible": {
                        "max_concurrent_per_run": 5,
                        "max_concurrent_global": 9,
                        "max_call_attempts": 6,
                        "max_resume_attempts": 4,
                    }
                },
            },
        )
        self.client.post(
            f"/course-drafts/{draft_id}/config",
            json={
                "template_id": "lecture-deep-dive",
                "content_density": "dense",
                "review_mode": "light",
                "review_enabled": False,
                "export_package": True,
                "provider": "openai_compatible",
                "base_url": "https://openrouter.ai/api/v1/chat/completions",
                "simple_model": "openai/gpt-4.1-mini",
                "complex_model": "openai/gpt-4.1",
                "timeout_seconds": 240,
            },
        )

        response = self.client.post(f"/runs/{run_id}/resume")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["backend"], "openai_compatible")
        self.assertEqual(payload["base_url"], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(payload["simple_model"], "openai/gpt-4.1-mini")
        self.assertEqual(payload["complex_model"], "openai/gpt-4.1")
        self.assertTrue(payload["review_enabled"])
        self.assertEqual(payload["review_mode"], "standard")
        self.assertEqual(payload["target_output"], "interview_knowledge_base")
        self.assertEqual(self.runner.started_specs[-1]["backend"], "openai_compatible")
        self.assertEqual(
            self.runner.started_specs[-1]["base_url"],
            "https://openrouter.ai/api/v1/chat/completions",
        )
        self.assertEqual(self.runner.started_specs[-1]["simple_model"], "openai/gpt-4.1-mini")
        self.assertEqual(self.runner.started_specs[-1]["complex_model"], "openai/gpt-4.1")
        self.assertEqual(self.runner.started_specs[-1]["max_concurrent_per_run"], "5")
        self.assertEqual(self.runner.started_specs[-1]["max_concurrent_global"], "9")
        self.assertEqual(self.runner.started_specs[-1]["max_call_attempts"], "6")
        self.assertEqual(self.runner.started_specs[-1]["max_resume_attempts"], "4")
        self.assertEqual(self.runner.started_specs[-1]["review_enabled"], "true")
        self.assertEqual(self.runner.started_specs[-1]["review_mode"], "standard")
        self.assertEqual(self.runner.started_specs[-1]["target_output"], "interview_knowledge_base")

    def test_resume_run_rejects_when_another_run_for_same_course_is_active(self) -> None:
        first_draft = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()
        first_run = self.client.post("/runs", json={"draft_id": first_draft["id"]}).json()
        self.runner.snapshots[first_run["id"]] = {"status": "completed", "last_error": None}
        self.client.get(f"/runs/{first_run['id']}")

        second_draft = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第2章 传输层\n\n本节介绍端到端通信。",
            },
        ).json()
        second_run = self.client.post("/runs", json={"draft_id": second_draft["id"]}).json()
        self.runner.snapshots[first_run["id"]] = {"status": "failed", "last_error": "temporary failure"}
        self.runner.snapshots[second_run["id"]] = {"status": "running", "last_error": None}

        response = self.client.post(f"/runs/{first_run['id']}/resume")

        self.assertEqual(response.status_code, 409)
        self.assertIn("already in progress", response.json()["detail"])

    def test_resume_run_clears_stale_runtime_error_when_new_attempt_is_running(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]
        course_dir = self.output_root / "courses" / course_id
        course_dir.mkdir(parents=True, exist_ok=True)
        (course_dir / "course_blueprint.json").write_text(
            json.dumps(
                {
                    "course_id": course_id,
                    "course_name": "Computer Networks",
                    "chapters": [
                        {"chapter_id": "chapter-01", "title": "chapter-01"},
                    ],
                    "policy": {"target_output": "standard_knowledge_pack", "review_mode": "light"},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (course_dir / "runtime_state.json").write_text(
            json.dumps(
                {
                    "course_id": course_id,
                    "blueprint_hash": "hash",
                    "chapters": {},
                    "global": {},
                    "last_error": "old provider quota exhausted",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.runner.snapshots[run_id] = {
            "status": "failed",
            "last_error": "old provider quota exhausted",
        }

        self.client.post(f"/runs/{run_id}/resume")
        self.runner.snapshots[run_id] = {
            "status": "running",
            "last_error": None,
        }

        response = self.client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "running")
        self.assertIsNone(payload["last_error"])

    def test_clean_run_executes_clean_command_and_resets_stage_track(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        self.runner.snapshots[run_id] = {"status": "completed", "last_error": None}

        response = self.client.post(f"/runs/{run_id}/clean")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "cleaned")
        self.assertEqual(self.runner.started_specs[-1]["command"], "clean-course")
        self.assertEqual(self.runner.started_specs[-1]["backend"], "heuristic")
        self.assertEqual(self.runner.started_specs[-1]["base_url"], "")
        self.assertEqual(self.runner.started_specs[-1]["model"], "")
        self.assertEqual([stage["status"] for stage in payload["stages"]], [
            "pending",
            "pending",
            "pending",
            "pending",
            "pending",
            "pending",
            "pending",
            "pending",
            "pending",
        ])

    def test_clean_run_reports_running_while_cleanup_subprocess_is_still_active(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        self.runner.snapshots[run_id] = {"status": "completed", "last_error": None}

        response = self.client.post(f"/runs/{run_id}/clean")
        self.runner.snapshots[run_id] = {"status": "running", "last_error": None}
        refreshed = self.client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.json()["status"], "running")

    def test_clean_run_restores_persisted_record_before_restarting_runner(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        self.runner.snapshots[run_id] = {"status": "completed", "last_error": None}

        replacement_runner = StubRunner()
        restart_client = TestClient(
            create_app(output_root=self.output_root, run_runner=replacement_runner, gui_config_path=self.gui_config_path)
        )

        response = restart_client.post(f"/runs/{run_id}/clean")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(replacement_runner.started_specs[-1]["command"], "clean-course")

    def test_failed_clean_run_does_not_trigger_auto_resume(self) -> None:
        self._configure_openai_runtime(max_resume_attempts=2)
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Distributed Systems",
                "subtitle_text": "# 第1章 概览\n\n本节介绍系统故障与恢复。",
            },
        ).json()
        self.client.post(
            f"/course-drafts/{draft_payload['id']}/config",
            json={
                "template_id": "interview-focus",
                "content_density": "balanced",
                "review_mode": "standard",
                "export_package": True,
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "simple_model": "gpt-5.4-mini",
                "complex_model": "gpt-5.4",
                "timeout_seconds": 180,
            },
        )
        run_payload = self.client.post("/runs", json={"draft_id": draft_payload["id"]}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]
        self._write_runtime_files(
            course_id=course_id,
            course_name="Distributed Systems",
            chapters={
                "chapter-01": {
                    "steps": {
                        "ingest": {"status": "completed"},
                        "curriculum_anchor": {
                            "status": "failed",
                            "attempt_count": 3,
                            "last_error_kind": "network:timeout",
                            "retry_history": [
                                {"attempt": 1, "status": "error", "error_kind": "network:timeout", "will_retry": True},
                                {"attempt": 2, "status": "error", "error_kind": "network:timeout", "will_retry": True},
                                {"attempt": 3, "status": "error", "error_kind": "network:timeout", "will_retry": False},
                            ],
                        },
                    }
                }
            },
            last_error={"scope": "chapter-01", "step": "curriculum_anchor", "last_error_kind": "network:timeout"},
        )
        self.runner.snapshots[run_id] = {"status": "completed", "last_error": None}

        clean_response = self.client.post(f"/runs/{run_id}/clean")
        self.assertEqual(clean_response.status_code, 200)

        self.runner.snapshots[run_id] = {"status": "failed", "last_error": "clean failed"}

        response = self.client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "failed")
        self.assertEqual([spec["command"] for spec in self.runner.started_specs], ["run-course", "clean-course"])

    def test_clean_run_recovers_to_cleaned_after_restart_when_course_runtime_is_gone(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]
        self.runner.snapshots[run_id] = {"status": "completed", "last_error": None}

        self.client.post(f"/runs/{run_id}/clean")

        record_path = self.output_root / "_gui" / "runs" / run_id / "session.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["session"]["status"] = "running"
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

        course_dir = self.output_root / "courses" / course_id
        course_dir.mkdir(parents=True, exist_ok=True)
        for child in list(course_dir.iterdir()):
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        course_dir.rmdir()

        restarted_client = TestClient(
            create_app(output_root=self.output_root, run_runner=StubRunner(), gui_config_path=self.gui_config_path)
        )

        response = restarted_client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "cleaned")

    def test_run_events_stream_returns_sse_payload(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        self.runner.snapshots[run_id] = {"status": "completed", "last_error": None}

        with self.client.stream("GET", f"/runs/{run_id}/events") as response:
            body = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn("event: run.update", body)
        self.assertIn(run_id, body)

    def test_run_log_events_stream_returns_incremental_log_chunk(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        log_path = self.output_root / "_gui" / "runs" / run_id / "process.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("stage 1\nstage 2\n", encoding="utf-8")
        self.runner.snapshots[run_id] = {
            "status": "completed",
            "last_error": None,
            "log_path": str(log_path),
        }

        with self.client.stream("GET", f"/runs/{run_id}/log/events") as response:
            body = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn("event: run.log", body)
        self.assertIn("stage 2", body)

    def test_get_run_log_chunk_marks_complete_when_run_is_terminal_without_log_file(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        self.runner.snapshots[run_id] = {
            "status": "completed",
            "last_error": None,
        }
        service = RunService(
            course_drafts=CourseDraftService(storage=DraftInputStorage(self.output_root)),
            runner=self.runner,
            runtime_reader=RuntimeStateReader(self.output_root),
            output_root=self.output_root,
            gui_config_store=GuiConfigStore(self.gui_config_path),
        )

        chunk = service.get_run_log_chunk(run_id, cursor=0)

        self.assertIsNotNone(chunk)
        self.assertEqual(chunk.content, "")
        self.assertTrue(chunk.complete)

    def test_get_run_log_returns_log_preview_without_exposing_runner_path_contract(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]
        log_path = self.output_root / "_gui" / "runs" / run_id / "process.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
        self.runner.snapshots[run_id] = {
            "status": "running",
            "last_error": None,
            "log_path": str(log_path),
        }

        response = self.client.get(f"/runs/{run_id}/log")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["run_id"], run_id)
        self.assertTrue(payload["available"])
        self.assertIn("line 3", payload["content"])

    def test_get_run_log_returns_unavailable_when_log_not_ready(self) -> None:
        draft_id = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()["id"]
        run_payload = self.client.post("/runs", json={"draft_id": draft_id}).json()
        run_id = run_payload["id"]

        response = self.client.get(f"/runs/{run_id}/log")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["run_id"], run_id)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["content"], "")

    def test_get_run_restores_persisted_run_after_service_restart(self) -> None:
        self.client.put(
            "/gui-runtime-config",
            json={
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "api_key": "sk-openai",
                        "base_url": "https://api.openai.com/v1",
                        "simple_model": "gpt-5.4-mini",
                        "complex_model": "gpt-5.4",
                        "timeout_seconds": 180,
                    },
                    "openai_compatible": {},
                    "anthropic": {},
                },
            },
        )
        draft_response = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        )
        run_payload = self.client.post("/runs", json={"draft_id": draft_response.json()["id"]}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]

        course_dir = self.output_root / "courses" / course_id
        course_dir.mkdir(parents=True, exist_ok=True)
        (course_dir / "course_blueprint.json").write_text(
            json.dumps(
                {
                    "course_id": course_id,
                    "course_name": "Computer Networks",
                    "chapters": [
                        {"chapter_id": "chapter-01", "title": "chapter-01"},
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (course_dir / "runtime_state.json").write_text(
            json.dumps(
                {
                    "course_id": course_id,
                    "chapters": {
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
                                "write_open_questions": {"status": "completed"},
                                "review": {"status": "completed"},
                            }
                        }
                    },
                    "global": {
                        "build_global_glossary": {"status": "completed"},
                        "build_interview_index": {"status": "completed"},
                    },
                    "last_error": None,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        restarted_client = TestClient(create_app(output_root=self.output_root, run_runner=StubRunner()))

        response = restarted_client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], run_id)
        self.assertEqual(payload["course_id"], course_id)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["backend"], "openai")
        self.assertEqual(payload["simple_model"], "gpt-5.4-mini")
        self.assertEqual(payload["complex_model"], "gpt-5.4")

    def test_get_run_does_not_mark_restart_completed_when_blueprint_has_unmaterialized_chapters(self) -> None:
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()
        run_payload = self.client.post("/runs", json={"draft_id": draft_payload["id"]}).json()
        run_id = run_payload["id"]
        course_id = run_payload["course_id"]

        course_dir = self.output_root / "courses" / course_id
        course_dir.mkdir(parents=True, exist_ok=True)
        (course_dir / "course_blueprint.json").write_text(
            json.dumps(
                {
                    "course_id": course_id,
                    "course_name": "Computer Networks",
                    "chapters": [
                        {"chapter_id": "chapter-01", "title": "chapter-01"},
                        {"chapter_id": "chapter-02", "title": "chapter-02"},
                    ],
                    "policy": {"target_output": "interview_knowledge_base", "review_mode": "light"},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (course_dir / "runtime_state.json").write_text(
            json.dumps(
                {
                    "course_id": course_id,
                    "blueprint_hash": "hash",
                    "chapters": {
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
                            }
                        }
                    },
                    "global": {},
                    "last_error": None,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        restarted_client = TestClient(create_app(output_root=self.output_root, run_runner=StubRunner()))

        response = restarted_client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["chapter_progress"], [
            {
                "chapter_id": "chapter-01",
                "status": "completed",
                "current_step": None,
                "completed_step_count": 8,
                "total_step_count": 8,
                "export_ready": True,
            },
            {
                "chapter_id": "chapter-02",
                "status": "pending",
                "current_step": None,
                "completed_step_count": 0,
                "total_step_count": 8,
                "export_ready": False,
            },
        ])

    def test_get_run_marks_orphaned_running_run_failed_after_restart(self) -> None:
        draft_payload = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()
        run_payload = self.client.post("/runs", json={"draft_id": draft_payload["id"]}).json()
        run_id = run_payload["id"]

        restarted_client = TestClient(
            create_app(output_root=self.output_root, run_runner=StubRunner(), gui_config_path=self.gui_config_path)
        )

        response = restarted_client.get(f"/runs/{run_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "failed")
        self.assertIn("runner snapshot", payload["last_error"].lower())

    def test_orphaned_running_run_does_not_block_new_run_for_same_course_after_restart(self) -> None:
        first_draft = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()
        first_run = self.client.post("/runs", json={"draft_id": first_draft["id"]}).json()

        second_draft = self.client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第2章 传输层\n\n本节介绍端到端通信。",
            },
        ).json()

        restarted_runner = StubRunner()
        restarted_client = TestClient(
            create_app(output_root=self.output_root, run_runner=restarted_runner, gui_config_path=self.gui_config_path)
        )

        response = restarted_client.post("/runs", json={"draft_id": second_draft["id"]})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(restarted_runner.started_specs[-1]["command"], "run-course")
        orphaned = restarted_client.get(f"/runs/{first_run['id']}").json()
        self.assertEqual(orphaned["status"], "failed")

    def test_concurrent_create_run_requests_allow_only_one_active_run_per_course(self) -> None:
        slow_runner = SlowStubRunner(delay_seconds=0.2)
        slow_client = TestClient(
            create_app(output_root=self.output_root, run_runner=slow_runner, gui_config_path=self.gui_config_path)
        )
        first_draft = slow_client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第1章 绪论\n\n本节介绍网络分层。",
            },
        ).json()
        second_draft = slow_client.post(
            "/course-drafts",
            json={
                "book_title": "Computer Networks",
                "subtitle_text": "# 第2章 传输层\n\n本节介绍端到端通信。",
            },
        ).json()

        barrier = threading.Barrier(3)
        responses: list[tuple[int, dict[str, object]]] = []

        def create_run(draft_id: str) -> None:
            barrier.wait()
            response = slow_client.post("/runs", json={"draft_id": draft_id})
            responses.append((response.status_code, response.json()))

        first_thread = threading.Thread(target=create_run, args=(first_draft["id"],))
        second_thread = threading.Thread(target=create_run, args=(second_draft["id"],))
        first_thread.start()
        second_thread.start()
        barrier.wait()
        first_thread.join()
        second_thread.join()

        status_codes = sorted(status for status, _payload in responses)
        self.assertEqual(status_codes, [201, 409])
        self.assertEqual(len(slow_runner.started_specs), 1)
