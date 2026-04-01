from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


@dataclass(frozen=True)
class CourseRunSpec:
    run_id: str
    command: str
    book_title: str
    input_dir: Path | None
    output_dir: Path
    backend: str = "heuristic"
    base_url: str | None = None
    model: str | None = None
    simple_model: str | None = None
    complex_model: str | None = None
    timeout_seconds: int | None = None
    env_overrides: dict[str, str] | None = None
    review_enabled: bool = False
    review_mode: str | None = None
    target_output: str | None = None
    max_concurrent_per_run: int | None = None
    max_concurrent_global: int | None = None
    max_call_attempts: int | None = None
    max_resume_attempts: int | None = None


@dataclass(frozen=True)
class RunnerSnapshot:
    status: str
    last_error: str | None = None
    log_path: Path | None = None


@dataclass
class _ProcessRecord:
    process: subprocess.Popen[str]
    log_handle: TextIO
    log_path: Path


class LocalProcessRunner:
    def __init__(self, workspace_root: Path, log_root: Path) -> None:
        self._workspace_root = workspace_root
        self._log_root = log_root
        self._processes: dict[str, _ProcessRecord] = {}

    def start(self, spec: CourseRunSpec) -> None:
        log_path = self._log_root / spec.run_id / "process.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("w", encoding="utf-8")
        command = [
            sys.executable,
            "-m",
            "processagent.cli",
            spec.command,
            "--book-title",
            spec.book_title,
            "--output-dir",
            str(spec.output_dir),
        ]
        if spec.input_dir is not None:
            command.extend(["--input-dir", str(spec.input_dir)])
        if spec.command in {"run-course", "resume-course", "clean-course"}:
            command.extend(["--run-id", spec.run_id])
        if spec.command in {"run-course", "resume-course", "build-blueprint", "bootstrap-course"}:
            command.extend(["--backend", spec.backend])
            if spec.base_url:
                command.extend(["--base-url", spec.base_url])
            if spec.model:
                command.extend(["--model", spec.model])
            if spec.timeout_seconds is not None:
                command.extend(["--timeout-seconds", str(spec.timeout_seconds)])
            if spec.simple_model:
                command.extend(["--blueprint-builder-model", spec.simple_model])
                command.extend(["--curriculum-anchor-model", spec.simple_model])
                command.extend(["--canonicalize-model", spec.simple_model])
            if spec.complex_model:
                command.extend(["--gap-fill-model", spec.complex_model])
                command.extend(["--compose-pack-model", spec.complex_model])
                command.extend(["--review-model", spec.complex_model])
        if spec.command in {"run-course", "resume-course"}:
            self._append_provider_policy_args(command, spec)
        if spec.command == "run-course" and spec.review_mode:
            command.extend(["--review-mode", spec.review_mode])
        if spec.command == "run-course" and spec.review_enabled:
            command.append("--enable-review")
        if spec.command == "run-course" and spec.target_output:
            command.extend(["--target-output", spec.target_output])
        if spec.command == "build-global":
            command.extend(["--backend", spec.backend])
            if spec.base_url:
                command.extend(["--base-url", spec.base_url])
            if spec.model:
                command.extend(["--model", spec.model])
            if spec.timeout_seconds is not None:
                command.extend(["--timeout-seconds", str(spec.timeout_seconds)])
            canonicalize_model = spec.simple_model or spec.complex_model
            if canonicalize_model:
                command.extend(["--canonicalize-model", canonicalize_model])
            self._append_provider_policy_args(command, spec)
        env = os.environ.copy()
        if spec.env_overrides:
            env.update(spec.env_overrides)
        process = subprocess.Popen(
            command,
            cwd=str(self._workspace_root),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        self._processes[spec.run_id] = _ProcessRecord(
            process=process,
            log_handle=log_handle,
            log_path=log_path,
        )

    @staticmethod
    def _append_provider_policy_args(command: list[str], spec: CourseRunSpec) -> None:
        if spec.max_concurrent_per_run is not None:
            command.extend(["--max-concurrent-per-run", str(spec.max_concurrent_per_run)])
        if spec.max_concurrent_global is not None:
            command.extend(["--max-concurrent-global", str(spec.max_concurrent_global)])
        if spec.max_call_attempts is not None:
            command.extend(["--max-call-attempts", str(spec.max_call_attempts)])
        if spec.max_resume_attempts is not None:
            command.extend(["--max-resume-attempts", str(spec.max_resume_attempts)])

    def snapshot(self, run_id: str) -> RunnerSnapshot | None:
        record = self._processes.get(run_id)
        if record is None:
            return None

        return_code = record.process.poll()
        if return_code is None:
            return RunnerSnapshot(status="running", log_path=record.log_path)

        if not record.log_handle.closed:
            record.log_handle.close()

        if return_code == 0:
            return RunnerSnapshot(status="completed", log_path=record.log_path)

        return RunnerSnapshot(
            status="failed",
            last_error=self._tail_log(record.log_path),
            log_path=record.log_path,
        )

    @staticmethod
    def _tail_log(log_path: Path) -> str:
        if not log_path.exists():
            return "Process failed without a log file."

        lines = [line.strip() for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return "Process failed without error output."
        return lines[-1]
