from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .blueprint import apply_policy_overrides, build_course_id, load_blueprint, save_blueprint
from .bootstrap import bootstrap_course_blueprint, describe_source, load_toc_text, write_json
from .llm import AnthropicMessagesBackend, OpenAICompatibleResponsesBackend, OpenAIResponsesBackend
from .pipeline import HeuristicLLMBackend, PipelineConfig, PipelineRunner
from .provider_policy import POLICY_OVERRIDE_FIELDS, resolve_provider_execution_policy
from .testing import StubLLMBackend

STAGE_MODEL_SPECS = {
    "blueprint_builder": "MODEL_BLUEPRINT_BUILDER",
    "curriculum_anchor": "MODEL_CURRICULUM_ANCHOR",
    "gap_fill": "MODEL_GAP_FILL",
    "pack_plan": "MODEL_COMPOSE_PACK",
    "write_lecture_note": "MODEL_COMPOSE_PACK",
    "write_terms": "MODEL_COMPOSE_PACK",
    "write_interview_qa": "MODEL_COMPOSE_PACK",
    "write_cross_links": "MODEL_COMPOSE_PACK",
    "write_open_questions": "MODEL_COMPOSE_PACK",
    "review": "MODEL_REVIEW",
    "build_global_glossary": "MODEL_CANONICALIZE",
    "build_interview_index": "MODEL_CANONICALIZE",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate NotebookLM-ready knowledge packs from lecture transcripts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    source_parent = argparse.ArgumentParser(add_help=False)
    source_parent.add_argument("--input-dir", required=True, type=Path, help="Directory containing chapter transcript markdown files.")
    source_parent.add_argument("--output-dir", required=True, type=Path, help="Directory where generated runtime artifacts will be written.")
    source_parent.add_argument("--book-title", required=True, help="Published textbook title used as the primary source anchor.")
    source_parent.add_argument("--toc-file", type=Path, help="Optional plain-text TOC file.")
    source_parent.add_argument("--toc-text", help="Optional inline TOC text.")
    source_parent.add_argument("--author", action="append", default=None, help="Optional author. Repeat for multiple authors.")
    source_parent.add_argument("--edition", default=None, help="Optional textbook edition.")
    source_parent.add_argument("--publisher", default=None, help="Optional publisher.")
    source_parent.add_argument("--isbn", default=None, help="Optional ISBN.")

    course_parent = argparse.ArgumentParser(add_help=False)
    course_parent.add_argument("--output-dir", required=True, type=Path, help="Directory where generated runtime artifacts are written.")
    course_parent.add_argument("--book-title", required=True, help="Published textbook title used to resolve the existing course runtime.")

    backend_parent = argparse.ArgumentParser(add_help=False)
    backend_parent.add_argument(
        "--backend",
        choices=("openai", "openai_compatible", "anthropic", "heuristic", "stub"),
        default="heuristic",
        help="LLM backend to use. heuristic works offline; hosted backends require provider API keys.",
    )
    backend_parent.add_argument("--model", default=None, help="Provider default model name.")
    backend_parent.add_argument("--base-url", default=None, help="Optional override for hosted API base URL.")
    backend_parent.add_argument("--timeout-seconds", type=int, default=None, help="Optional override for hosted backend request timeout.")
    backend_parent.add_argument("--stub-scenario", type=Path, help="JSON file with canned agent responses for the stub backend.")
    backend_parent.add_argument("--blueprint-builder-model", default=None, help="Optional stage-specific model for blueprint building.")
    backend_parent.add_argument("--curriculum-anchor-model", default=None, help="Optional stage-specific model for curriculum anchoring.")
    backend_parent.add_argument("--gap-fill-model", default=None, help="Optional stage-specific model for gap filling.")
    backend_parent.add_argument("--compose-pack-model", default=None, help="Optional stage-specific model for knowledge pack composition.")
    backend_parent.add_argument("--review-model", default=None, help="Optional stage-specific model for reviewer stage.")
    backend_parent.add_argument("--canonicalize-model", default=None, help="Optional stage-specific model for canonicalization.")

    build_blueprint = subparsers.add_parser(
        "build-blueprint",
        parents=[source_parent, backend_parent],
        help="Build and persist course_blueprint.json without running the full pipeline.",
    )
    build_blueprint.set_defaults(handler=handle_build_blueprint)

    bootstrap_course = subparsers.add_parser(
        "bootstrap-course",
        parents=[source_parent, backend_parent],
        help="Alias of build-blueprint for GUI/bootstrap flows.",
    )
    bootstrap_course.set_defaults(handler=handle_build_blueprint)

    run_course = subparsers.add_parser(
        "run-course",
        parents=[source_parent, backend_parent],
        help="Build or refresh blueprint, then run the course pipeline.",
    )
    run_course.add_argument("--clean", action="store_true", help="Delete the existing runtime for this course before running.")
    run_course.add_argument("--review-mode", choices=("light", "standard", "strict"), default=None, help="Optional override for blueprint policy.review_mode.")
    run_course.add_argument("--target-output", default=None, help="Optional override for blueprint policy.target_output.")
    run_course.add_argument("--enable-review", action="store_true", help="Run the optional reviewer stage for this invocation.")
    add_run_id_argument(run_course)
    add_provider_policy_arguments(run_course)
    run_course.set_defaults(handler=handle_run_course)

    resume_course = subparsers.add_parser(
        "resume-course",
        parents=[source_parent, backend_parent],
        help="Resume the course pipeline from valid checkpoints.",
    )
    add_run_id_argument(resume_course)
    add_provider_policy_arguments(resume_course)
    resume_course.set_defaults(handler=handle_resume_course)

    build_global = subparsers.add_parser(
        "build-global",
        parents=[course_parent, backend_parent],
        help="Rebuild global consolidation outputs from existing approved chapter artifacts.",
    )
    add_provider_policy_arguments(build_global)
    build_global.set_defaults(handler=handle_build_global)

    inspect_source = subparsers.add_parser(
        "inspect-source",
        parents=[source_parent],
        help="Inspect transcript inventory without building outputs.",
    )
    inspect_source.set_defaults(handler=handle_inspect_source)

    clean_course = subparsers.add_parser(
        "clean-course",
        parents=[source_parent],
        help="Delete runtime artifacts for the resolved course id.",
    )
    add_run_id_argument(clean_course)
    clean_course.set_defaults(handler=handle_clean_course)

    show_status = subparsers.add_parser(
        "show-status",
        parents=[source_parent],
        help="Show runtime_state.json for the resolved course id.",
    )
    show_status.set_defaults(handler=handle_show_status)

    return parser


def positive_int_arg(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def add_provider_policy_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-concurrent-per-run", type=positive_int_arg, default=None, help="Optional provider policy override for run-scoped chapter concurrency.")
    parser.add_argument("--max-concurrent-global", type=positive_int_arg, default=None, help="Optional provider policy override for process-wide provider concurrency.")
    parser.add_argument("--max-call-attempts", type=positive_int_arg, default=None, help="Optional provider policy override for per-call retry attempts.")
    parser.add_argument("--max-resume-attempts", type=positive_int_arg, default=None, help="Optional provider policy override for run-level resume attempts.")


def add_run_id_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-id", default=None, help="Optional GUI run id used for final-output snapshots.")


def load_dotenv_file(path: Path, override: bool = False) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if key in os.environ and not override:
            continue
        os.environ[key] = value


def normalize_base_url(backend: str, base_url: str | None) -> str | None:
    if base_url is None:
        return None

    normalized = base_url.strip().rstrip("/")
    parsed = urlparse(normalized)

    if parsed.scheme not in {"http", "https"}:
        raise SystemExit(f"Invalid --base-url for {backend}: must start with http:// or https://")
    if not parsed.netloc:
        raise SystemExit(f"Invalid --base-url for {backend}: host is required")
    if parsed.params or parsed.query or parsed.fragment:
        raise SystemExit(f"Invalid --base-url for {backend}: query strings and fragments are not supported")

    path = parsed.path.rstrip("/")

    if backend == "openai":
        if path in {"", "/v1"}:
            return f"{parsed.scheme}://{parsed.netloc}/v1/responses"
        if path.endswith("/responses"):
            return normalized
        raise SystemExit("Invalid --base-url for openai: expected a root URL, /v1, or an endpoint ending with /responses")

    if backend == "openai_compatible":
        if path in {"", "/v1"}:
            return f"{parsed.scheme}://{parsed.netloc}/v1/chat/completions"
        if path.endswith("/responses") or path.endswith("/chat/completions"):
            return normalized
        raise SystemExit(
            "Invalid --base-url for openai_compatible: expected a root URL, /v1, or an endpoint ending with /responses or /chat/completions"
        )

    if backend == "anthropic":
        if path in {"", "/v1"}:
            return f"{parsed.scheme}://{parsed.netloc}/v1/messages"
        if path.endswith("/messages"):
            return normalized
        raise SystemExit("Invalid --base-url for anthropic: expected a root URL, /v1, or an endpoint ending with /messages")

    return normalized


def resolve_model(explicit_model: str | None, env_key: str, default: str) -> str:
    return explicit_model or os.environ.get(env_key) or default


def resolve_timeout(explicit_timeout: int | None, default: int = 300) -> int:
    if explicit_timeout is not None:
        return explicit_timeout
    env_timeout = os.environ.get("LLM_TIMEOUT_SECONDS")
    if env_timeout:
        return int(env_timeout)
    return default


def resolve_stage_models(args: argparse.Namespace) -> dict[str, str]:
    provider_env_key = {
        "openai": "OPENAI_MODEL",
        "openai_compatible": "OPENAI_COMPATIBLE_MODEL",
        "anthropic": "ANTHROPIC_MODEL",
    }.get(getattr(args, "backend", ""), "")
    provider_default = os.environ.get(provider_env_key) or getattr(args, "model", None)
    legacy_cli_mapping = {
        "pack_plan": "compose_pack_model",
        "write_lecture_note": "compose_pack_model",
        "write_terms": "compose_pack_model",
        "write_interview_qa": "compose_pack_model",
        "write_cross_links": "compose_pack_model",
        "write_open_questions": "compose_pack_model",
        "build_global_glossary": "canonicalize_model",
        "build_interview_index": "canonicalize_model",
    }
    resolved: dict[str, str] = {}
    for stage_name, env_key in STAGE_MODEL_SPECS.items():
        cli_attr = legacy_cli_mapping.get(stage_name, f"{stage_name}_model")
        cli_value = getattr(args, cli_attr, None)
        model = cli_value or os.environ.get(env_key) or provider_default
        if model:
            resolved[stage_name] = model
    return resolved


def resolve_provider_policy(
    args: argparse.Namespace,
    config_policy: dict[str, Any] | object | None = None,
):
    cli_overrides = {field_name: getattr(args, field_name, None) for field_name in POLICY_OVERRIDE_FIELDS}
    return resolve_provider_execution_policy(
        provider=getattr(args, "backend", "heuristic"),
        config_policy=config_policy,
        cli_overrides=cli_overrides,
    )


def create_backend(args: argparse.Namespace):
    timeout_seconds = resolve_timeout(getattr(args, "timeout_seconds", None))
    if args.backend == "openai":
        base_url = normalize_base_url("openai", args.base_url or "https://api.openai.com/v1/responses")
        model = resolve_model(args.model, "OPENAI_MODEL", "gpt-5.4-mini")
        return OpenAIResponsesBackend(model=model, base_url=base_url, timeout_seconds=timeout_seconds)
    if args.backend == "openai_compatible":
        base_url = normalize_base_url(
            "openai_compatible",
            args.base_url or os.environ.get("OPENAI_COMPATIBLE_BASE_URL") or "https://openrouter.ai/api/v1/chat/completions",
        )
        model = resolve_model(args.model, "OPENAI_COMPATIBLE_MODEL", "openai/gpt-4.1-mini")
        return OpenAICompatibleResponsesBackend(model=model, base_url=base_url, timeout_seconds=timeout_seconds)
    if args.backend == "anthropic":
        base_url = normalize_base_url("anthropic", args.base_url or "https://api.anthropic.com/v1/messages")
        model = resolve_model(args.model, "ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        return AnthropicMessagesBackend(model=model, base_url=base_url, timeout_seconds=timeout_seconds)
    if args.backend == "stub":
        if not args.stub_scenario:
            raise SystemExit("--stub-scenario is required when --backend stub is used.")
        responses = json.loads(args.stub_scenario.read_text(encoding="utf-8"))
        return StubLLMBackend(responses=responses)
    return HeuristicLLMBackend()


def _resolve_course_dir(output_dir: Path, book_title: str) -> Path:
    return output_dir / "courses" / build_course_id(book_title.strip())


def _load_existing_course_blueprint(output_dir: Path, book_title: str) -> dict[str, Any]:
    course_dir = _resolve_course_dir(output_dir, book_title)
    blueprint_path = course_dir / "course_blueprint.json"
    if not blueprint_path.exists():
        raise SystemExit(f"course_blueprint.json not found for course: {book_title}")
    return load_blueprint(blueprint_path)


def _load_existing_runtime_state(output_dir: Path, book_title: str) -> dict[str, Any]:
    course_dir = _resolve_course_dir(output_dir, book_title)
    runtime_state_path = course_dir / "runtime_state.json"
    if not runtime_state_path.exists():
        raise SystemExit(f"runtime_state.json not found for course: {book_title}")
    return json.loads(runtime_state_path.read_text(encoding="utf-8"))


def _build_blueprint(args: argparse.Namespace, backend: Any | None) -> dict[str, Any]:
    toc_text = load_toc_text(args.toc_file, args.toc_text)
    llm_backend = backend if toc_text is None else None
    return bootstrap_course_blueprint(
        input_dir=args.input_dir,
        book_title=args.book_title,
        toc_text=toc_text,
        llm_backend=llm_backend,
        blueprint_builder_model=getattr(args, "blueprint_builder_model", None),
        authors=args.author,
        edition=args.edition,
        publisher=args.publisher,
        isbn=args.isbn,
    )


def handle_build_blueprint(args: argparse.Namespace) -> int:
    backend = create_backend(args) if getattr(args, "backend", None) else None
    blueprint = _build_blueprint(args, backend)
    course_dir = _resolve_course_dir(args.output_dir, blueprint["course_name"])
    save_blueprint(course_dir / "course_blueprint.json", blueprint)
    write_json(course_dir / "runtime_state.json", {"course_id": blueprint["course_id"], "blueprint_hash": blueprint["blueprint_hash"]})
    return 0


def handle_run_course(args: argparse.Namespace) -> int:
    provider_policy = resolve_provider_policy(args)
    backend = create_backend(args)
    blueprint = _build_blueprint(args, backend)
    blueprint = apply_policy_overrides(
        blueprint,
        review_mode=getattr(args, "review_mode", None),
        target_output=getattr(args, "target_output", None),
    )
    runner = PipelineRunner(
        config=PipelineConfig(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            model=getattr(backend, "model", ""),
            clean_output=getattr(args, "clean", False),
            course_blueprint=blueprint,
            stage_models=resolve_stage_models(args),
            backend_name=args.backend,
            enable_review=getattr(args, "enable_review", False),
            run_id=getattr(args, "run_id", None),
            provider_policy=provider_policy,
        ),
        llm_backend=backend,
    )
    runner.run()
    return 0


def handle_resume_course(args: argparse.Namespace) -> int:
    provider_policy = resolve_provider_policy(args)
    backend = create_backend(args)
    blueprint = _load_existing_course_blueprint(args.output_dir, args.book_title)
    runtime_state = _load_existing_runtime_state(args.output_dir, args.book_title)
    run_identity = runtime_state.get("run_identity", {})
    blueprint = apply_policy_overrides(
        blueprint,
        review_mode=run_identity.get("review_mode"),
        target_output=run_identity.get("target_output"),
    )
    runner = PipelineRunner(
        config=PipelineConfig(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            model=getattr(backend, "model", ""),
            course_blueprint=blueprint,
            stage_models=resolve_stage_models(args),
            backend_name=args.backend,
            enable_review=bool(run_identity.get("review_enabled", False)),
            run_id=getattr(args, "run_id", None),
            provider_policy=provider_policy,
        ),
        llm_backend=backend,
    )
    runner.run()
    return 0


def handle_build_global(args: argparse.Namespace) -> int:
    provider_policy = resolve_provider_policy(args)
    backend = create_backend(args)
    blueprint = _load_existing_course_blueprint(args.output_dir, args.book_title)
    runner = PipelineRunner(
        config=PipelineConfig(
            input_dir=args.output_dir,
            output_dir=args.output_dir,
            model=getattr(backend, "model", ""),
            course_blueprint=blueprint,
            stage_models=resolve_stage_models(args),
            backend_name=args.backend,
            run_global_consolidation=True,
            provider_policy=provider_policy,
        ),
        llm_backend=backend,
    )
    runner.run()
    return 0


def handle_inspect_source(args: argparse.Namespace) -> int:
    print(json.dumps(describe_source(args.input_dir), ensure_ascii=False, indent=2))
    return 0


def handle_clean_course(args: argparse.Namespace) -> int:
    course_dir = _resolve_course_dir(args.output_dir, args.book_title)
    if course_dir.exists():
        shutil.rmtree(course_dir)
    run_id = getattr(args, "run_id", None)
    if run_id:
        snapshot_dir = args.output_dir / "_gui" / "results-snapshots" / build_course_id(args.book_title) / run_id
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)
    return 0


def handle_show_status(args: argparse.Namespace) -> int:
    course_dir = _resolve_course_dir(args.output_dir, args.book_title)
    status_path = course_dir / "runtime_state.json"
    if not status_path.exists():
        raise SystemExit(f"runtime_state.json not found for course: {args.book_title}")
    print(status_path.read_text(encoding="utf-8"))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    load_dotenv_file(Path.cwd() / ".env")
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
