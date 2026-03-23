import unittest

from processagent.pipeline import IngestAgent


class IngestAgentTest(unittest.TestCase):
    def test_ingest_normalizes_and_chunks_transcript(self) -> None:
        agent = IngestAgent()

        result = agent.run(
            chapter_id="第一章·绪论",
            transcript_text=(
                "嗯 我们先讲数据库发展阶段。"
                "人工管理阶段数据不能共享。"
                "\n\n"
                "然后 文件系统阶段有数据冗余和不一致问题。"
                "啊 数据库阶段由 DBMS 管理。"
            ),
        )

        self.assertEqual(result["chapter_id"], "第一章·绪论")
        self.assertGreaterEqual(len(result["chunks"]), 2)
        first_chunk = result["chunks"][0]
        self.assertEqual(first_chunk["chunk_id"], "chunk-001")
        self.assertIn("数据库发展阶段", first_chunk["clean_text"])
        self.assertIn("filler", first_chunk["noise_flags"])


if __name__ == "__main__":
    unittest.main()
