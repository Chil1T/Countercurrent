import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.app.main import create_app


class AppBootstrapTests(unittest.TestCase):
    def test_create_app_uses_repo_root_defaults_instead_of_process_cwd(self) -> None:
        fake_cwd = tempfile.TemporaryDirectory()
        repo_root = Path(__file__).resolve().parents[2]

        try:
            with patch("server.app.main.Path.cwd", return_value=Path(fake_cwd.name)):
                with patch("server.app.main.LocalProcessRunner") as runner_cls:
                    create_app()

            _, kwargs = runner_cls.call_args
            self.assertEqual(kwargs["workspace_root"], repo_root)
            self.assertEqual(kwargs["log_root"], repo_root / "out" / "_gui" / "runs")
        finally:
            fake_cwd.cleanup()
