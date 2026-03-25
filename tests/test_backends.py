import argparse
import json
import os
import unittest

from processagent.cli import create_backend, resolve_stage_models
from processagent.llm import AnthropicMessagesBackend, OpenAICompatibleResponsesBackend, parse_json_text


class BackendFactoryTest(unittest.TestCase):
    def test_create_backend_supports_openai_compatible(self) -> None:
        backend = create_backend(
            argparse.Namespace(
                backend="openai_compatible",
                model="openrouter/auto",
                base_url="https://openrouter.ai/api/v1/responses",
                stub_scenario=None,
            )
        )

        self.assertIsInstance(backend, OpenAICompatibleResponsesBackend)
        self.assertEqual(backend.base_url, "https://openrouter.ai/api/v1/responses")
        self.assertEqual(backend.api_key_env, "OPENAI_COMPATIBLE_API_KEY")

    def test_create_backend_supports_anthropic(self) -> None:
        backend = create_backend(
            argparse.Namespace(
                backend="anthropic",
                model=None,
                base_url=None,
                stub_scenario=None,
            )
        )

        self.assertIsInstance(backend, AnthropicMessagesBackend)
        self.assertEqual(backend.api_key_env, "ANTHROPIC_API_KEY")
        self.assertTrue(backend.model.startswith("claude"))

    def test_create_backend_normalizes_trailing_slash_in_base_url(self) -> None:
        backend = create_backend(
            argparse.Namespace(
                backend="openai_compatible",
                model="openrouter/auto",
                base_url="https://openrouter.ai/api/v1/chat/completions/",
                stub_scenario=None,
            )
        )

        self.assertEqual(backend.base_url, "https://openrouter.ai/api/v1/chat/completions")

    def test_create_backend_expands_root_base_url_for_openai_compatible(self) -> None:
        backend = create_backend(
            argparse.Namespace(
                backend="openai_compatible",
                model="openrouter/auto",
                base_url="https://api.ohmygpt.com",
                stub_scenario=None,
            )
        )

        self.assertEqual(backend.base_url, "https://api.ohmygpt.com/v1/chat/completions")

    def test_create_backend_expands_v1_base_url_for_openai_compatible(self) -> None:
        backend = create_backend(
            argparse.Namespace(
                backend="openai_compatible",
                model="openrouter/auto",
                base_url="https://api.ohmygpt.com/v1",
                stub_scenario=None,
            )
        )

        self.assertEqual(backend.base_url, "https://api.ohmygpt.com/v1/chat/completions")

    def test_create_backend_rejects_invalid_base_url_scheme(self) -> None:
        with self.assertRaises(SystemExit) as context:
            create_backend(
                argparse.Namespace(
                    backend="openai_compatible",
                    model="openrouter/auto",
                    base_url="ftp://openrouter.ai/api/v1/responses",
                    stub_scenario=None,
                )
            )

        self.assertIn("http:// or https://", str(context.exception))

    def test_create_backend_expands_v1_base_url_for_anthropic(self) -> None:
        backend = create_backend(
            argparse.Namespace(
                backend="anthropic",
                model=None,
                base_url="https://api.anthropic.com/v1",
                stub_scenario=None,
            )
        )

        self.assertEqual(backend.base_url, "https://api.anthropic.com/v1/messages")

    def test_create_backend_rejects_anthropic_base_url_without_messages_endpoint(self) -> None:
        with self.assertRaises(SystemExit) as context:
            create_backend(
                argparse.Namespace(
                    backend="anthropic",
                    model=None,
                    base_url="https://api.anthropic.com/v1/complete",
                    stub_scenario=None,
                )
            )

        self.assertIn("/messages", str(context.exception))

    def test_create_backend_reads_openai_compatible_model_from_env(self) -> None:
        original = os.environ.get("OPENAI_COMPATIBLE_MODEL")
        os.environ["OPENAI_COMPATIBLE_MODEL"] = "moonshot/kimi-k2"
        try:
            backend = create_backend(
                argparse.Namespace(
                    backend="openai_compatible",
                    model=None,
                    base_url="https://api.ohmygpt.com",
                    stub_scenario=None,
                )
            )
        finally:
            if original is None:
                os.environ.pop("OPENAI_COMPATIBLE_MODEL", None)
            else:
                os.environ["OPENAI_COMPATIBLE_MODEL"] = original

        self.assertEqual(backend.model, "moonshot/kimi-k2")

    def test_cli_model_argument_overrides_env_model(self) -> None:
        original = os.environ.get("OPENAI_COMPATIBLE_MODEL")
        os.environ["OPENAI_COMPATIBLE_MODEL"] = "moonshot/kimi-k2"
        try:
            backend = create_backend(
                argparse.Namespace(
                    backend="openai_compatible",
                    model="deepseek/deepseek-chat-v3",
                    base_url="https://api.ohmygpt.com",
                    stub_scenario=None,
                )
            )
        finally:
            if original is None:
                os.environ.pop("OPENAI_COMPATIBLE_MODEL", None)
            else:
                os.environ["OPENAI_COMPATIBLE_MODEL"] = original

        self.assertEqual(backend.model, "deepseek/deepseek-chat-v3")

    def test_create_backend_reads_timeout_from_env(self) -> None:
        original = os.environ.get("LLM_TIMEOUT_SECONDS")
        os.environ["LLM_TIMEOUT_SECONDS"] = "420"
        try:
            backend = create_backend(
                argparse.Namespace(
                    backend="openai_compatible",
                    model=None,
                    base_url="https://api.ohmygpt.com",
                    stub_scenario=None,
                    timeout_seconds=None,
                )
            )
        finally:
            if original is None:
                os.environ.pop("LLM_TIMEOUT_SECONDS", None)
            else:
                os.environ["LLM_TIMEOUT_SECONDS"] = original

        self.assertEqual(backend.timeout_seconds, 420)

    def test_resolve_stage_models_prefers_stage_specific_env_over_provider_default(self) -> None:
        original_specific = os.environ.get("MODEL_COMPOSE_PACK")
        original_default = os.environ.get("OPENAI_COMPATIBLE_MODEL")
        os.environ["MODEL_COMPOSE_PACK"] = "openai/gpt-5.4"
        os.environ["OPENAI_COMPATIBLE_MODEL"] = "openai/gpt-4.1-mini"
        try:
            models = resolve_stage_models(
                argparse.Namespace(
                    backend="openai_compatible",
                    curriculum_anchor_model=None,
                    gap_fill_model=None,
                    compose_pack_model=None,
                    review_model=None,
                    canonicalize_model=None,
                    blueprint_builder_model=None,
                )
            )
        finally:
            if original_specific is None:
                os.environ.pop("MODEL_COMPOSE_PACK", None)
            else:
                os.environ["MODEL_COMPOSE_PACK"] = original_specific
            if original_default is None:
                os.environ.pop("OPENAI_COMPATIBLE_MODEL", None)
            else:
                os.environ["OPENAI_COMPATIBLE_MODEL"] = original_default

        self.assertEqual(models["pack_plan"], "openai/gpt-5.4")
        self.assertEqual(models["write_interview_qa"], "openai/gpt-5.4")
        self.assertEqual(models["build_global_glossary"], "openai/gpt-4.1-mini")
        self.assertEqual(models["curriculum_anchor"], "openai/gpt-4.1-mini")


