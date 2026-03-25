import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from processagent.blueprint import build_course_id
from processagent.cli import _build_blueprint

REPO_ROOT = Path(__file__).resolve().parents[1]


class _RecordingBlueprintBackend:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_json(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, object],
        model_override: str | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "agent_name": agent_name,
                "prompt": prompt,
                "payload": payload,
                "model_override": model_override,
            }
        )
        return {
            "course_name": "数据库系统概论",
            "chapters": [
                {
                    "chapter_id": "第一章·绪论",
                    "title": "绪论",
                    "aliases": ["第一章·绪论"],
                    "expected_topics": [],
                }
            ],
            "provenance": {
                "chapter_structure": {"strategy": "llm_completed"},
            },
        }


class CliTest(unittest.TestCase):
    def test_build_blueprint_applies_blueprint_builder_model_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            input_dir.mkdir()
            (input_dir / "第一章·绪论.md").write_text("数据库系统由数据库组成。", encoding="utf-8")

            backend = _RecordingBlueprintBackend()

            blueprint = _build_blueprint(
                Namespace(
                    input_dir=input_dir,
                    book_title="数据库系统概论",
                    toc_file=None,
                    toc_text=None,
                    author=None,
                    edition=None,
                    publisher=None,
                    isbn=None,
                    blueprint_builder_model="gpt-5.4-mini-blueprint",
                ),
                backend,
            )

            self.assertEqual(blueprint["course_name"], "数据库系统概论")
            self.assertEqual(backend.calls[0]["agent_name"], "blueprint_builder")
            self.assertEqual(backend.calls[0]["model_override"], "gpt-5.4-mini-blueprint")

    def test_build_blueprint_subcommand_writes_course_blueprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "generated"
            toc_file = root / "toc.txt"
            input_dir.mkdir()

            (input_dir / "第一章·绪论.md").write_text(
                "数据库系统由数据库、硬件、软件和人员组成。",
                encoding="utf-8",
            )
            toc_file.write_text("第一章 绪论\n第二章 关系数据库\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "processagent.cli",
                    "build-blueprint",
                    "--book-title",
                    "数据库系统概论",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--toc-file",
                    str(toc_file),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            course_dirs = list((output_dir / "courses").iterdir())
            self.assertEqual(len(course_dirs), 1)
            blueprint_path = course_dirs[0] / "course_blueprint.json"
            self.assertTrue(blueprint_path.exists())

            blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
            self.assertEqual(blueprint["book"]["title"], "数据库系统概论")
            self.assertEqual(blueprint["source_type"], "published_textbook")
            self.assertEqual(len(blueprint["chapters"]), 2)

    def test_run_course_subcommand_runs_with_stub_scenario_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "generated"
            scenario_file = root / "scenario.json"
            toc_file = root / "toc.txt"
            input_dir.mkdir()

            (input_dir / "第一章·绪论.md").write_text(
                "数据库系统由数据库、硬件、软件和人员组成。",
                encoding="utf-8",
            )
            toc_file.write_text("第一章 绪论\n", encoding="utf-8")

            scenario_file.write_text(
                json.dumps(
                    {
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
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "processagent.cli",
                    "run-course",
                    "--book-title",
                    "数据库系统概论",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--toc-file",
                    str(toc_file),
                    "--backend",
                    "stub",
                    "--stub-scenario",
                    str(scenario_file),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            course_dirs = list((output_dir / "courses").iterdir())
            self.assertEqual(len(course_dirs), 1)
            course_dir = course_dirs[0]
            chapter_dirs = list((course_dir / "chapters").iterdir())
            self.assertEqual(len(chapter_dirs), 1)
            self.assertTrue((chapter_dirs[0] / "notebooklm" / "01-精讲.md").exists())
            self.assertFalse((chapter_dirs[0] / "review_report.json").exists())
            self.assertFalse((course_dir / "global" / "global_glossary.md").exists())

    def test_run_course_applies_policy_overrides_to_persisted_blueprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "generated"
            scenario_file = root / "scenario.json"
            toc_file = root / "toc.txt"
            input_dir.mkdir()

            (input_dir / "第一章·绪论.md").write_text(
                "数据库系统由数据库、硬件、软件和人员组成。",
                encoding="utf-8",
            )
            toc_file.write_text("第一章 绪论\n", encoding="utf-8")
            scenario_file.write_text(
                json.dumps(
                    {
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
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "processagent.cli",
                    "run-course",
                    "--book-title",
                    "数据库系统概论",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--toc-file",
                    str(toc_file),
                    "--backend",
                    "stub",
                    "--stub-scenario",
                    str(scenario_file),
                    "--review-mode",
                    "standard",
                    "--target-output",
                    "lecture_deep_dive",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            course_dir = next((output_dir / "courses").iterdir())
            blueprint = json.loads((course_dir / "course_blueprint.json").read_text(encoding="utf-8"))
            self.assertEqual(blueprint["policy"]["review_mode"], "standard")
            self.assertEqual(blueprint["policy"]["target_output"], "lecture_deep_dive")

    def test_run_course_with_enable_review_writes_review_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "generated"
            scenario_file = root / "scenario.json"
            toc_file = root / "toc.txt"
            input_dir.mkdir()

            (input_dir / "第一章·绪论.md").write_text(
                "数据库系统由数据库、硬件、软件和人员组成。",
                encoding="utf-8",
            )
            toc_file.write_text("第一章 绪论\n", encoding="utf-8")
            scenario_file.write_text(
                json.dumps(
                    {
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
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "processagent.cli",
                    "run-course",
                    "--book-title",
                    "数据库系统概论",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--toc-file",
                    str(toc_file),
                    "--backend",
                    "stub",
                    "--stub-scenario",
                    str(scenario_file),
                    "--enable-review",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            course_dir = next((output_dir / "courses").iterdir())
            chapter_dir = next((course_dir / "chapters").iterdir())
            self.assertTrue((chapter_dir / "review_report.json").exists())

    def test_resume_course_uses_persisted_pipeline_identity_from_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "generated"
            scenario_file = root / "scenario.json"
            toc_file = root / "toc.txt"
            input_dir.mkdir()

            (input_dir / "第一章·绪论.md").write_text(
                "数据库系统由数据库、硬件、软件和人员组成。",
                encoding="utf-8",
            )
            toc_file.write_text("第一章 绪论\n", encoding="utf-8")
            scenario_file.write_text(
                json.dumps(
                    {
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
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            first_run = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "processagent.cli",
                    "run-course",
                    "--book-title",
                    "数据库系统概论",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--toc-file",
                    str(toc_file),
                    "--backend",
                    "stub",
                    "--stub-scenario",
                    str(scenario_file),
                    "--review-mode",
                    "standard",
                    "--target-output",
                    "interview_knowledge_base",
                    "--enable-review",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(first_run.returncode, 0, msg=first_run.stderr)
            course_dir = next((output_dir / "courses").iterdir())
            chapter_dir = next((course_dir / "chapters").iterdir())
            review_path = chapter_dir / "review_report.json"
            self.assertTrue(review_path.exists())

            review_path.unlink()
            runtime_state_path = course_dir / "runtime_state.json"
            runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
            self.assertTrue(runtime_state["run_identity"]["review_enabled"])
            self.assertEqual(runtime_state["run_identity"]["review_mode"], "standard")
            self.assertEqual(runtime_state["run_identity"]["target_output"], "interview_knowledge_base")
            runtime_state["chapters"][chapter_dir.name]["steps"].pop("review", None)
            runtime_state_path.write_text(json.dumps(runtime_state, ensure_ascii=False, indent=2), encoding="utf-8")

            resume = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "processagent.cli",
                    "resume-course",
                    "--book-title",
                    "数据库系统概论",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--toc-file",
                    str(toc_file),
                    "--backend",
                    "stub",
                    "--stub-scenario",
                    str(scenario_file),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(resume.returncode, 0, msg=resume.stderr)
            self.assertTrue(review_path.exists())
            refreshed_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
            self.assertTrue(refreshed_state["run_identity"]["review_enabled"])
            self.assertEqual(refreshed_state["run_identity"]["review_mode"], "standard")
            self.assertEqual(refreshed_state["run_identity"]["target_output"], "interview_knowledge_base")

    def test_resume_course_rejects_pipeline_identity_override_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            output_dir = root / "generated"
            input_dir.mkdir()
            (input_dir / "第一章·绪论.md").write_text("数据库系统由数据库、硬件、软件和人员组成。", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "processagent.cli",
                    "resume-course",
                    "--book-title",
                    "数据库系统概论",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--target-output",
                    "lecture_deep_dive",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unrecognized arguments: --target-output", result.stderr)

    def test_build_global_subcommand_generates_global_outputs_from_existing_course(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "generated"
            course_dir = output_dir / "courses" / build_course_id("数据库系统概论")
            chapter_dir = course_dir / "chapters" / "第一章·绪论" / "notebooklm"
            scenario_file = root / "scenario.json"

            chapter_dir.mkdir(parents=True)
            (course_dir / "course_blueprint.json").write_text(
                json.dumps(
                    {
                        "course_id": build_course_id("数据库系统概论"),
                        "course_name": "数据库系统概论",
                        "chapters": [{"chapter_id": "第一章·绪论", "title": "绪论"}],
                        "policy": {"target_output": "interview_knowledge_base", "review_mode": "light"},
                        "blueprint_hash": "hash",
                        "source_type": "published_textbook",
                        "book": {"title": "数据库系统概论"},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (chapter_dir / "02-术语与定义.md").write_text("# 术语\n\n- DBMS\n", encoding="utf-8")
            (chapter_dir / "03-面试问答.md").write_text("# 面试问答\n\n- 什么是 DBMS？\n", encoding="utf-8")
            (chapter_dir / "04-跨章关联.md").write_text("# 跨章关联\n\n- 与后续章节关联。\n", encoding="utf-8")
            scenario_file.write_text(
                json.dumps(
                    {
                        "build_global_glossary": "# glossary\n",
                        "build_interview_index": "# index\n",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "processagent.cli",
                    "build-global",
                    "--book-title",
                    "数据库系统概论",
                    "--output-dir",
                    str(output_dir),
                    "--backend",
                    "stub",
                    "--stub-scenario",
                    str(scenario_file),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((course_dir / "global" / "global_glossary.md").exists())
            self.assertTrue((course_dir / "global" / "interview_index.md").exists())


if __name__ == "__main__":
    unittest.main()
