import tempfile
import unittest
from pathlib import Path

from processagent.testing import StubLLMBackend


class BlueprintBuilderTest(unittest.TestCase):
    def test_build_blueprint_from_toc_prefers_deterministic_structure(self) -> None:
        from processagent.bootstrap import bootstrap_course_blueprint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            input_dir.mkdir()
            (input_dir / "第一章·绪论.md").write_text("数据库系统由数据库、软件和人员组成。", encoding="utf-8")
            (input_dir / "第二章·关系数据库.md").write_text("关系模型是数据库系统概论核心内容。", encoding="utf-8")

            blueprint = bootstrap_course_blueprint(
                input_dir=input_dir,
                book_title="数据库系统概论",
                toc_text="第一章 绪论\n第二章 关系数据库\n",
                llm_backend=None,
            )

            self.assertEqual(blueprint["source_type"], "published_textbook")
            self.assertEqual(blueprint["book"]["title"], "数据库系统概论")
            self.assertEqual([chapter["title"] for chapter in blueprint["chapters"]], ["绪论", "关系数据库"])
            self.assertEqual(
                blueprint["provenance"]["chapter_structure"]["strategy"],
                "user_toc",
            )

    def test_build_blueprint_falls_back_to_llm_when_structure_missing(self) -> None:
        from processagent.bootstrap import bootstrap_course_blueprint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "captions"
            input_dir.mkdir()
            (input_dir / "lecture-01.md").write_text("这一讲介绍数据库系统概论的基本概念。", encoding="utf-8")

            backend = StubLLMBackend(
                responses={
                    "blueprint_builder": {
                        "course_name": "数据库系统概论",
                        "chapters": [
                            {
                                "chapter_id": "chapter-01",
                                "title": "绪论",
                                "aliases": ["第一章·绪论"],
                                "expected_topics": ["数据库系统组成", "数据模型"],
                            }
                        ],
                        "provenance": {
                            "chapter_structure": {
                                "strategy": "llm_completed",
                            }
                        },
                    }
                }
            )

            blueprint = bootstrap_course_blueprint(
                input_dir=input_dir,
                book_title="数据库系统概论",
                toc_text=None,
                llm_backend=backend,
            )

            self.assertEqual(len(blueprint["chapters"]), 1)
            self.assertEqual(blueprint["chapters"][0]["title"], "绪论")
            self.assertEqual(blueprint["provenance"]["chapter_structure"]["strategy"], "llm_completed")


if __name__ == "__main__":
    unittest.main()
