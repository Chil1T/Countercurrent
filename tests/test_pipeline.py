import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any

import processagent.pipeline as pipeline_module
import processagent.provider_policy as provider_policy_module
from processagent.blueprint import finalize_blueprint
from processagent.pipeline import EXECUTION_STRATEGY, HOSTED_PRESSURE_STAGES, PIPELINE_SIGNATURE, HeuristicLLMBackend, PipelineConfig, PipelineRunner
from processagent.provider_policy import ProviderExecutionPolicy
from processagent.testing import StubLLMBackend


def make_blueprint(
    *,
    course_name: str = "数据库系统概论",
    chapters: list[dict] | None = None,
    review_mode: str = "light",
    target_output: str = "interview_knowledge_base",
) -> dict:
    return finalize_blueprint(
        {
            "course_name": course_name,
            "source_type": "published_textbook",
            "book": {
                "title": course_name,
                "authors": ["王珊", "萨师煊"],
                "edition": "第5版",
                "publisher": "高等教育出版社",
                "isbn": "",
            },
            "chapters": chapters or [
                {
                    "chapter_id": "第一章·绪论",
                    "title": "绪论",
                    "aliases": ["第一章·绪论"],
                    "expected_topics": ["数据库发展阶段", "三层模式两级映像"],
                }
            ],
            "policy": {
                "augmentation_mode": "conservative",
                "review_mode": review_mode,
                "target_output": target_output,
            },
            "provenance": {
                "metadata": {"strategy": "user_input"},
                "chapter_structure": {"strategy": "user_toc"},
            },
        }
    )


def make_step_record(blueprint_hash: str | None) -> dict:
    return {
        "status": "completed",
        "updated_at": "t",
        "blueprint_hash": blueprint_hash,
        "pipeline_signature": PIPELINE_SIGNATURE,
    }


class FakeChapterExecutionRuntime:
    def __init__(
        self,
        *,
        course_dir: Path,
        review_enabled: bool = False,
        writer_names: tuple[str, ...] = (
            "write_lecture_note",
            "write_terms",
            "write_interview_qa",
            "write_cross_links",
            "write_open_questions",
        ),
        writer_file_map: dict[str, str] | None = None,
    ) -> None:
        self.course_dir = course_dir
        self.review_enabled = review_enabled
        self.writer_names = writer_names
        self.writer_file_map = writer_file_map or {
            "write_lecture_note": "01-精讲.md",
            "write_terms": "02-术语与定义.md",
            "write_interview_qa": "03-面试问答.md",
            "write_cross_links": "04-跨章关联.md",
            "write_open_questions": "05-疑点与待核.md",
        }
        self.call_order: list[str] = []

    def slim_course_blueprint(self) -> dict[str, Any]:
        return {"course_id": "course-1", "policy": {"target_output": "standard_knowledge_pack"}}

    def ingest_transcript(self, chapter_id: str, transcript_text: str) -> dict[str, Any]:
        return {
            "chapter_id": chapter_id,
            "chunks": [
                {
                    "chunk_id": "chunk-001",
                    "raw_text": transcript_text,
                    "clean_text": transcript_text,
                    "speaker_role": "lecturer",
                    "noise_flags": [],
                }
            ],
        }

    def run_json_stage(self, stage_name: str, payload: dict[str, Any], *, scope: str) -> dict[str, Any]:
        self.call_order.append(stage_name)
        responses = {
            "curriculum_anchor": {"chapter_summary": "锚点", "anchors": []},
            "gap_fill": {"candidates": []},
            "pack_plan": {"writer_profile": "standard_knowledge_pack", "files": []},
            "review": {"status": "approved", "issues": []},
        }
        return responses[stage_name]

    def run_text_stage(self, stage_name: str, payload: dict[str, Any], *, scope: str) -> str:
        self.call_order.append(stage_name)
        return f"# {stage_name}\n"

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def build_pack_payload(
        self,
        *,
        chapter_blueprint: dict[str, Any],
        normalized: dict[str, Any],
        topic_map: dict[str, Any],
        augmentation: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "course_blueprint": self.slim_course_blueprint(),
            "chapter_blueprint": chapter_blueprint,
            "normalized_transcript": normalized,
            "topic_anchor_map": topic_map,
            "augmentation_digest": augmentation,
        }

    def build_writer_payload(
        self,
        *,
        chapter_blueprint: dict[str, Any],
        normalized: dict[str, Any],
        topic_map: dict[str, Any],
        augmentation: dict[str, Any],
        pack_plan: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "chapter_blueprint": chapter_blueprint,
            "normalized_transcript": normalized,
            "topic_anchor_map": topic_map,
            "augmentation_digest": augmentation,
            "pack_plan": pack_plan,
        }

    def build_review_payload(
        self,
        *,
        chapter_blueprint: dict[str, Any],
        normalized: dict[str, Any],
        topic_map: dict[str, Any],
        augmentation: dict[str, Any],
        pack: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "chapter_blueprint": chapter_blueprint,
            "normalized_transcript": normalized,
            "topic_anchor_map": topic_map,
            "augmentation_digest": augmentation,
            "knowledge_pack": pack,
        }


class ConcurrentStageProbe:
    def __init__(self) -> None:
        self.entered = threading.Event()
        self._lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.chapter_ids: list[str] = []

    def enter(self, chapter_id: str) -> None:
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.chapter_ids.append(chapter_id)
            self.entered.set()

    def leave(self) -> None:
        with self._lock:
            self.active -= 1


