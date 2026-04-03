import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "start-gui-local.ps1"


class GuiDevScriptTest(unittest.TestCase):
    def test_start_gui_local_can_boot_minimal_stack(self) -> None:
        tmp = tempfile.mkdtemp()
        workspace = Path(tmp)
        process: subprocess.Popen[str] | None = None
        stdout_handle = None
        stderr_handle = None
        try:
            server_app = workspace / "server" / "app"
            web_dir = workspace / "web"
            server_app.mkdir(parents=True)
            web_dir.mkdir()
            (workspace / "server" / "requirements.txt").write_text("", encoding="utf-8")
            (web_dir / "package.json").write_text(
                '{"name":"web","private":true}',
                encoding="utf-8",
            )
            (server_app / "__init__.py").write_text("", encoding="utf-8")
            (server_app / "main.py").write_text(
                "from fastapi import FastAPI\n"
                "\n"
                "app = FastAPI()\n"
                "\n"
                "@app.get('/healthz')\n"
                "def healthz() -> dict[str, str]:\n"
                "    return {'status': 'ok'}\n",
                encoding="utf-8",
            )

            frontend_server = workspace / "fake_frontend_server.py"
            frontend_server.write_text(
                "import argparse\n"
                "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
                "\n"
                "parser = argparse.ArgumentParser()\n"
                "parser.add_argument('--host', default='127.0.0.1')\n"
                "parser.add_argument('--port', type=int, required=True)\n"
                "args = parser.parse_args()\n"
                "\n"
                "class Handler(BaseHTTPRequestHandler):\n"
                "    def do_GET(self):\n"
                "        self.send_response(200)\n"
                "        self.end_headers()\n"
                "        self.wfile.write(b'ok')\n"
                "\n"
                "    def log_message(self, format, *args):\n"
                "        return\n"
                "\n"
                "HTTPServer((args.host, args.port), Handler).serve_forever()\n",
                encoding="utf-8",
            )

            fake_npx = workspace / "fake-npx.cmd"
            fake_npx.write_text(
                "@echo off\r\n"
                "setlocal EnableDelayedExpansion\r\n"
                "set HOST=127.0.0.1\r\n"
                "set PORT=3000\r\n"
                ":parse\r\n"
                'if "%~1"=="" goto run\r\n'
                'if /I "%~1"=="next" (\r\n'
                "  shift\r\n"
                "  goto parse\r\n"
                ")\r\n"
                'if /I "%~1"=="dev" (\r\n'
                "  shift\r\n"
                "  goto parse\r\n"
                ")\r\n"
                'if /I "%~1"=="--hostname" (\r\n'
                "  set HOST=%~2\r\n"
                "  shift\r\n"
                "  shift\r\n"
                "  goto parse\r\n"
                ")\r\n"
                'if /I "%~1"=="--port" (\r\n'
                "  set PORT=%~2\r\n"
                "  shift\r\n"
                "  shift\r\n"
                "  goto parse\r\n"
                ")\r\n"
                "shift\r\n"
                "goto parse\r\n"
                ":run\r\n"
                f'"{sys.executable}" "{frontend_server}" --host %HOST% --port %PORT%\r\n',
                encoding="utf-8",
            )

            stdout_path = workspace / "script-stdout.log"
            stderr_path = workspace / "script-stderr.log"
            stdout_handle = stdout_path.open("w", encoding="utf-8")
            stderr_handle = stderr_path.open("w", encoding="utf-8")

            process = subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(SCRIPT_PATH),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-SkipBackendInstall",
                    "-SkipFrontendInstall",
                    "-PythonCommand",
                    str(Path(sys.executable)),
                    "-NpxCommand",
                    str(fake_npx),
                    "-BackendPort",
                    "8110",
                    "-FrontendPort",
                    "3110",
                    "-HealthTimeoutSeconds",
                    "15",
                    "-ExitWhenReady",
                ],
                cwd=REPO_ROOT,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
            )

            deadline = time.time() + 25
            backend_ready = False
            frontend_ready = False
            while time.time() < deadline:
                if process.poll() is not None:
                    break

                try:
                    with urllib.request.urlopen(
                        "http://127.0.0.1:8110/healthz",
                        timeout=2,
                    ) as response:
                        backend_ready = response.status == 200
                except (urllib.error.URLError, TimeoutError):
                    pass

                try:
                    with urllib.request.urlopen(
                        "http://127.0.0.1:3110/courses/new/input",
                        timeout=2,
                    ) as response:
                        frontend_ready = response.status == 200
                except (urllib.error.URLError, TimeoutError):
                    pass

                if backend_ready and frontend_ready:
                    break

                time.sleep(1)

            process.wait(timeout=10)
            stdout_handle.flush()
            stderr_handle.flush()
            stdout_output = stdout_path.read_text(encoding="utf-8")
            stderr_output = stderr_path.read_text(encoding="utf-8")
            self.assertEqual(process.returncode, 0, msg=f"STDOUT:\n{stdout_output}\nSTDERR:\n{stderr_output}")
            self.assertTrue(
                backend_ready and frontend_ready or "ExitWhenReady enabled" in stdout_output,
                msg=f"STDOUT:\n{stdout_output}\nSTDERR:\n{stderr_output}",
            )
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=10)
            if stdout_handle is not None:
                stdout_handle.close()
            if stderr_handle is not None:
                stderr_handle.close()

            for _ in range(10):
                try:
                    shutil.rmtree(workspace)
                    break
                except PermissionError:
                    time.sleep(1)
            else:
                shutil.rmtree(workspace, ignore_errors=True)

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
            self.assertIn("npx", result.stdout)
            self.assertIn("next dev --hostname 127.0.0.1 --port 3100", result.stdout)
            self.assertIn("Resolved Python command:", result.stdout)
            self.assertIn(str(Path(sys.executable)), result.stdout)
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

    def test_start_gui_local_rejects_python_older_than_310(self) -> None:
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
            fake_python = workspace / "fake-python.cmd"
            fake_python.write_text(
                "@echo off\r\n"
                'if "%~1"=="--version" (\r\n'
                "  echo Python 3.9.18\r\n"
                "  exit /b 0\r\n"
                ")\r\n"
                "exit /b 0\r\n",
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
                    "-SkipBackendInstall",
                    "-SkipFrontendInstall",
                    "-PythonCommand",
                    str(fake_python),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("python 3.10+", result.stderr.lower())
            self.assertIn("3.9.18", result.stderr)


if __name__ == "__main__":
    unittest.main()
