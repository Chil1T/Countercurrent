import json
import tempfile
import unittest
from pathlib import Path

from processagent.blueprint import finalize_blueprint
from processagent.pipeline import PipelineConfig, PipelineRunner
from processagent.testing import StubLLMBackend


def make_blueprint(*, review_mode: str = "light", target_output: str = "interview_knowledge_base") -> dict:
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
            "chapters": [
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


class PipelineRunnerTest(unittest.TestCase):
    def _chapter_dir(self, output_dir: Path, blueprint: dict) -> Path:
        return output_dir / "courses" / blueprint["course_id"] / "chapters" / "第一章·绪论"

    def test_run_creates_course_scoped_outputs_and_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint()
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
            self.assertTrue((chapter_dir / "review_report.json").exists())
            self.assertTrue((chapter_dir / "notebooklm" / "01-精讲.md").exists())
            self.assertTrue((course_dir / "global" / "global_glossary.md").exists())

            runtime_state = json.loads((course_dir / "runtime_state.json").read_text(encoding="utf-8"))
            self.assertEqual(runtime_state["blueprint_hash"], blueprint["blueprint_hash"])
            self.assertEqual(runtime_state["chapters"]["第一章·绪论"]["steps"]["compose_pack"]["status"], "completed")

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
            self.assertIn("compose_pack", called_agents)
            self.assertTrue((notebooklm_dir / "01-精讲.md").exists())
            self.assertTrue((chapter_dir / "review_report.json").exists())

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
                                    "ingest": {"status": "completed", "updated_at": "t", "blueprint_hash": None},
                                    "curriculum_anchor": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": old_blueprint["blueprint_hash"],
                                    },
                                    "gap_fill": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": old_blueprint["blueprint_hash"],
                                    },
                                    "compose_pack": {
                                        "status": "completed",
                                        "updated_at": "t",
                                        "blueprint_hash": old_blueprint["blueprint_hash"],
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
            self.assertIn("compose_pack", called_agents)

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
            self.assertTrue((self._chapter_dir(output_dir, blueprint) / "review_report.json").exists())

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

    def test_critical_review_moves_chapter_to_quarantine(self) -> None:
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
                        "status": "quarantine",
                        "issues": [
                            {
                                "severity": "high",
                                "issue_type": "unsupported_claim",
                                "location": "01-精讲.md",
                                "fix_hint": "删除无证据扩写。",
                            }
                        ],
                    },
                    "canonicalize": {
                        "global_glossary": "# 全书术语表\n",
                        "interview_index": "# 面试索引\n",
                    },
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(input_dir=input_dir, output_dir=output_dir, course_blueprint=blueprint),
                llm_backend=backend,
            )

            runner.run()

            quarantined = output_dir / "courses" / blueprint["course_id"] / "quarantine" / "第一章·绪论"
            active = self._chapter_dir(output_dir, blueprint)

            self.assertTrue(quarantined.exists())
            self.assertFalse(active.exists())
            report = json.loads((quarantined / "review_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "quarantine")

    def test_light_review_is_skipped_when_no_risk_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "out"
            blueprint = make_blueprint()
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
                    "canonicalize": {
                        "global_glossary": "# 全书术语表\n",
                        "interview_index": "# 面试索引\n",
                    },
                }
            )

            runner = PipelineRunner(
                config=PipelineConfig(input_dir=input_dir, output_dir=output_dir, course_blueprint=blueprint),
                llm_backend=backend,
            )

            runner.run()

            report = json.loads((self._chapter_dir(output_dir, blueprint) / "review_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "skipped")
            self.assertEqual(report["reason"], "light_review_not_needed")
            called_agents = [item["agent_name"] for item in backend.calls or []]
            self.assertNotIn("review", called_agents)


if __name__ == "__main__":
    unittest.main()
