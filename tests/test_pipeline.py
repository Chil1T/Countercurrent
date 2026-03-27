import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from processagent.blueprint import finalize_blueprint
from processagent.pipeline import EXECUTION_STRATEGY, HOSTED_PRESSURE_STAGES, PIPELINE_SIGNATURE, HeuristicLLMBackend, PipelineConfig, PipelineRunner
from processagent.testing import StubLLMBackend


def make_blueprint(
    *,
    chapters: list[dict] | None = None,
    review_mode: str = "light",
    target_output: str = "interview_knowledge_base",
) -> dict:
    return finalize_blueprint(
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


class PipelineRunnerTest(unittest.TestCase):
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
                "chapter_loop": "serial",
                "writer_loop": "serial",
                "global_consolidation": "serial",
            },
        )

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
