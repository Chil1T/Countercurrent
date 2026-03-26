import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "start-gui-local.ps1"


class GuiDevScriptTest(unittest.TestCase):
    def test_start_gui_local_dry_run_prints_expected_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "server").mkdir()
            (workspace / "web").mkdir()
            (workspace / "server" / "requirements.txt").write_text(
                "fastapi>=0.115,<1\n",
                encoding="utf-8",
            )
            (workspace / "web" / "package.json").write_text(
                '{"name":"web","private":true}',
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(SCRIPT_PATH),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-DryRun",
                    "-BackendPort",
                    "8100",
                    "-FrontendPort",
                    "3100",
                    "-SkipBackendInstall",
                    "-SkipFrontendInstall",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("backend-dev.log", result.stdout)
            self.assertIn("frontend-dev.log", result.stdout)
            self.assertIn("http://127.0.0.1:8100/healthz", result.stdout)
            self.assertIn("http://127.0.0.1:3100/courses/new/input", result.stdout)
            self.assertTrue((workspace / "out" / "_gui").exists())

    def test_start_gui_local_requires_server_and_web_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(SCRIPT_PATH),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-DryRun",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("workspace root", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