class TrackingLLMBackend:
    def __init__(
        self,
        *,
        probe: ConcurrentStageProbe | None = None,
        tracked_stage: str = "curriculum_anchor",
        delay_seconds: float = 0.0,
        fail_once_stage: str | None = None,
        provider_name: str = "stub",
    ) -> None:
        self.probe = probe
        self.tracked_stage = tracked_stage
        self.delay_seconds = delay_seconds
        self.fail_once_stage = fail_once_stage
        self.provider_name = provider_name
        self._failed = False
        self._last_call_metadata: dict[str, Any] | None = None

    def generate_json(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        self._track_if_needed(agent_name, payload)
        try:
            if self.fail_once_stage == agent_name and not self._failed:
                self._failed = True
                self._remember_call(payload, None, model_override, status="error", error="forced failure")
                raise RuntimeError(f"forced failure for {agent_name}")
            response = self._json_response(agent_name)
            self._remember_call(payload, response, model_override)
            return response
        finally:
            self._release_if_needed(agent_name)

    def generate_text(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> str:
        self._track_if_needed(agent_name, payload)
        try:
            if self.fail_once_stage == agent_name and not self._failed:
                self._failed = True
                self._remember_call(payload, None, model_override, status="error", error="forced failure")
                raise RuntimeError(f"forced failure for {agent_name}")
            response = f"# {agent_name}\n"
            self._remember_call(payload, response, model_override)
            return response
        finally:
            self._release_if_needed(agent_name)

    def consume_last_call_metadata(self) -> dict[str, Any] | None:
        metadata = self._last_call_metadata
        self._last_call_metadata = None
        return metadata

    def _track_if_needed(self, agent_name: str, payload: dict[str, Any]) -> None:
        if self.probe is None or agent_name != self.tracked_stage:
            return
        chapter_id = payload.get("chapter_blueprint", {}).get("chapter_id", "global")
        self.probe.enter(chapter_id)
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

    def _release_if_needed(self, agent_name: str) -> None:
        if self.probe is None or agent_name != self.tracked_stage:
            return
        self.probe.leave()

    def _remember_call(
        self,
        payload: dict[str, Any],
        response: dict[str, Any] | str | None,
        model_override: str | None,
        *,
        status: str = "completed",
        error: str | None = None,
    ) -> None:
        output_value = "" if response is None else response
        self._last_call_metadata = {
            "provider": self.provider_name,
            "model": model_override,
            "input_tokens": self._estimate_tokens(payload),
            "output_tokens": self._estimate_tokens(output_value),
            "duration_ms": 0,
            "status": status,
            "error": error,
        }

    def _estimate_tokens(self, value: dict[str, Any] | str) -> int:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        return max(1, len(text.encode("utf-8")) // 4)

    def _json_response(self, agent_name: str) -> dict[str, Any]:
        if agent_name == "curriculum_anchor":
            return {"chapter_summary": "锚点", "anchors": []}
        if agent_name == "gap_fill":
            return {"candidates": []}
        if agent_name == "pack_plan":
            return {"writer_profile": "standard_knowledge_pack", "files": []}
        if agent_name == "review":
            return {"status": "approved", "issues": []}
        raise KeyError(f"Unsupported JSON agent: {agent_name}")


class MetadataRaceHeuristicBackend(HeuristicLLMBackend):
    def __init__(self) -> None:
        super().__init__()
        self._arrival_lock = threading.Lock()
        self._arrival_order: list[str] = []
        self._second_ready = threading.Event()
        self._first_consume_done = threading.Event()
        self._writer_file_map = {
            "write_lecture_note": "01-精讲.md",
            "write_terms": "02-术语与定义.md",
            "write_interview_qa": "03-面试问答.md",
            "write_cross_links": "04-跨章关联.md",
            "write_open_questions": "05-疑点与待核.md",
        }
        self._consume_count = 0

    def generate_json(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        if agent_name == "curriculum_anchor":
            chapter_id = payload["chapter_blueprint"]["chapter_id"]
            response = {"chapter_summary": chapter_id, "anchors": []}
            self._remember_call(payload, response, chapter_id)
            order = self._register_arrival(chapter_id)
            if order == 0:
                self._second_ready.wait(timeout=2)
                return response
            self._second_ready.set()
            self._first_consume_done.wait(timeout=2)
            return response
        if agent_name == "gap_fill":
            response = {"candidates": []}
            self._remember_call(payload, response, model_override)
            return response
        if agent_name == "pack_plan":
            response = {"writer_profile": "standard_knowledge_pack", "files": []}
            self._remember_call(payload, response, model_override)
            return response
        return super().generate_json(agent_name, prompt, payload, model_override=model_override)

    def generate_text(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> str:
        if agent_name in self._writer_file_map:
            response = f"# {payload['chapter_blueprint']['chapter_id']} {agent_name}\n"
            self._remember_call(payload, response, model_override)
            return response
        return super().generate_text(agent_name, prompt, payload, model_override=model_override)

    def consume_last_call_metadata(self) -> dict[str, Any] | None:
        metadata = super().consume_last_call_metadata()
        with self._arrival_lock:
            self._consume_count += 1
            if self._consume_count == 1:
                self._first_consume_done.set()
        return metadata

    def _register_arrival(self, chapter_id: str) -> int:
        with self._arrival_lock:
            order = len(self._arrival_order)
            self._arrival_order.append(chapter_id)
            return order


class PipelineRunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_provider_registry = getattr(provider_policy_module, "reset_provider_permit_registry", None)
        if callable(reset_provider_registry):
            reset_provider_registry()
        reset_runtime_registries = getattr(pipeline_module, "reset_pipeline_runtime_registries", None)
        if callable(reset_runtime_registries):
            reset_runtime_registries()

    def test_pipeline_declares_current_hosted_pressure_points_and_serial_execution(self) -> None:
        self.assertEqual(
            HOSTED_PRESSURE_STAGES,
            (
                "curriculum_anchor",
                "gap_fill",
                "pack_plan",
                "write_lecture_note",
                "write_terms",
                "write_interview_qa",
                "write_cross_links",
                "write_open_questions",
                "review",
                "build_global_glossary",
                "build_interview_index",
            ),
        )
        self.assertEqual(
            EXECUTION_STRATEGY,
            {
                "chapter_loop": "policy_limited_parallel",
                "writer_loop": "serial",
                "global_consolidation": "serial",
            },
        )

    def test_run_allows_multiple_chapters_concurrently_but_caps_per_run_parallelism(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            chapters = [
                {
                    "chapter_id": "第一章·绪论",
                    "title": "绪论",
                    "aliases": ["第一章·绪论"],
                    "expected_topics": ["数据库发展阶段"],
                },
                {
                    "chapter_id": "第二章·模型",
                    "title": "模型",
                    "aliases": ["第二章·模型"],
                    "expected_topics": ["关系模型"],
                },
                {
                    "chapter_id": "第三章·语言",
                    "title": "语言",
                    "aliases": ["第三章·语言"],
                    "expected_topics": ["SQL"],
                },
            ]
            blueprint = make_blueprint(chapters=chapters)
            input_dir.mkdir()
            for chapter in chapters:
                (input_dir / f"{chapter['chapter_id']}.md").write_text(
                    f"{chapter['title']} transcript",
                    encoding="utf-8",
                )

            probe = ConcurrentStageProbe()
            backend = TrackingLLMBackend(probe=probe, delay_seconds=0.15)
            policy = ProviderExecutionPolicy(
                provider="stub",
                max_concurrent_per_run=2,
                max_concurrent_global=8,
                transient_http_statuses=(),
                max_call_attempts=1,
                max_resume_attempts=1,
            )
            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    backend_name="stub",
                    provider_policy=policy,
                ),
                llm_backend=backend,
            )

            runner.run()

            self.assertGreaterEqual(len(set(probe.chapter_ids)), 3)
            self.assertEqual(probe.max_active, 2)

    def test_provider_global_permit_caps_total_hosted_calls_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._use_shared_coordination_root(root / "coordination")
            output_dir_a = root / "out-a"
            output_dir_b = root / "out-b"
            shared_probe = ConcurrentStageProbe()
            policy = ProviderExecutionPolicy(
                provider="stub",
                max_concurrent_per_run=2,
                max_concurrent_global=1,
                transient_http_statuses=(),
                max_call_attempts=1,
                max_resume_attempts=1,
            )

            runner_a = self._make_runner_with_tracking_backend(
                root=root,
                course_name="数据库系统概论-A",
                output_dir=output_dir_a,
                probe=shared_probe,
                provider_name="stub",
                policy=policy,
            )
            runner_b = self._make_runner_with_tracking_backend(
                root=root,
                course_name="数据库系统概论-B",
                output_dir=output_dir_b,
                probe=shared_probe,
                provider_name="stub",
                policy=policy,
            )

            errors: list[Exception] = []
            thread_a = self._start_runner_thread(runner_a, errors)
            self.assertTrue(shared_probe.entered.wait(timeout=2))
            thread_b = self._start_runner_thread(runner_b, errors)
            thread_a.join(timeout=5)
            thread_b.join(timeout=5)

            self.assertFalse(thread_a.is_alive())
            self.assertFalse(thread_b.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(shared_probe.max_active, 1)

    def test_failed_hosted_stage_releases_provider_permit_for_stub_and_heuristic(self) -> None:
        for provider_name in ("stub", "heuristic"):
            reset_provider_registry = getattr(provider_policy_module, "reset_provider_permit_registry", None)
            if callable(reset_provider_registry):
                reset_provider_registry()

            with self.subTest(provider_name=provider_name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    output_dir = root / "out"
                    policy = ProviderExecutionPolicy(
                        provider=provider_name,
                        max_concurrent_per_run=1,
                        max_concurrent_global=1,
                        transient_http_statuses=(),
                        max_call_attempts=1,
                        max_resume_attempts=1,
                    )

                    failing_runner = self._make_runner_with_tracking_backend(
                        root=root,
                        course_name=f"{provider_name}-failing",
                        output_dir=output_dir,
                        probe=ConcurrentStageProbe(),
                        provider_name=provider_name,
                        policy=policy,
                        fail_once_stage="curriculum_anchor",
                    )
                    with self.assertRaises(RuntimeError):
                        failing_runner.run()

                    self.assertEqual(failing_runner.provider_permit_registry.active_permits(provider_name), 0)

                    healthy_runner = self._make_runner_with_tracking_backend(
                        root=root,
                        course_name=f"{provider_name}-healthy",
                        output_dir=output_dir,
                        probe=ConcurrentStageProbe(),
                        provider_name=provider_name,
                        policy=policy,
                    )
                    healthy_runner.run()

    def test_same_course_id_rejects_multiple_active_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._use_shared_coordination_root(root / "coordination")
            output_dir_a = root / "out-a"
            output_dir_b = root / "out-b"
            probe = ConcurrentStageProbe()
            policy = ProviderExecutionPolicy(
                provider="stub",
                max_concurrent_per_run=1,
                max_concurrent_global=2,
                transient_http_statuses=(),
                max_call_attempts=1,
                max_resume_attempts=1,
            )
            runner_a = self._make_runner_with_tracking_backend(
                root=root,
                course_name="数据库系统概论-冲突课程",
                output_dir=output_dir_a,
                probe=probe,
                provider_name="stub",
                policy=policy,
                delay_seconds=0.2,
            )
            runner_b = self._make_runner_with_tracking_backend(
                root=root,
                course_name="数据库系统概论-冲突课程",
                output_dir=output_dir_b,
                probe=ConcurrentStageProbe(),
                provider_name="stub",
                policy=policy,
            )

            errors: list[Exception] = []
            thread_a = self._start_runner_thread(runner_a, errors)
            self.assertTrue(probe.entered.wait(timeout=2))

            second_errors: list[Exception] = []
            thread_b = self._start_runner_thread(runner_b, second_errors)
            thread_b.join(timeout=3)
            thread_a.join(timeout=5)

            self.assertFalse(thread_a.is_alive())
            self.assertFalse(thread_b.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(len(second_errors), 1)
            self.assertIsInstance(second_errors[0], RuntimeError)

    def test_stale_course_run_lock_is_reclaimed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            coordination_root = root / "coordination"
            self._use_shared_coordination_root(coordination_root)
            output_dir = root / "out"
            runner = self._make_runner_with_tracking_backend(
                root=root,
                course_name="数据库系统概论-陈旧锁",
                output_dir=output_dir,
                probe=ConcurrentStageProbe(),
                provider_name="stub",
                policy=ProviderExecutionPolicy(
                    provider="stub",
                    max_concurrent_per_run=1,
                    max_concurrent_global=1,
                    transient_http_statuses=(),
                    max_call_attempts=1,
                    max_resume_attempts=1,
                ),
            )
            course_id = runner.course_blueprint["course_id"]
            lock_dir = coordination_root / "course_run_locks" / course_id
            lock_dir.mkdir(parents=True)
            (lock_dir / "owner.json").write_text(
                json.dumps({"course_id": course_id, "pid": 99999999, "acquired_at": 0}, ensure_ascii=False),
                encoding="utf-8",
            )

            runner.run()

            self.assertFalse(lock_dir.exists())
            self.assertTrue((runner.course_dir / "runtime_state.json").exists())

    def test_legacy_course_run_lock_without_pid_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            coordination_root = root / "coordination"
            self._use_shared_coordination_root(coordination_root)
            output_dir = root / "out"
            runner = self._make_runner_with_tracking_backend(
                root=root,
                course_name="数据库系统概论-旧格式锁",
                output_dir=output_dir,
                probe=ConcurrentStageProbe(),
                provider_name="stub",
                policy=ProviderExecutionPolicy(
                    provider="stub",
                    max_concurrent_per_run=1,
                    max_concurrent_global=1,
                    transient_http_statuses=(),
                    max_call_attempts=1,
                    max_resume_attempts=1,
                ),
            )
            course_id = runner.course_blueprint["course_id"]
            lock_dir = coordination_root / "course_run_locks" / course_id
            lock_dir.mkdir(parents=True)
            legacy_owner = {"course_id": course_id, "acquired_at": 123.0}
            (lock_dir / "owner.json").write_text(json.dumps(legacy_owner, ensure_ascii=False), encoding="utf-8")

            with self.assertRaises(RuntimeError):
                runner.run()

            self.assertTrue(lock_dir.exists())
            self.assertEqual(json.loads((lock_dir / "owner.json").read_text(encoding="utf-8")), legacy_owner)

    def test_active_course_run_lock_is_not_reclaimed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            coordination_root = root / "coordination"
            self._use_shared_coordination_root(coordination_root)
            output_dir = root / "out"
            runner = self._make_runner_with_tracking_backend(
                root=root,
                course_name="数据库系统概论-活跃锁",
                output_dir=output_dir,
                probe=ConcurrentStageProbe(),
                provider_name="stub",
                policy=ProviderExecutionPolicy(
                    provider="stub",
                    max_concurrent_per_run=1,
                    max_concurrent_global=1,
                    transient_http_statuses=(),
                    max_call_attempts=1,
                    max_resume_attempts=1,
                ),
            )
            course_id = runner.course_blueprint["course_id"]
            lock_dir = coordination_root / "course_run_locks" / course_id
            lock_dir.mkdir(parents=True)
            owner_payload = provider_policy_module.build_coordination_owner_payload({"course_id": course_id})
            (lock_dir / "owner.json").write_text(json.dumps(owner_payload, ensure_ascii=False), encoding="utf-8")

            with self.assertRaises(RuntimeError):
                runner.run()

            self.assertTrue(lock_dir.exists())

    def test_concurrent_llm_logging_keeps_per_call_metadata_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            chapters = [
                {
                    "chapter_id": "第一章·绪论",
                    "title": "绪论",
                    "aliases": ["第一章·绪论"],
                    "expected_topics": ["数据库发展阶段"],
                },
                {
                    "chapter_id": "第二章·模型",
                    "title": "模型",
                    "aliases": ["第二章·模型"],
                    "expected_topics": ["关系模型"],
                },
            ]
            blueprint = make_blueprint(chapters=chapters)
            input_dir.mkdir()
            for chapter in chapters:
                (input_dir / f"{chapter['chapter_id']}.md").write_text(
                    f"{chapter['title']} transcript",
                    encoding="utf-8",
                )

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    backend_name="heuristic",
                    provider_policy=ProviderExecutionPolicy(
                        provider="heuristic",
                        max_concurrent_per_run=2,
                        max_concurrent_global=2,
                        transient_http_statuses=(),
                        max_call_attempts=1,
                        max_resume_attempts=1,
                    ),
                ),
                llm_backend=MetadataRaceHeuristicBackend(),
            )

            runner.run()

            log_entries = [
                json.loads(line)
                for line in (output_dir / "courses" / blueprint["course_id"] / "runtime" / "llm_calls.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            ]
            curriculum_entries = {
                entry["scope"]: entry
                for entry in log_entries
                if entry["stage"] == "curriculum_anchor"
            }
            self.assertEqual(curriculum_entries["第一章·绪论"]["model"], "第一章·绪论")
            self.assertEqual(curriculum_entries["第二章·模型"]["model"], "第二章·模型")

    def test_heuristic_run_course_completes_with_slim_writer_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(target_output="standard_knowledge_pack")
            input_dir.mkdir()
            (input_dir / "第一章·绪论.md").write_text(
                "数据库系统由数据库、硬件、软件和人员组成。三层模式两级映像是重点。",
                encoding="utf-8",
            )

            runner = PipelineRunner(
                config=PipelineConfig(input_dir=input_dir, output_dir=output_dir, course_blueprint=blueprint),
                llm_backend=HeuristicLLMBackend(),
            )

            runner.run()

            chapter_dir = self._chapter_dir(output_dir, blueprint)
            self.assertTrue((chapter_dir / "notebooklm" / "01-精讲.md").exists())
            self.assertTrue((chapter_dir / "notebooklm" / "05-疑点与待核.md").exists())

    def test_chapter_worker_runs_single_chapter_stages_in_serial_order(self) -> None:
        from processagent.chapter_execution import ChapterExecutionPlanner, ChapterWorker, RuntimeStateMutationGuard

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            course_dir = root / "out" / "courses" / "course-1"
            transcript_file = root / "captions" / "第一章·绪论.md"
            transcript_file.parent.mkdir(parents=True)
            transcript_file.write_text(
                "数据库系统由数据库、硬件、软件和人员组成。三层模式两级映像是重点。",
                encoding="utf-8",
            )
            runtime_state = {"chapters": {}, "global": {}, "last_error": None}
            runtime_state_path = course_dir / "runtime_state.json"
            runtime = FakeChapterExecutionRuntime(course_dir=course_dir)
            guard = RuntimeStateMutationGuard(
                runtime_state_path=runtime_state_path,
                runtime_state=runtime_state,
                blueprint_hash="hash-1",
                now_iso_factory=lambda: "2026-03-27T00:00:00+00:00",
            )
            guard.persist()

            planner = ChapterExecutionPlanner(runtime=runtime, runtime_state_guard=guard)
            chapter_blueprint = {
                "chapter_id": "第一章·绪论",
                "title": "绪论",
                "expected_topics": ["数据库发展阶段", "三层模式两级映像"],
            }
            plan = planner.plan(transcript_file=transcript_file, chapter_blueprint=chapter_blueprint)

            ChapterWorker(runtime=runtime, runtime_state_guard=guard).run(plan)

            self.assertEqual(
                runtime.call_order,
                [
                    "curriculum_anchor",
                    "gap_fill",
                    "pack_plan",
                    "write_lecture_note",
                    "write_terms",
                    "write_interview_qa",
                    "write_cross_links",
                    "write_open_questions",
                ],
            )

    def test_chapter_execution_planner_skips_completed_steps_for_same_chapter(self) -> None:
        from processagent.chapter_execution import ChapterExecutionPlanner, RuntimeStateMutationGuard

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            course_dir = root / "out" / "courses" / "course-1"
            chapter_dir = course_dir / "chapters" / "第一章·绪论"
            intermediate_dir = chapter_dir / "intermediate"
            transcript_file = root / "captions" / "第一章·绪论.md"
            transcript_file.parent.mkdir(parents=True)
            intermediate_dir.mkdir(parents=True)

            transcript_file.write_text("数据库系统由数据库、硬件、软件和人员组成。", encoding="utf-8")
            (intermediate_dir / "normalized_transcript.json").write_text(
                json.dumps(
                    {
                        "chapter_id": "第一章·绪论",
                        "chunks": [
                            {
                                "chunk_id": "chunk-001",
                                "raw_text": "raw",
                                "clean_text": "数据库系统由数据库、硬件、软件和人员组成。",
                                "speaker_role": "lecturer",
                                "noise_flags": [],
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (intermediate_dir / "topic_anchor_map.json").write_text(
                json.dumps({"chapter_summary": "锚点", "anchors": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (intermediate_dir / "augmentation_candidates.json").write_text(
                json.dumps({"candidates": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            runtime_state = {
                "chapters": {
                    "第一章·绪论": {
                        "steps": {
                            "ingest": make_step_record(None),
                            "curriculum_anchor": make_step_record("hash-1"),
                            "gap_fill": make_step_record("hash-1"),
                        }
                    }
                },
                "global": {},
                "last_error": None,
            }
            course_dir.mkdir(parents=True, exist_ok=True)
            runtime_state_path = course_dir / "runtime_state.json"
            runtime_state_path.write_text(json.dumps(runtime_state, ensure_ascii=False, indent=2), encoding="utf-8")

            runtime = FakeChapterExecutionRuntime(course_dir=course_dir)
            guard = RuntimeStateMutationGuard(
                runtime_state_path=runtime_state_path,
                runtime_state=runtime_state,
                blueprint_hash="hash-1",
                now_iso_factory=lambda: "2026-03-27T00:00:00+00:00",
            )
            planner = ChapterExecutionPlanner(runtime=runtime, runtime_state_guard=guard)

            plan = planner.plan(
                transcript_file=transcript_file,
                chapter_blueprint={
                    "chapter_id": "第一章·绪论",
                    "title": "绪论",
                    "expected_topics": [],
                },
            )

            self.assertEqual(
                plan.pending_steps,
                (
                    "pack_plan",
                    "write_lecture_note",
                    "write_terms",
                    "write_interview_qa",
                    "write_cross_links",
                    "write_open_questions",
                ),
            )

    def test_runtime_state_mutation_guard_preserves_other_chapter_state(self) -> None:
        from processagent.chapter_execution import RuntimeStateMutationGuard

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_state_path = root / "runtime_state.json"
            runtime_state = {
                "course_id": "course-1",
                "blueprint_hash": "hash-1",
                "provider": "stub",
                "default_model": "",
                "stage_models": {},
                "pipeline_signature": PIPELINE_SIGNATURE,
                "review_enabled": False,
                "review_mode": "light",
                "target_output": "interview_knowledge_base",
                "run_identity": {
                    "review_enabled": False,
                    "review_mode": "light",
                    "target_output": "interview_knowledge_base",
                },
                "chapters": {
                    "第一章·绪论": {"steps": {"ingest": make_step_record(None)}},
                    "第二章·模型": {"steps": {"gap_fill": make_step_record("hash-1")}},
                },
                "global": {},
                "last_error": {"scope": "第一章·绪论", "step": "gap_fill"},
            }
            runtime_state_path.write_text(json.dumps(runtime_state, ensure_ascii=False, indent=2), encoding="utf-8")

            guard = RuntimeStateMutationGuard(
                runtime_state_path=runtime_state_path,
                runtime_state=runtime_state,
                blueprint_hash="hash-1",
                now_iso_factory=lambda: "2026-03-27T00:00:00+00:00",
            )

            guard.mark_step_complete("第一章·绪论", "pack_plan")

            persisted_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
            self.assertIn("第二章·模型", persisted_state["chapters"])
            self.assertEqual(
                persisted_state["chapters"]["第二章·模型"]["steps"]["gap_fill"]["status"],
                "completed",
            )
            self.assertEqual(
                persisted_state["chapters"]["第一章·绪论"]["steps"]["pack_plan"]["pipeline_signature"],
                PIPELINE_SIGNATURE,
            )
            self.assertIsNone(persisted_state["last_error"])

    def test_run_with_build_global_keeps_chapter_execution_path_bypassed(self) -> None:
        class ExplodingPlanner:
            def plan(self, *, transcript_file: Path, chapter_blueprint: dict[str, Any]) -> Any:
                raise AssertionError("build-global should not invoke chapter planner")

        class ExplodingWorker:
            def run(self, plan: Any) -> None:
                raise AssertionError("build-global should not invoke chapter worker")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(target_output="standard_knowledge_pack")
            course_dir = output_dir / "courses" / blueprint["course_id"]
            notebooklm_dir = self._chapter_dir(output_dir, blueprint) / "notebooklm"
            input_dir.mkdir()
            notebooklm_dir.mkdir(parents=True)

            runtime_state = {
                "course_id": blueprint["course_id"],
                "blueprint_hash": blueprint["blueprint_hash"],
                "provider": "stub",
                "default_model": "",
                "stage_models": {},
                "pipeline_signature": PIPELINE_SIGNATURE,
                "review_enabled": False,
                "review_mode": blueprint["policy"]["review_mode"],
                "target_output": blueprint["policy"]["target_output"],
                "run_identity": {
                    "review_enabled": False,
                    "review_mode": blueprint["policy"]["review_mode"],
                    "target_output": blueprint["policy"]["target_output"],
                },
                "chapters": {
                    "第一章·绪论": {
                        "steps": {
                            "write_terms": make_step_record(blueprint["blueprint_hash"]),
                            "write_interview_qa": make_step_record(blueprint["blueprint_hash"]),
                            "write_cross_links": make_step_record(blueprint["blueprint_hash"]),
                        }
                    }
                },
                "global": {},
                "last_error": None,
            }
            course_dir.mkdir(parents=True, exist_ok=True)
            (course_dir / "course_blueprint.json").write_text(
                json.dumps(blueprint, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (course_dir / "runtime_state.json").write_text(
                json.dumps(runtime_state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (notebooklm_dir / "02-术语与定义.md").write_text("# 术语\n\n- DBMS\n", encoding="utf-8")
            (notebooklm_dir / "03-面试问答.md").write_text("# 面试问答\n\n- 什么是 DBMS？\n", encoding="utf-8")
            (notebooklm_dir / "04-跨章关联.md").write_text("# 跨章关联\n\n- 与后续章节关联。\n", encoding="utf-8")

            backend = StubLLMBackend(
                responses={
                    "build_global_glossary": "# 全书术语表\n\n## 第一章·绪论\n- DBMS\n",
                    "build_interview_index": "# 面试索引\n\n## 第一章·绪论\n- 什么是 DBMS？\n",
                }
            )
            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    run_global_consolidation=True,
                ),
                llm_backend=backend,
            )
            runner.chapter_planner = ExplodingPlanner()
            runner.chapter_worker = ExplodingWorker()

            runner.run()

            self.assertTrue((course_dir / "global" / "global_glossary.md").exists())
            self.assertTrue((course_dir / "global" / "interview_index.md").exists())

    def _make_runner_with_tracking_backend(
        self,
        *,
        root: Path,
        course_name: str,
        output_dir: Path,
        probe: ConcurrentStageProbe,
        provider_name: str,
        policy: ProviderExecutionPolicy,
        delay_seconds: float = 0.15,
        fail_once_stage: str | None = None,
    ) -> PipelineRunner:
        input_dir = root / course_name / "captions"
        chapters = [
            {
                "chapter_id": "第一章·绪论",
                "title": "绪论",
                "aliases": ["第一章·绪论"],
                "expected_topics": ["数据库发展阶段"],
            },
            {
                "chapter_id": "第二章·模型",
                "title": "模型",
                "aliases": ["第二章·模型"],
                "expected_topics": ["关系模型"],
            },
        ]
        blueprint = make_blueprint(course_name=course_name, chapters=chapters)
        input_dir.mkdir(parents=True, exist_ok=True)
        for chapter in chapters:
            (input_dir / f"{chapter['chapter_id']}.md").write_text(
                f"{chapter['title']} transcript",
                encoding="utf-8",
            )
        backend = TrackingLLMBackend(
            probe=probe,
            delay_seconds=delay_seconds,
            fail_once_stage=fail_once_stage,
            provider_name=provider_name,
        )
        return PipelineRunner(
            config=PipelineConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                course_blueprint=blueprint,
                backend_name=provider_name,
                provider_policy=policy,
            ),
            llm_backend=backend,
        )

    def _start_runner_thread(self, runner: PipelineRunner, errors: list[Exception]) -> threading.Thread:
        def target() -> None:
            try:
                runner.run()
            except Exception as error:  # pragma: no cover - test helper
                errors.append(error)

        thread = threading.Thread(target=target)
        thread.start()
        return thread

    def _use_shared_coordination_root(self, coordination_root: Path) -> None:
        original = os.environ.get("PROCESSAGENT_COORDINATION_ROOT")
        os.environ["PROCESSAGENT_COORDINATION_ROOT"] = str(coordination_root)

        def restore() -> None:
            if original is None:
                os.environ.pop("PROCESSAGENT_COORDINATION_ROOT", None)
            else:
                os.environ["PROCESSAGENT_COORDINATION_ROOT"] = original

        self.addCleanup(restore)
        reset_provider_registry = getattr(provider_policy_module, "reset_provider_permit_registry", None)
        if callable(reset_provider_registry):
            reset_provider_registry()
        reset_runtime_registries = getattr(pipeline_module, "reset_pipeline_runtime_registries", None)
        if callable(reset_runtime_registries):
            reset_runtime_registries()

    def _chapter_dir(self, output_dir: Path, blueprint: dict) -> Path:
        return output_dir / "courses" / blueprint["course_id"] / "chapters" / "第一章·绪论"

    def test_run_creates_course_scoped_outputs_and_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(target_output="standard_knowledge_pack")
            input_dir.mkdir()

            (input_dir / "第一章·绪论.md").write_text(
                "第一章 数据库发展经历人工管理、文件系统和数据库系统阶段。"
                "三层模式两级映像是高频概念。",
                encoding="utf-8",
            )

            backend = StubLLMBackend(
                responses={
                    "curriculum_anchor": {
                        "chapter_summary": "标准数据库系统概论主题映射",
                        "anchors": [
                            {
                                "canonical_topic": "数据库发展阶段",
                                "coverage_status": "covered",
                                "supporting_chunk_ids": ["chunk-001"],
                                "missing_expected_points": [],
                            }
                        ],
                    },
                    "gap_fill": {"candidates": []},
                    "compose_pack": {
                        "files": {
                            "01-精讲.md": "# 精讲\n\n- 内容来自 transcript。",
                            "02-术语与定义.md": "# 术语\n\n- **DBMS**：数据库管理系统。",
                            "03-面试问答.md": "# 面试问答\n\n## 概念题\n\n### 什么是 DBMS？",
                            "04-跨章关联.md": "# 跨章关联\n\n- 与关系模型和 SQL 基础相连。",
                            "05-疑点与待核.md": "# 疑点与待核\n\n- 暂无高风险疑点。",
                        }
                    },
                    "canonicalize": {
                        "global_glossary": "# 全书术语表\n\n- **模式**：数据库整体逻辑结构。",
                        "interview_index": "# 面试索引\n\n- 三层模式两级映像",
                    },
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(input_dir=input_dir, output_dir=output_dir, course_blueprint=blueprint),
                llm_backend=backend,
            )

            runner.run()

            course_dir = output_dir / "courses" / blueprint["course_id"]
            chapter_dir = self._chapter_dir(output_dir, blueprint)
            self.assertTrue((course_dir / "course_blueprint.json").exists())
            self.assertTrue((course_dir / "runtime_state.json").exists())
            self.assertTrue((chapter_dir / "intermediate" / "normalized_transcript.json").exists())
            self.assertTrue((chapter_dir / "intermediate" / "topic_anchor_map.json").exists())
            self.assertTrue((chapter_dir / "intermediate" / "augmentation_candidates.json").exists())
            self.assertFalse((chapter_dir / "review_report.json").exists())
            self.assertTrue((chapter_dir / "notebooklm" / "01-精讲.md").exists())
            self.assertTrue((chapter_dir / "notebooklm" / "05-疑点与待核.md").exists())
            self.assertFalse((course_dir / "global" / "global_glossary.md").exists())

            runtime_state = json.loads((course_dir / "runtime_state.json").read_text(encoding="utf-8"))
            self.assertEqual(runtime_state["blueprint_hash"], blueprint["blueprint_hash"])
            self.assertEqual(runtime_state["chapters"]["第一章·绪论"]["steps"]["pack_plan"]["status"], "completed")
            self.assertEqual(
                runtime_state["chapters"]["第一章·绪论"]["steps"]["write_open_questions"]["status"],
                "completed",
            )
            self.assertEqual(runtime_state["global"], {})

    def test_run_writes_per_call_llm_accountability_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(target_output="standard_knowledge_pack")
            input_dir.mkdir()
            (input_dir / "第一章·绪论.md").write_text(
                "第一章 数据库发展经历人工管理、文件系统和数据库系统阶段。",
                encoding="utf-8",
            )
            backend = StubLLMBackend(
                responses={
                    "curriculum_anchor": {
                        "chapter_summary": "标准数据库系统概论主题映射",
                        "anchors": [],
                    },
                    "gap_fill": {"candidates": []},
                    "compose_pack": {
                        "files": {
                            "01-精讲.md": "# 精讲\n",
                            "02-术语与定义.md": "# 术语\n",
                            "03-面试问答.md": "# 面试问答\n",
                            "04-跨章关联.md": "# 跨章关联\n",
                            "05-疑点与待核.md": "# 疑点与待核\n",
                        }
                    },
                }
            )
            runner = PipelineRunner(
                config=PipelineConfig(input_dir=input_dir, output_dir=output_dir, course_blueprint=blueprint),
                llm_backend=backend,
            )

            runner.run()

            log_path = output_dir / "courses" / blueprint["course_id"] / "runtime" / "llm_calls.jsonl"
            self.assertTrue(log_path.exists())
            entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(
                [entry["stage"] for entry in entries],
                [
                    "curriculum_anchor",
                    "gap_fill",
                    "pack_plan",
                    "write_lecture_note",
                    "write_terms",
                    "write_interview_qa",
                    "write_cross_links",
                    "write_open_questions",
                ],
            )
            self.assertTrue(all(entry["provider"] == "stub" for entry in entries))
            self.assertTrue(all(entry["scope"] == "第一章·绪论" for entry in entries))
            self.assertTrue(all(entry["input_tokens"] > 0 for entry in entries))
            self.assertTrue(all(entry["output_tokens"] > 0 for entry in entries))

    def test_run_resumes_from_existing_intermediate_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint()
            course_dir = output_dir / "courses" / blueprint["course_id"]
            chapter_dir = self._chapter_dir(output_dir, blueprint)
            intermediate_dir = chapter_dir / "intermediate"
            notebooklm_dir = chapter_dir / "notebooklm"
            input_dir.mkdir()
            intermediate_dir.mkdir(parents=True)
            notebooklm_dir.mkdir(parents=True)

            (input_dir / "第一章·绪论.md").write_text("这份文本不应该再触发前置步骤。", encoding="utf-8")
            (course_dir / "course_blueprint.json").parent.mkdir(parents=True, exist_ok=True)
            (course_dir / "course_blueprint.json").write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")
            (intermediate_dir / "normalized_transcript.json").write_text(
                json.dumps(
                    {
                        "chapter_id": "第一章·绪论",
                        "chunks": [
                            {
                                "chunk_id": "chunk-001",
                                "raw_text": "raw",
                                "clean_text": "clean",
                                "speaker_role": "lecturer",
                                "noise_flags": [],
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (intermediate_dir / "topic_anchor_map.json").write_text(
                json.dumps({"chapter_summary": "s", "anchors": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (intermediate_dir / "augmentation_candidates.json").write_text(
                json.dumps({"candidates": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (course_dir / "runtime_state.json").write_text(
                json.dumps(
                    {
                        "course_id": blueprint["course_id"],
                        "blueprint_hash": blueprint["blueprint_hash"],
                        "provider": "stub",
                        "default_model": "",
                        "stage_models": {},
                        "chapters": {
                            "第一章·绪论": {
                                "steps": {
                                    "ingest": {"status": "completed", "updated_at": "t", "blueprint_hash": None, "pipeline_signature": PIPELINE_SIGNATURE},
                                    "curriculum_anchor": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": blueprint["blueprint_hash"],
                                        "pipeline_signature": PIPELINE_SIGNATURE,
                                    },
                                    "gap_fill": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": blueprint["blueprint_hash"],
                                        "pipeline_signature": PIPELINE_SIGNATURE,
                                    },
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

            backend = StubLLMBackend(
                responses={
                    "compose_pack": {
                        "files": {
                            "01-精讲.md": "# 精讲\n",
                            "02-术语与定义.md": "# 术语\n",
                            "03-面试问答.md": "# 面试问答\n",
                            "04-跨章关联.md": "# 跨章关联\n",
                            "05-疑点与待核.md": "# 疑点与待核\n",
                        }
                    },
                    "canonicalize": {"global_glossary": "# g\n", "interview_index": "# i\n"},
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(input_dir=input_dir, output_dir=output_dir, course_blueprint=blueprint),
                llm_backend=backend,
            )

            runner.run()

            called_agents = [item["agent_name"] for item in backend.calls or []]
            self.assertNotIn("curriculum_anchor", called_agents)
            self.assertNotIn("gap_fill", called_agents)
            self.assertIn("pack_plan", called_agents)
            self.assertIn("write_lecture_note", called_agents)
            self.assertTrue((notebooklm_dir / "01-精讲.md").exists())
            self.assertFalse((chapter_dir / "review_report.json").exists())

    def test_blueprint_hash_change_invalidates_downstream_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            old_blueprint = make_blueprint(target_output="review_notes")
            new_blueprint = make_blueprint(target_output="interview_knowledge_base")
            course_dir = output_dir / "courses" / new_blueprint["course_id"]
            chapter_dir = self._chapter_dir(output_dir, new_blueprint)
            intermediate_dir = chapter_dir / "intermediate"
            notebooklm_dir = chapter_dir / "notebooklm"
            input_dir.mkdir()
            intermediate_dir.mkdir(parents=True)
            notebooklm_dir.mkdir(parents=True)

            (input_dir / "第一章·绪论.md").write_text("数据库系统由数据库、软件和人员组成。", encoding="utf-8")
            (course_dir / "course_blueprint.json").write_text(json.dumps(old_blueprint, ensure_ascii=False, indent=2), encoding="utf-8")
            (intermediate_dir / "normalized_transcript.json").write_text(
                json.dumps(
                    {
                        "chapter_id": "第一章·绪论",
                        "chunks": [
                            {
                                "chunk_id": "chunk-001",
                                "raw_text": "raw",
                                "clean_text": "数据库系统由数据库、软件和人员组成。",
                                "speaker_role": "lecturer",
                                "noise_flags": [],
                            }
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
                        "course_id": old_blueprint["course_id"],
                        "blueprint_hash": old_blueprint["blueprint_hash"],
                        "provider": "stub",
                        "default_model": "",
                        "stage_models": {},
                        "chapters": {
                            "第一章·绪论": {
                                "steps": {
                                    "ingest": {"status": "completed", "updated_at": "t", "blueprint_hash": None, "pipeline_signature": PIPELINE_SIGNATURE},
                                    "curriculum_anchor": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": old_blueprint["blueprint_hash"],
                                        "pipeline_signature": PIPELINE_SIGNATURE,
                                    },
                                    "gap_fill": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": old_blueprint["blueprint_hash"],
                                        "pipeline_signature": PIPELINE_SIGNATURE,
                                    },
                                    "compose_pack": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": old_blueprint["blueprint_hash"],
                                        "pipeline_signature": PIPELINE_SIGNATURE,
                                    },
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
            for file_name in (
                "topic_anchor_map.json",
                "augmentation_candidates.json",
            ):
                (intermediate_dir / file_name).write_text("{}", encoding="utf-8")
            for file_name in (
                "01-精讲.md",
                "02-术语与定义.md",
                "03-面试问答.md",
                "04-跨章关联.md",
                "05-疑点与待核.md",
            ):
                (notebooklm_dir / file_name).write_text("old", encoding="utf-8")

            backend = StubLLMBackend(
                responses={
                    "curriculum_anchor": {"chapter_summary": "x", "anchors": []},
                    "gap_fill": {"candidates": []},
                    "compose_pack": {
                        "files": {
                            "01-精讲.md": "# 精讲\n",
                            "02-术语与定义.md": "# 术语\n",
                            "03-面试问答.md": "# 面试问答\n",
                            "04-跨章关联.md": "# 跨章关联\n",
                            "05-疑点与待核.md": "# 疑点与待核\n",
                        }
                    },
                    "canonicalize": {"global_glossary": "# g\n", "interview_index": "# i\n"},
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(input_dir=input_dir, output_dir=output_dir, course_blueprint=new_blueprint),
                llm_backend=backend,
            )

            runner.run()

            called_agents = [item["agent_name"] for item in backend.calls or []]
            self.assertIn("curriculum_anchor", called_agents)
            self.assertIn("gap_fill", called_agents)
            self.assertIn("pack_plan", called_agents)
            self.assertIn("write_lecture_note", called_agents)

    def test_new_run_overwrites_persisted_run_identity_with_current_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            old_blueprint = make_blueprint(review_mode="light", target_output="standard_knowledge_pack")
            new_blueprint = make_blueprint(review_mode="strict", target_output="interview_knowledge_base")
            course_dir = output_dir / "courses" / new_blueprint["course_id"]
            input_dir.mkdir()
            course_dir.mkdir(parents=True, exist_ok=True)

            (course_dir / "runtime_state.json").write_text(
                json.dumps(
                    {
                        "course_id": new_blueprint["course_id"],
                        "blueprint_hash": old_blueprint["blueprint_hash"],
                        "provider": "stub",
                        "default_model": "",
                        "stage_models": {},
                        "pipeline_signature": PIPELINE_SIGNATURE,
                        "review_enabled": False,
                        "review_mode": "light",
                        "target_output": "standard_knowledge_pack",
                        "run_identity": {
                            "review_enabled": False,
                            "review_mode": "light",
                            "target_output": "standard_knowledge_pack",
                        },
                        "chapters": {},
                        "global": {},
                        "last_error": None,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=new_blueprint,
                    enable_review=True,
                ),
                llm_backend=HeuristicLLMBackend(),
            )

            self.assertEqual(
                runner.runtime_state["run_identity"],
                {
                    "review_enabled": True,
                    "review_mode": "strict",
                    "target_output": "interview_knowledge_base",
                },
            )
            self.assertTrue(runner.runtime_state["review_enabled"])
            self.assertEqual(runner.runtime_state["review_mode"], "strict")
            self.assertEqual(runner.runtime_state["target_output"], "interview_knowledge_base")

    def test_manual_global_consolidation_preserves_persisted_run_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(review_mode="standard", target_output="interview_knowledge_base")
            course_dir = output_dir / "courses" / blueprint["course_id"]
            notebooklm_dir = self._chapter_dir(output_dir, blueprint) / "notebooklm"
            input_dir.mkdir()
            notebooklm_dir.mkdir(parents=True)
            course_dir.mkdir(parents=True, exist_ok=True)

            (course_dir / "course_blueprint.json").write_text(
                json.dumps(blueprint, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (course_dir / "runtime_state.json").write_text(
                json.dumps(
                    {
                        "course_id": blueprint["course_id"],
                        "blueprint_hash": blueprint["blueprint_hash"],
                        "provider": "stub",
                        "default_model": "",
                        "stage_models": {},
                        "pipeline_signature": PIPELINE_SIGNATURE,
                        "review_enabled": True,
                        "review_mode": "standard",
                        "target_output": "interview_knowledge_base",
                        "run_identity": {
                            "review_enabled": True,
                            "review_mode": "standard",
                            "target_output": "interview_knowledge_base",
                        },
                        "chapters": {
                            "第一章·绪论": {
                                "steps": {
                                    "write_terms": {
                                        "status": "completed",
                                        "blueprint_hash": blueprint["blueprint_hash"],
                                        "pipeline_signature": PIPELINE_SIGNATURE,
                                    },
                                    "write_interview_qa": {
                                        "status": "completed",
                                        "blueprint_hash": blueprint["blueprint_hash"],
                                        "pipeline_signature": PIPELINE_SIGNATURE,
                                    },
                                    "write_cross_links": {
                                        "status": "completed",
                                        "blueprint_hash": blueprint["blueprint_hash"],
                                        "pipeline_signature": PIPELINE_SIGNATURE,
                                    },
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
            (notebooklm_dir / "02-术语与定义.md").write_text("# 术语\n\n- DBMS\n", encoding="utf-8")
            (notebooklm_dir / "03-面试问答.md").write_text("# 面试问答\n\n- 什么是 DBMS？\n", encoding="utf-8")
            (notebooklm_dir / "04-跨章关联.md").write_text("# 跨章关联\n\n- 与后续章节关联。\n", encoding="utf-8")

            backend = StubLLMBackend(
                responses={
                    "build_global_glossary": "# glossary\n",
                    "build_interview_index": "# index\n",
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    run_global_consolidation=True,
                ),
                llm_backend=backend,
            )

            self.assertEqual(
                runner.runtime_state["run_identity"],
                {
                    "review_enabled": True,
                    "review_mode": "standard",
                    "target_output": "interview_knowledge_base",
                },
            )

    def test_manual_global_consolidation_excludes_stale_runtime_scopes_from_old_blueprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(target_output="standard_knowledge_pack")
            course_dir = output_dir / "courses" / blueprint["course_id"]
            current_notebooklm_dir = self._chapter_dir(output_dir, blueprint) / "notebooklm"
            stale_notebooklm_dir = course_dir / "chapters" / "第二章·旧章节" / "notebooklm"
            input_dir.mkdir()
            current_notebooklm_dir.mkdir(parents=True)
            stale_notebooklm_dir.mkdir(parents=True)
            course_dir.mkdir(parents=True, exist_ok=True)

            current_step = {
                "status": "completed",
                "updated_at": "t",
                "blueprint_hash": blueprint["blueprint_hash"],
                "pipeline_signature": PIPELINE_SIGNATURE,
            }
            stale_step = {
                "status": "completed",
                "updated_at": "old",
                "blueprint_hash": "stale-blueprint-hash",
                "pipeline_signature": PIPELINE_SIGNATURE,
            }

            (course_dir / "course_blueprint.json").write_text(
                json.dumps(blueprint, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (course_dir / "runtime_state.json").write_text(
                json.dumps(
                    {
                        "course_id": blueprint["course_id"],
                        "blueprint_hash": blueprint["blueprint_hash"],
                        "provider": "stub",
                        "default_model": "",
                        "stage_models": {},
                        "pipeline_signature": PIPELINE_SIGNATURE,
                        "review_enabled": False,
                        "review_mode": blueprint["policy"]["review_mode"],
                        "target_output": blueprint["policy"]["target_output"],
                        "run_identity": {
                            "review_enabled": False,
                            "review_mode": blueprint["policy"]["review_mode"],
                            "target_output": blueprint["policy"]["target_output"],
                        },
                        "chapters": {
                            "第一章·绪论": {
                                "steps": {
                                    "write_terms": current_step,
                                    "write_interview_qa": current_step,
                                    "write_cross_links": current_step,
                                }
                            },
                            "第二章·旧章节": {
                                "steps": {
                                    "write_terms": stale_step,
                                    "write_interview_qa": stale_step,
                                    "write_cross_links": stale_step,
                                }
                            },
                        },
                        "global": {},
                        "last_error": None,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (current_notebooklm_dir / "02-术语与定义.md").write_text("# 术语\n\n- DBMS\n", encoding="utf-8")
            (current_notebooklm_dir / "03-面试问答.md").write_text("# 面试问答\n\n- 什么是 DBMS？\n", encoding="utf-8")
            (current_notebooklm_dir / "04-跨章关联.md").write_text("# 跨章关联\n\n- 与后续章节关联。\n", encoding="utf-8")
            (stale_notebooklm_dir / "02-术语与定义.md").write_text("# 术语\n\n- STALE\n", encoding="utf-8")
            (stale_notebooklm_dir / "03-面试问答.md").write_text("# 面试问答\n\n- 什么是 STALE？\n", encoding="utf-8")
            (stale_notebooklm_dir / "04-跨章关联.md").write_text("# 跨章关联\n\n- 这是旧章节。\n", encoding="utf-8")

            backend = StubLLMBackend(
                responses={
                    "build_global_glossary": "# 全书术语表\n\n## 第一章·绪论\n- DBMS\n",
                    "build_interview_index": "# 面试索引\n\n## 第一章·绪论\n- 什么是 DBMS？\n",
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    run_global_consolidation=True,
                ),
                llm_backend=backend,
            )

            runner.run()

            global_calls = [item for item in (backend.calls or []) if item["agent_name"] == "build_global_glossary"]
            self.assertEqual(len(global_calls), 1)
            chapters_payload = global_calls[0]["payload"]["chapters"]
            self.assertEqual([chapter["chapter_id"] for chapter in chapters_payload], ["第一章·绪论"])

    def test_clean_output_removes_stale_course_files_before_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint()
            course_dir = output_dir / "courses" / blueprint["course_id"]
            stale_file = course_dir / "stale.txt"
            input_dir.mkdir()
            stale_file.parent.mkdir(parents=True)
            stale_file.write_text("old", encoding="utf-8")
            (input_dir / "第一章·绪论.md").write_text("数据库系统由数据库、硬件、软件和人员组成。", encoding="utf-8")

            backend = StubLLMBackend(
                responses={
                    "curriculum_anchor": {"chapter_summary": "绪论主题", "anchors": []},
                    "gap_fill": {"candidates": []},
                    "compose_pack": {
                        "files": {
                            "01-精讲.md": "# 精讲\n",
                            "02-术语与定义.md": "# 术语\n",
                            "03-面试问答.md": "# 面试问答\n",
                            "04-跨章关联.md": "# 跨章关联\n",
                            "05-疑点与待核.md": "# 疑点与待核\n",
                        }
                    },
                    "canonicalize": {"global_glossary": "# g\n", "interview_index": "# i\n"},
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    clean_output=True,
                    course_blueprint=blueprint,
                ),
                llm_backend=backend,
            )

            runner.run()

            self.assertFalse(stale_file.exists())
            self.assertFalse((self._chapter_dir(output_dir, blueprint) / "review_report.json").exists())

    def test_compose_payload_uses_slim_transcript_view(self) -> None:
        backend = StubLLMBackend(
            responses={
                "canonicalize": {"global_glossary": "# g\n", "interview_index": "# i\n"},
            }
        )
        blueprint = make_blueprint()
        runner = PipelineRunner(
            config=PipelineConfig(input_dir=Path("."), output_dir=Path("."), course_blueprint=blueprint),
            llm_backend=backend,
        )

        normalized = {
            "chapter_id": "第一章·绪论",
            "chunks": [
                {
                    "chunk_id": "chunk-001",
                    "raw_text": "raw content",
                    "clean_text": "clean content",
                    "speaker_role": "lecturer",
                    "noise_flags": ["filler"],
                }
            ],
        }
        topic_map = {"chapter_summary": "summary", "anchors": []}
        augmentation = {"candidates": []}

        payload = runner._build_pack_payload(
            chapter_blueprint=blueprint["chapters"][0],
            normalized=normalized,
            topic_map=topic_map,
            augmentation=augmentation,
        )

        chunk = payload["transcript_evidence"]["chunks"][0]
        self.assertEqual(chunk["clean_text"], "clean content")
        self.assertNotIn("raw_text", chunk)
        self.assertEqual(payload["chapter_blueprint"]["chapter_id"], "第一章·绪论")

    def test_explicit_review_does_not_move_chapter_to_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(review_mode="strict")
            input_dir.mkdir()

            (input_dir / "第一章·绪论.md").write_text(
                "数据库完整性包括实体完整性、参照完整性和用户定义完整性。",
                encoding="utf-8",
            )

            backend = StubLLMBackend(
                responses={
                    "curriculum_anchor": {"chapter_summary": "完整性主题映射", "anchors": []},
                    "gap_fill": {
                        "candidates": [
                            {
                                "claim": "存在低置信度推断。",
                                "source_type": "inference",
                                "confidence": "low",
                                "support": "教材常识补全",
                                "allowed_in_final": True,
                            }
                        ]
                    },
                    "compose_pack": {
                        "files": {
                            "01-精讲.md": "# 精讲\n\n内容。",
                            "02-术语与定义.md": "# 术语\n\n内容。",
                            "03-面试问答.md": "# 面试问答\n\n内容。",
                            "04-跨章关联.md": "# 跨章关联\n\n内容。",
                            "05-疑点与待核.md": "# 疑点与待核\n\n内容。",
                        }
                    },
                    "review": {
                        "status": "needs_attention",
                        "issues": [
                            {
                                "severity": "high",
                                "issue_type": "unsupported_claim",
                                "location": "01-精讲.md",
                                "fix_hint": "删除无证据扩写。",
                            }
                        ],
                    },
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    enable_review=True,
                ),
                llm_backend=backend,
            )

            runner.run()

            quarantined = output_dir / "courses" / blueprint["course_id"] / "quarantine" / "第一章·绪论"
            active = self._chapter_dir(output_dir, blueprint)

            self.assertFalse(quarantined.exists())
            self.assertTrue(active.exists())
            report = json.loads((active / "review_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "needs_attention")

    def test_default_run_skips_review_even_when_risk_signals_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(target_output="standard_knowledge_pack")
            input_dir.mkdir()

            (input_dir / "第一章·绪论.md").write_text(
                "数据库系统由数据库、硬件、软件和人员组成。",
                encoding="utf-8",
            )

            backend = StubLLMBackend(
                responses={
                    "curriculum_anchor": {
                        "chapter_summary": "绪论主题",
                        "anchors": [
                            {
                                "canonical_topic": "数据库系统组成",
                                "coverage_status": "covered",
                                "supporting_chunk_ids": ["chunk-001"],
                                "missing_expected_points": [],
                            }
                        ],
                    },
                    "gap_fill": {
                        "candidates": [
                            {
                                "claim": "数据库系统由数据库、DBMS、应用程序和人员组成。",
                                "source_type": "transcript",
                                "confidence": "high",
                                "support": "chunk-001",
                                "allowed_in_final": True,
                            }
                        ]
                    },
                    "compose_pack": {
                        "files": {
                            "01-精讲.md": "# 精讲\n\n内容。",
                            "02-术语与定义.md": "# 术语\n\n内容。",
                            "03-面试问答.md": "# 面试问答\n\n内容。",
                            "04-跨章关联.md": "# 跨章关联\n\n内容。",
                            "05-疑点与待核.md": "# 疑点与待核\n\n- 暂无待核。",
                        }
                    },
                    "review": {"status": "approved", "issues": []},
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(input_dir=input_dir, output_dir=output_dir, course_blueprint=blueprint),
                llm_backend=backend,
            )

            runner.run()

            called_agents = [item["agent_name"] for item in backend.calls or []]
            self.assertNotIn("review", called_agents)
            self.assertFalse((self._chapter_dir(output_dir, blueprint) / "review_report.json").exists())
            self.assertFalse((output_dir / "courses" / blueprint["course_id"] / "global" / "global_glossary.md").exists())

    def test_explicit_review_runs_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(review_mode="standard")
            input_dir.mkdir()

            (input_dir / "第一章·绪论.md").write_text(
                "数据库系统由数据库、硬件、软件和人员组成。",
                encoding="utf-8",
            )

            backend = StubLLMBackend(
                responses={
                    "curriculum_anchor": {"chapter_summary": "绪论主题", "anchors": []},
                    "gap_fill": {"candidates": []},
                    "compose_pack": {
                        "files": {
                            "01-精讲.md": "# 精讲\n",
                            "02-术语与定义.md": "# 术语\n",
                            "03-面试问答.md": "# 面试问答\n",
                            "04-跨章关联.md": "# 跨章关联\n",
                            "05-疑点与待核.md": "# 疑点与待核\n",
                        }
                    },
                    "review": {"status": "approved", "issues": []},
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    enable_review=True,
                ),
                llm_backend=backend,
            )

            runner.run()

            called_agents = [item["agent_name"] for item in backend.calls or []]
            self.assertIn("review", called_agents)
            report = json.loads((self._chapter_dir(output_dir, blueprint) / "review_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "approved")

    def test_manual_global_consolidation_builds_global_outputs_from_existing_chapters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(target_output="standard_knowledge_pack")
            course_dir = output_dir / "courses" / blueprint["course_id"]
            chapter_dir = self._chapter_dir(output_dir, blueprint)
            notebooklm_dir = chapter_dir / "notebooklm"
            notebooklm_dir.mkdir(parents=True)
            input_dir.mkdir()

            course_dir.mkdir(parents=True, exist_ok=True)
            (course_dir / "course_blueprint.json").write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")
            (notebooklm_dir / "02-术语与定义.md").write_text("# 术语\n\n- DBMS\n", encoding="utf-8")
            (notebooklm_dir / "03-面试问答.md").write_text("# 面试问答\n\n- 什么是 DBMS？\n", encoding="utf-8")
            (notebooklm_dir / "04-跨章关联.md").write_text("# 跨章关联\n\n- 与后续章节关联。\n", encoding="utf-8")

            backend = StubLLMBackend(
                responses={
                    "build_global_glossary": "# 全书术语表\n\n## 第一章·绪论\n- DBMS\n",
                    "build_interview_index": "# 面试索引\n\n## 第一章·绪论\n- 什么是 DBMS？\n",
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    run_global_consolidation=True,
                ),
                llm_backend=backend,
            )

            runner.run()

            called_agents = [item["agent_name"] for item in backend.calls or []]
            self.assertEqual(called_agents, ["build_global_glossary", "build_interview_index"])
            self.assertTrue((course_dir / "global" / "global_glossary.md").exists())
            self.assertTrue((course_dir / "global" / "interview_index.md").exists())

    def test_manual_global_consolidation_accepts_deep_dive_chapters_without_interview_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(target_output="lecture_deep_dive")
            course_dir = output_dir / "courses" / blueprint["course_id"]
            chapter_dir = self._chapter_dir(output_dir, blueprint)
            notebooklm_dir = chapter_dir / "notebooklm"
            notebooklm_dir.mkdir(parents=True)
            input_dir.mkdir()

            course_dir.mkdir(parents=True, exist_ok=True)
            (course_dir / "course_blueprint.json").write_text(
                json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (notebooklm_dir / "02-术语与定义.md").write_text("# 术语\n\n- DBMS\n", encoding="utf-8")
            (notebooklm_dir / "04-跨章关联.md").write_text("# 跨章关联\n\n- 与后续章节关联。\n", encoding="utf-8")

            backend = StubLLMBackend(
                responses={
                    "build_global_glossary": "# 全书术语表\n\n## 第一章·绪论\n- DBMS\n",
                    "build_interview_index": "# 面试索引\n\n## 第一章·绪论\n- 课堂精讲重点\n",
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    run_global_consolidation=True,
                ),
                llm_backend=backend,
            )

            runner.run()

            called_agents = [item["agent_name"] for item in backend.calls or []]
            self.assertEqual(called_agents, ["build_global_glossary", "build_interview_index"])
            self.assertTrue((course_dir / "global" / "global_glossary.md").exists())
            self.assertTrue((course_dir / "global" / "interview_index.md").exists())

    def test_manual_global_consolidation_with_heuristic_backend_writes_global_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(target_output="standard_knowledge_pack")
            course_dir = output_dir / "courses" / blueprint["course_id"]
            chapter_dir = self._chapter_dir(output_dir, blueprint)
            notebooklm_dir = chapter_dir / "notebooklm"
            notebooklm_dir.mkdir(parents=True)
            input_dir.mkdir()

            course_dir.mkdir(parents=True, exist_ok=True)
            (course_dir / "course_blueprint.json").write_text(
                json.dumps(blueprint, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (notebooklm_dir / "02-术语与定义.md").write_text("# 术语\n\n- DBMS\n", encoding="utf-8")
            (notebooklm_dir / "03-面试问答.md").write_text("# 面试问答\n\n- 什么是 DBMS？\n", encoding="utf-8")
            (notebooklm_dir / "04-跨章关联.md").write_text("# 跨章关联\n\n- 与后续章节关联。\n", encoding="utf-8")

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    run_global_consolidation=True,
                ),
                llm_backend=HeuristicLLMBackend(),
            )

            runner.run()

            self.assertTrue((course_dir / "global" / "global_glossary.md").exists())
            self.assertTrue((course_dir / "global" / "interview_index.md").exists())

    def test_manual_global_consolidation_collects_runtime_fallback_chapter_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = finalize_blueprint(
                {
                    "course_name": "数据库系统概论",
                    "source_type": "published_textbook",
                    "book": {
                        "title": "数据库系统概论",
                        "authors": ["王珊", "萨师煊"],
                        "edition": "第5版",
                        "publisher": "高等教育出版社",
                        "isbn": "",
                    },
                    "chapters": [
                        {
                            "chapter_id": "toc-chapter-11",
                            "title": "目录章节十一",
                            "aliases": [],
                            "expected_topics": [],
                        }
                    ],
                    "policy": {
                        "augmentation_mode": "conservative",
                        "review_mode": "light",
                        "target_output": "interview_knowledge_base",
                    },
                    "provenance": {
                        "metadata": {"strategy": "user_input"},
                        "chapter_structure": {"strategy": "user_toc"},
                    },
                }
            )
            course_dir = output_dir / "courses" / blueprint["course_id"]
            fallback_chapter_id = "第十一章·数据库恢复技术"
            notebooklm_dir = course_dir / "chapters" / fallback_chapter_id / "notebooklm"
            notebooklm_dir.mkdir(parents=True)
            input_dir.mkdir()

            course_dir.mkdir(parents=True, exist_ok=True)
            (course_dir / "course_blueprint.json").write_text(
                json.dumps(blueprint, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (course_dir / "runtime_state.json").write_text(
                json.dumps(
                    {
                        "course_id": blueprint["course_id"],
                        "blueprint_hash": blueprint["blueprint_hash"],
                        "provider": "stub",
                        "default_model": "",
                        "stage_models": {},
                        "pipeline_signature": PIPELINE_SIGNATURE,
                        "review_enabled": False,
                        "review_mode": blueprint["policy"]["review_mode"],
                        "target_output": blueprint["policy"]["target_output"],
                        "run_identity": {
                            "review_enabled": False,
                            "review_mode": blueprint["policy"]["review_mode"],
                            "target_output": blueprint["policy"]["target_output"],
                        },
                        "chapters": {
                            fallback_chapter_id: {
                                "steps": {
                                    "write_terms": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": blueprint["blueprint_hash"],
                                        "pipeline_signature": PIPELINE_SIGNATURE,
                                    },
                                    "write_interview_qa": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": blueprint["blueprint_hash"],
                                        "pipeline_signature": PIPELINE_SIGNATURE,
                                    },
                                    "write_cross_links": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": blueprint["blueprint_hash"],
                                        "pipeline_signature": PIPELINE_SIGNATURE,
                                    },
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
            (notebooklm_dir / "02-术语与定义.md").write_text("# 术语\n\n- WAL\n", encoding="utf-8")
            (notebooklm_dir / "03-面试问答.md").write_text("# 面试问答\n\n- 什么是 WAL？\n", encoding="utf-8")
            (notebooklm_dir / "04-跨章关联.md").write_text("# 跨章关联\n\n- 与日志恢复关联。\n", encoding="utf-8")

            backend = StubLLMBackend(
                responses={
                    "build_global_glossary": "# 全书术语表\n\n## 第十一章·数据库恢复技术\n- WAL\n",
                    "build_interview_index": "# 面试索引\n\n## 第十一章·数据库恢复技术\n- 什么是 WAL？\n",
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    run_global_consolidation=True,
                ),
                llm_backend=backend,
            )

            runner.run()

            self.assertTrue((course_dir / "global" / "global_glossary.md").exists())
            self.assertTrue((course_dir / "global" / "interview_index.md").exists())

    def test_manual_global_consolidation_excludes_stale_runtime_chapter_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(target_output="standard_knowledge_pack")
            course_dir = output_dir / "courses" / blueprint["course_id"]
            current_notebooklm_dir = self._chapter_dir(output_dir, blueprint) / "notebooklm"
            stale_notebooklm_dir = course_dir / "chapters" / "旧版章节·已废弃" / "notebooklm"
            input_dir.mkdir()
            current_notebooklm_dir.mkdir(parents=True)
            stale_notebooklm_dir.mkdir(parents=True)

            runtime_state = {
                "course_id": blueprint["course_id"],
                "blueprint_hash": blueprint["blueprint_hash"],
                "provider": "stub",
                "default_model": "",
                "stage_models": {},
                "pipeline_signature": PIPELINE_SIGNATURE,
                "review_enabled": False,
                "review_mode": blueprint["policy"]["review_mode"],
                "target_output": blueprint["policy"]["target_output"],
                "run_identity": {
                    "review_enabled": False,
                    "review_mode": blueprint["policy"]["review_mode"],
                    "target_output": blueprint["policy"]["target_output"],
                },
                "chapters": {
                    "第一章·绪论": {
                        "steps": {
                            "write_terms": {
                                "status": "completed",
                                "updated_at": "t",
                                "blueprint_hash": blueprint["blueprint_hash"],
                                "pipeline_signature": PIPELINE_SIGNATURE,
                            },
                            "write_interview_qa": {
                                "status": "completed",
                                "updated_at": "t",
                                "blueprint_hash": blueprint["blueprint_hash"],
                                "pipeline_signature": PIPELINE_SIGNATURE,
                            },
                            "write_cross_links": {
                                "status": "completed",
                                "updated_at": "t",
                                "blueprint_hash": blueprint["blueprint_hash"],
                                "pipeline_signature": PIPELINE_SIGNATURE,
                            },
                        }
                    }
                },
                "global": {},
                "last_error": None,
            }

            course_dir.mkdir(parents=True, exist_ok=True)
            (course_dir / "course_blueprint.json").write_text(
                json.dumps(blueprint, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (course_dir / "runtime_state.json").write_text(
                json.dumps(runtime_state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            (current_notebooklm_dir / "02-术语与定义.md").write_text("# 术语\n\n- DBMS\n", encoding="utf-8")
            (current_notebooklm_dir / "03-面试问答.md").write_text("# 面试问答\n\n- 什么是 DBMS？\n", encoding="utf-8")
            (current_notebooklm_dir / "04-跨章关联.md").write_text("# 跨章关联\n\n- 与后续章节关联。\n", encoding="utf-8")

            (stale_notebooklm_dir / "02-术语与定义.md").write_text("# 术语\n\n- STALE\n", encoding="utf-8")
            (stale_notebooklm_dir / "03-面试问答.md").write_text("# 面试问答\n\n- 什么是 STALE？\n", encoding="utf-8")
            (stale_notebooklm_dir / "04-跨章关联.md").write_text("# 跨章关联\n\n- 这是旧章节。\n", encoding="utf-8")

            backend = StubLLMBackend(
                responses={
                    "build_global_glossary": "# 全书术语表\n\n## 第一章·绪论\n- DBMS\n",
                    "build_interview_index": "# 面试索引\n\n## 第一章·绪论\n- 什么是 DBMS？\n",
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    course_blueprint=blueprint,
                    run_global_consolidation=True,
                ),
                llm_backend=backend,
            )

            runner.run()

            global_calls = [item for item in (backend.calls or []) if item["agent_name"] == "build_global_glossary"]
            self.assertEqual(len(global_calls), 1)
            chapters_payload = global_calls[0]["payload"]["chapters"]
            self.assertEqual([chapter["chapter_id"] for chapter in chapters_payload], ["第一章·绪论"])
            self.assertTrue((course_dir / "global" / "global_glossary.md").exists())
            self.assertTrue((course_dir / "global" / "interview_index.md").exists())

    def test_heuristic_compose_pack_respects_target_output_style(self) -> None:
        backend = HeuristicLLMBackend()
        payload = {
            "course_blueprint": {
                "policy": {"target_output": "lecture_deep_dive"},
                "chapters": [{"chapter_id": "第一章·绪论", "title": "绪论"}],
            },
            "chapter_blueprint": {"chapter_id": "第一章·绪论", "title": "绪论", "expected_topics": ["数据库系统组成"]},
            "transcript_evidence": {
                "chapter_id": "第一章·绪论",
                "chunks": [
                    {
                        "chunk_id": "chunk-001",
                        "clean_text": "数据库系统由数据库、硬件、软件和人员组成。",
                        "speaker_role": "lecturer",
                        "noise_flags": [],
                    }
                ],
            },
            "topic_anchor_map": {"anchors": []},
            "augmentation_digest": {"candidates": []},
        }

        lecture_pack = backend.generate_json("compose_pack", "", payload)
        interview_pack = backend.generate_json(
            "compose_pack",
            "",
            {
                **payload,
                "course_blueprint": {
                    "policy": {"target_output": "interview_knowledge_base"},
                    "chapters": [{"chapter_id": "第一章·绪论", "title": "绪论"}],
                },
            },
        )

        self.assertIn("课堂精讲主线", lecture_pack["files"]["01-精讲.md"])
        self.assertIn("面试表达", interview_pack["files"]["03-面试问答.md"])
        self.assertNotEqual(
            lecture_pack["files"]["01-精讲.md"],
            interview_pack["files"]["01-精讲.md"],
        )

    def test_pipeline_signature_change_invalidates_existing_compose_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint(target_output="standard_knowledge_pack")
            course_dir = output_dir / "courses" / blueprint["course_id"]
            chapter_dir = self._chapter_dir(output_dir, blueprint)
            intermediate_dir = chapter_dir / "intermediate"
            notebooklm_dir = chapter_dir / "notebooklm"
            input_dir.mkdir()
            intermediate_dir.mkdir(parents=True)
            notebooklm_dir.mkdir(parents=True)

            (input_dir / "第一章·绪论.md").write_text("数据库系统由数据库、硬件、软件和人员组成。", encoding="utf-8")
            (course_dir / "course_blueprint.json").write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")
            (intermediate_dir / "normalized_transcript.json").write_text(
                json.dumps(
                    {
                        "chapter_id": "第一章·绪论",
                        "chunks": [
                            {
                                "chunk_id": "chunk-001",
                                "raw_text": "raw",
                                "clean_text": "数据库系统由数据库、硬件、软件和人员组成。",
                                "speaker_role": "lecturer",
                                "noise_flags": [],
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (intermediate_dir / "topic_anchor_map.json").write_text(
                json.dumps({"chapter_summary": "s", "anchors": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (intermediate_dir / "augmentation_candidates.json").write_text(
                json.dumps({"candidates": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (course_dir / "runtime_state.json").write_text(
                json.dumps(
                    {
                        "course_id": blueprint["course_id"],
                        "blueprint_hash": blueprint["blueprint_hash"],
                        "provider": "stub",
                        "default_model": "",
                        "stage_models": {},
                        "chapters": {
                            "第一章·绪论": {
                                "steps": {
                                    "ingest": {"status": "completed", "updated_at": "t", "blueprint_hash": None},
                                    "curriculum_anchor": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": blueprint["blueprint_hash"],
                                    },
                                    "gap_fill": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": blueprint["blueprint_hash"],
                                    },
                                    "compose_pack": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": blueprint["blueprint_hash"],
                                    },
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
            for file_name in (
                "01-精讲.md",
                "02-术语与定义.md",
                "03-面试问答.md",
                "04-跨章关联.md",
                "05-疑点与待核.md",
            ):
                (notebooklm_dir / file_name).write_text("old", encoding="utf-8")

            backend = StubLLMBackend(
                responses={
                    "curriculum_anchor": {"chapter_summary": "x", "anchors": []},
                    "gap_fill": {"candidates": []},
                    "compose_pack": {
                        "files": {
                            "01-精讲.md": "# 新精讲\n",
                            "02-术语与定义.md": "# 新术语\n",
                            "03-面试问答.md": "# 新问答\n",
                            "04-跨章关联.md": "# 新跨章关联\n",
                            "05-疑点与待核.md": "# 新疑点与待核\n",
                        }
                    },
                    "canonicalize": {"global_glossary": "# g\n", "interview_index": "# i\n"},
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(input_dir=input_dir, output_dir=output_dir, course_blueprint=blueprint),
                llm_backend=backend,
            )

            runner.run()

            called_agents = [item["agent_name"] for item in backend.calls or []]
            self.assertIn("pack_plan", called_agents)
            self.assertIn("write_lecture_note", called_agents)
            self.assertEqual((notebooklm_dir / "01-精讲.md").read_text(encoding="utf-8"), "# 新精讲\n")


if __name__ == "__main__":
    unittest.main()
