import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from server.app.adapters.cli_runner import CourseRunSpec, LocalProcessRunner


class LocalProcessRunnerTests(unittest.TestCase):
    def test_start_passes_provider_policy_flags_to_runtime_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = LocalProcessRunner(workspace_root=root, log_root=root / "logs")
            runtime_specs = (
                CourseRunSpec(
                    run_id="run-1",
                    command="run-course",
                    book_title="数据库系统概论",
                    input_dir=root / "input",
                    output_dir=root / "out",
                    backend="openai",
                    max_concurrent_per_run=2,
                    max_concurrent_global=5,
                    max_call_attempts=4,
                    max_resume_attempts=3,
                ),
                CourseRunSpec(
                    run_id="run-2",
                    command="resume-course",
                    book_title="数据库系统概论",
                    input_dir=root / "input",
                    output_dir=root / "out",
                    backend="openai",
                    max_concurrent_per_run=2,
                    max_concurrent_global=5,
                    max_call_attempts=4,
                    max_resume_attempts=3,
                ),
                CourseRunSpec(
                    run_id="run-3",
                    command="build-global",
                    book_title="数据库系统概论",
                    input_dir=None,
                    output_dir=root / "out",
                    backend="openai",
                    max_concurrent_per_run=2,
                    max_concurrent_global=5,
                    max_call_attempts=4,
                    max_resume_attempts=3,
                ),
            )

            try:
                with patch("server.app.adapters.cli_runner.subprocess.Popen", return_value=MagicMock()) as popen:
                    for spec in runtime_specs:
                        runner.start(spec)

                for call in popen.call_args_list:
                    command = call.kwargs["args"] if "args" in call.kwargs else call.args[0]
                    self.assertIn("--max-concurrent-per-run", command)
                    self.assertIn("2", command)
                    self.assertIn("--max-concurrent-global", command)
                    self.assertIn("5", command)
                    self.assertIn("--max-call-attempts", command)
                    self.assertIn("4", command)
                    self.assertIn("--max-resume-attempts", command)
                    self.assertIn("3", command)
            finally:
                for record in runner._processes.values():
                    record.log_handle.close()

    def test_start_does_not_pass_provider_policy_flags_to_clean_course(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = LocalProcessRunner(workspace_root=root, log_root=root / "logs")
            spec = CourseRunSpec(
                run_id="run-clean",
                command="clean-course",
                book_title="数据库系统概论",
                input_dir=root / "input",
                output_dir=root / "out",
                backend="heuristic",
                max_concurrent_per_run=2,
                max_concurrent_global=5,
                max_call_attempts=4,
                max_resume_attempts=3,
            )

            try:
                with patch("server.app.adapters.cli_runner.subprocess.Popen", return_value=MagicMock()) as popen:
                    runner.start(spec)

                command = popen.call_args.kwargs["args"] if "args" in popen.call_args.kwargs else popen.call_args.args[0]
                self.assertNotIn("--max-concurrent-per-run", command)
                self.assertNotIn("--max-concurrent-global", command)
                self.assertNotIn("--max-call-attempts", command)
                self.assertNotIn("--max-resume-attempts", command)
            finally:
                for record in runner._processes.values():
                    record.log_handle.close()

    def test_start_does_not_pass_provider_policy_flags_to_blueprint_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = LocalProcessRunner(workspace_root=root, log_root=root / "logs")
            blueprint_specs = (
                CourseRunSpec(
                    run_id="run-blueprint",
                    command="build-blueprint",
                    book_title="数据库系统概论",
                    input_dir=root / "input",
                    output_dir=root / "out",
                    backend="openai",
                    max_concurrent_per_run=2,
                    max_concurrent_global=5,
                    max_call_attempts=4,
                    max_resume_attempts=3,
                ),
                CourseRunSpec(
                    run_id="run-bootstrap",
                    command="bootstrap-course",
                    book_title="数据库系统概论",
                    input_dir=root / "input",
                    output_dir=root / "out",
                    backend="openai",
                    max_concurrent_per_run=2,
                    max_concurrent_global=5,
                    max_call_attempts=4,
                    max_resume_attempts=3,
                ),
            )

            try:
                with patch("server.app.adapters.cli_runner.subprocess.Popen", return_value=MagicMock()) as popen:
                    for spec in blueprint_specs:
                        runner.start(spec)

                for call in popen.call_args_list:
                    command = call.kwargs["args"] if "args" in call.kwargs else call.args[0]
                    self.assertNotIn("--max-concurrent-per-run", command)
                    self.assertNotIn("--max-concurrent-global", command)
                    self.assertNotIn("--max-call-attempts", command)
                    self.assertNotIn("--max-resume-attempts", command)
            finally:
                for record in runner._processes.values():
                    record.log_handle.close()


if __name__ == "__main__":
    unittest.main()
