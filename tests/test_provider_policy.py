import importlib
import importlib.util
import unittest

from server.app.models.gui_runtime_config import GuiRuntimeConfig


class ProviderPolicyTests(unittest.TestCase):
    def _load_module(self):
        spec = importlib.util.find_spec("processagent.provider_policy")
        self.assertIsNotNone(spec, "processagent.provider_policy should exist")
        return importlib.import_module("processagent.provider_policy")

    def test_gui_runtime_config_exposes_provider_policy_overrides(self) -> None:
        config = GuiRuntimeConfig.model_validate(
            {
                "provider_policies": {
                    "openai": {
                        "max_concurrent_per_run": 2,
                        "max_concurrent_global": 6,
                        "max_call_attempts": 5,
                        "max_resume_attempts": 4,
                    }
                }
            }
        )

        self.assertTrue(hasattr(config, "provider_policies"))
        self.assertEqual(config.provider_policies.openai.max_concurrent_per_run, 2)
        self.assertEqual(config.provider_policies.openai.max_concurrent_global, 6)
        self.assertEqual(config.provider_policies.openai.max_call_attempts, 5)
        self.assertEqual(config.provider_policies.openai.max_resume_attempts, 4)

    def test_builtin_registry_covers_supported_providers(self) -> None:
        module = self._load_module()

        self.assertEqual(
            set(module.BUILTIN_PROVIDER_EXECUTION_POLICIES),
            {"openai", "openai_compatible", "anthropic", "heuristic", "stub"},
        )

        for provider_name in module.BUILTIN_PROVIDER_EXECUTION_POLICIES:
            policy = module.get_builtin_provider_policy(provider_name)
            self.assertEqual(policy.provider, provider_name)
            self.assertGreater(policy.max_concurrent_per_run, 0)
            self.assertGreater(policy.max_concurrent_global, 0)
            self.assertGreater(policy.max_call_attempts, 0)
            self.assertGreater(policy.max_resume_attempts, 0)
            self.assertIsInstance(policy.transient_http_statuses, tuple)

    def test_resolve_provider_policy_applies_config_then_cli_priority(self) -> None:
        module = self._load_module()
        config = GuiRuntimeConfig.model_validate(
            {
                "provider_policies": {
                    "openai": {
                        "max_concurrent_per_run": 2,
                        "max_concurrent_global": 5,
                        "max_call_attempts": 4,
                    }
                }
            }
        )

        builtin = module.get_builtin_provider_policy("openai")
        merged_from_config = module.apply_config_policy_overrides(
            builtin,
            config.provider_policies.openai,
        )
        merged_from_cli = module.apply_cli_policy_overrides(
            merged_from_config,
            {
                "max_concurrent_global": 9,
                "max_call_attempts": 7,
                "max_resume_attempts": 3,
            },
        )

        self.assertEqual(merged_from_config.max_concurrent_per_run, 2)
        self.assertEqual(merged_from_config.max_concurrent_global, 5)
        self.assertEqual(merged_from_config.max_call_attempts, 4)
        self.assertEqual(merged_from_config.max_resume_attempts, builtin.max_resume_attempts)
        self.assertEqual(merged_from_cli.max_concurrent_per_run, 2)
        self.assertEqual(merged_from_cli.max_concurrent_global, 9)
        self.assertEqual(merged_from_cli.max_call_attempts, 7)
        self.assertEqual(merged_from_cli.max_resume_attempts, 3)

        resolved = module.resolve_provider_execution_policy(
            provider="openai",
            config_policy=config.provider_policies.openai,
            cli_overrides={
                "max_concurrent_global": 11,
                "max_call_attempts": 8,
                "max_resume_attempts": 6,
            },
        )
        self.assertEqual(resolved.max_concurrent_per_run, 2)
        self.assertEqual(resolved.max_concurrent_global, 11)
        self.assertEqual(resolved.max_call_attempts, 8)
        self.assertEqual(resolved.max_resume_attempts, 6)

    def test_provider_policy_resolver_rejects_non_strict_integer_values(self) -> None:
        module = self._load_module()

        for invalid_value in (True, "2"):
            with self.subTest(source="config", invalid_value=invalid_value):
                with self.assertRaises(ValueError):
                    module.resolve_provider_execution_policy(
                        provider="openai",
                        config_policy={"max_call_attempts": invalid_value},
                    )

            with self.subTest(source="cli", invalid_value=invalid_value):
                with self.assertRaises(ValueError):
                    module.resolve_provider_execution_policy(
                        provider="openai",
                        cli_overrides={"max_call_attempts": invalid_value},
                    )


if __name__ == "__main__":
    unittest.main()
