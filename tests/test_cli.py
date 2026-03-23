import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTest(unittest.TestCase):
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
                cwd=r"C:\Users\ming\Documents\databaseleaning",
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
                        "canonicalize": {
                            "global_glossary": "# glossary\n",
                            "interview_index": "# index\n",
                        },
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
                cwd=r"C:\Users\ming\Documents\databaseleaning",
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            course_dirs = list((output_dir / "courses").iterdir())
            self.assertEqual(len(course_dirs), 1)
            course_dir = course_dirs[0]
            self.assertTrue((course_dir / "global" / "global_glossary.md").exists())
            chapter_dirs = list((course_dir / "chapters").iterdir())
            self.assertEqual(len(chapter_dirs), 1)
            self.assertTrue((chapter_dirs[0] / "notebooklm" / "01-精讲.md").exists())


if __name__ == "__main__":
    unittest.main()
