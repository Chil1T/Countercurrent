import os
import tempfile
import unittest
from pathlib import Path

from processagent.cli import load_dotenv_file


class EnvLoadingTest(unittest.TestCase):
    def test_load_dotenv_file_sets_missing_environment_variables(self) -> None:
        original = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                env_file = Path(tmp) / ".env"
                env_file.write_text(
                    "# comment\nOPENAI_API_KEY=test-key\nEMPTY_VALUE=\n",
                    encoding="utf-8",
                )

                load_dotenv_file(env_file)

                self.assertEqual(os.environ["OPENAI_API_KEY"], "test-key")
                self.assertEqual(os.environ["EMPTY_VALUE"], "")
        finally:
            os.environ.pop("EMPTY_VALUE", None)
            if original is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = original


if __name__ == "__main__":
    unittest.main()