class AnthropicBackendTest(unittest.TestCase):
    def test_extract_text_reads_text_content_blocks(self) -> None:
        backend = AnthropicMessagesBackend(model="claude-sonnet-4-20250514")

        text = backend._extract_text(
            {
                "content": [
                    {"type": "text", "text": "{\"status\":\"ok\"}"},
                    {"type": "thinking", "thinking": "ignored"},
                ]
            }
        )

        self.assertEqual(text, "{\"status\":\"ok\"}")


class OpenAICompatibleBackendTest(unittest.TestCase):
    def test_extract_text_reads_chat_completions_response(self) -> None:
        backend = OpenAICompatibleResponsesBackend(
            model="openrouter/auto",
            base_url="https://api.ohmygpt.com/v1/chat/completions",
        )

        text = backend._extract_text(
            {
                "choices": [
                    {
                        "message": {
                            "content": "{\"status\":\"ok\"}"
                        }
                    }
                ]
            }
        )

        self.assertEqual(text, "{\"status\":\"ok\"}")

    def test_build_text_request_body_omits_json_response_format(self) -> None:
        backend = OpenAICompatibleResponsesBackend(
            model="openrouter/auto",
            base_url="https://api.ohmygpt.com/v1/chat/completions",
        )

        body = backend._build_text_request_body("Write markdown only.", {"chapter": "绪论"})

        self.assertNotIn("response_format", body)
        self.assertEqual(body["messages"][0]["content"], "Write markdown only.")

    def test_build_json_request_body_injects_json_hint_when_missing(self) -> None:
        backend = OpenAICompatibleResponsesBackend(
            model="openrouter/auto",
            base_url="https://api.ohmygpt.com/v1/chat/completions",
        )

        body = backend._build_request_body("Only return the object.", {"chapter": "绪论"})

        self.assertIn("json", body["messages"][0]["content"].lower())

    def test_build_request_body_uses_chat_completions_schema_when_needed(self) -> None:
        backend = OpenAICompatibleResponsesBackend(
            model="openrouter/auto",
            base_url="https://api.ohmygpt.com/v1/chat/completions",
        )

        body = backend._build_request_body("system prompt", {"chapter_id": "第一章"})

        self.assertIn("messages", body)
        self.assertNotIn("input", body)
        self.assertEqual(body["response_format"], {"type": "json_object"})


class JsonParsingTest(unittest.TestCase):
    def test_parse_json_text_accepts_markdown_code_fence(self) -> None:
        data = parse_json_text('```json\n{"ok": true}\n```')
        self.assertEqual(data, {"ok": True})

    def test_parse_json_text_extracts_first_json_object_from_mixed_text(self) -> None:
        data = parse_json_text('Here is the result:\n{"ok": true}\nDone.')
        self.assertEqual(data, {"ok": True})

    def test_parse_json_text_reports_blank_output_clearly(self) -> None:
        with self.assertRaisesRegex(json.JSONDecodeError, "blank model output"):
            parse_json_text("   \n\t")


if __name__ == "__main__":
    unittest.main()
