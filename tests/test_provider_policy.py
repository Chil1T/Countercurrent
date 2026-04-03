import importlib
import importlib.util
import json
import shutil
import tempfile
import threading
import types
import unittest
from pathlib import Path

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

    def test_provider_limit_recovers_from_corrupt_limit_file(self) -> None:
        module = self._load_module()
        with tempfile.TemporaryDirectory() as tmp:
            registry = module.ProviderPermitRegistry(root_dir=Path(tmp))
            provider_dir = Path(tmp) / "stub"
            provider_dir.mkdir(parents=True)
            (provider_dir / "limit.json").write_text("{", encoding="utf-8")
            policy = module.ProviderExecutionPolicy(
                provider="stub",
                max_concurrent_per_run=1,
                max_concurrent_global=2,
                transient_http_statuses=(),
                max_call_attempts=1,
                max_resume_attempts=1,
            )

            with registry.acquire(policy):
                self.assertEqual(registry.active_permits("stub"), 1)

            self.assertEqual(
                json.loads((provider_dir / "limit.json").read_text(encoding="utf-8"))["max_concurrent_global"],
                2,
            )

    def test_stale_provider_permit_slot_is_reclaimed(self) -> None:
        module = self._load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root_dir = Path(tmp)
            registry = module.ProviderPermitRegistry(root_dir=root_dir, poll_interval_seconds=0.01)
            provider_dir = root_dir / "stub"
            slot_dir = provider_dir / "slot-00"
            slot_dir.mkdir(parents=True)
            (provider_dir / "limit.json").write_text(
                json.dumps({"max_concurrent_global": 1}, ensure_ascii=False),
                encoding="utf-8",
            )
            (slot_dir / "owner.json").write_text(
                json.dumps({"pid": 99999999, "acquired_at": 0}, ensure_ascii=False),
                encoding="utf-8",
            )
            policy = module.ProviderExecutionPolicy(
                provider="stub",
                max_concurrent_per_run=1,
                max_concurrent_global=1,
                transient_http_statuses=(),
                max_call_attempts=1,
                max_resume_attempts=1,
            )

            entered = threading.Event()
            errors: list[Exception] = []

            def target() -> None:
                try:
                    with registry.acquire(policy):
                        entered.set()
                except Exception as error:
                    errors.append(error)

            worker = threading.Thread(target=target, daemon=True)
            worker.start()
            try:
                self.assertTrue(entered.wait(timeout=1), "stale provider slot was not reclaimed")
            finally:
                if worker.is_alive():
                    shutil.rmtree(slot_dir, ignore_errors=True)
                    worker.join(timeout=1)

            self.assertEqual(errors, [])

    def test_provider_limit_change_does_not_interleave_with_slot_allocation(self) -> None:
        module = self._load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root_dir = Path(tmp)
            registry_a = module.ProviderPermitRegistry(root_dir=root_dir, poll_interval_seconds=0.01)
            registry_b = module.ProviderPermitRegistry(root_dir=root_dir, poll_interval_seconds=0.01)
            high_policy = module.ProviderExecutionPolicy(
                provider="stub",
                max_concurrent_per_run=1,
                max_concurrent_global=2,
                transient_http_statuses=(),
                max_call_attempts=1,
                max_resume_attempts=1,
            )
            low_policy = module.ProviderExecutionPolicy(
                provider="stub",
                max_concurrent_per_run=1,
                max_concurrent_global=1,
                transient_http_statuses=(),
                max_call_attempts=1,
                max_resume_attempts=1,
            )
            limit_ready = threading.Event()
            allow_first = threading.Event()
            first_entered = threading.Event()
            second_entered = threading.Event()
            release_first = threading.Event()
            release_second = threading.Event()
            errors: list[Exception] = []

            original_ensure = registry_a._ensure_provider_limit

            def wrapped_ensure(self, provider_dir: Path, policy: object) -> int:
                configured_limit = original_ensure(provider_dir, policy)
                limit_ready.set()
                allow_first.wait(timeout=2)
                return configured_limit

            registry_a._ensure_provider_limit = types.MethodType(wrapped_ensure, registry_a)

            def run_first() -> None:
                try:
                    with registry_a.acquire(high_policy):
                        first_entered.set()
                        release_first.wait(timeout=2)
                except Exception as error:
                    errors.append(error)

            def run_second() -> None:
                try:
                    with registry_b.acquire(low_policy):
                        second_entered.set()
                        release_second.wait(timeout=2)
                except Exception as error:
                    errors.append(error)

            first_thread = threading.Thread(target=run_first, daemon=True)
            second_thread = threading.Thread(target=run_second, daemon=True)
            first_thread.start()
            self.assertTrue(limit_ready.wait(timeout=1))
            second_thread.start()

            self.assertFalse(
                second_entered.wait(timeout=0.2),
                "lower-limit acquisition interleaved before earlier slot allocation linearized",
            )

            allow_first.set()
            self.assertTrue(first_entered.wait(timeout=1))
            release_first.set()
            first_thread.join(timeout=2)
            self.assertFalse(first_thread.is_alive())
            self.assertTrue(second_entered.wait(timeout=1))
            release_second.set()
            second_thread.join(timeout=2)
            self.assertFalse(second_thread.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(
                json.loads((root_dir / "stub" / "limit.json").read_text(encoding="utf-8"))["max_concurrent_global"],
                1,
            )

    def test_provider_limit_change_waits_for_active_permit_drain_instead_of_failing(self) -> None:
        module = self._load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root_dir = Path(tmp)
            registry_a = module.ProviderPermitRegistry(root_dir=root_dir, poll_interval_seconds=0.01)
            registry_b = module.ProviderPermitRegistry(root_dir=root_dir, poll_interval_seconds=0.01)
            high_policy = module.ProviderExecutionPolicy(
                provider="stub",
                max_concurrent_per_run=1,
                max_concurrent_global=2,
                transient_http_statuses=(),
                max_call_attempts=1,
                max_resume_attempts=1,
            )
            low_policy = module.ProviderExecutionPolicy(
                provider="stub",
                max_concurrent_per_run=1,
                max_concurrent_global=1,
                transient_http_statuses=(),
                max_call_attempts=1,
                max_resume_attempts=1,
            )
            first_entered = threading.Event()
            allow_first_release = threading.Event()
            second_entered = threading.Event()
            allow_second_release = threading.Event()
            errors: list[Exception] = []

            def run_first() -> None:
                try:
                    with registry_a.acquire(high_policy):
                        first_entered.set()
                        allow_first_release.wait(timeout=2)
                except Exception as error:
                    errors.append(error)

            def run_second() -> None:
                try:
                    with registry_b.acquire(low_policy):
                        second_entered.set()
                        allow_second_release.wait(timeout=2)
                except Exception as error:
                    errors.append(error)

            first_thread = threading.Thread(target=run_first, daemon=True)
            second_thread = threading.Thread(target=run_second, daemon=True)
            first_thread.start()
            self.assertTrue(first_entered.wait(timeout=1))
            second_thread.start()
            self.assertFalse(
                second_entered.wait(timeout=0.2),
                "lower global limit should wait for active permits to drain",
            )

            allow_first_release.set()
            first_thread.join(timeout=2)
            self.assertFalse(first_thread.is_alive())
            self.assertTrue(second_entered.wait(timeout=1))
            allow_second_release.set()
            second_thread.join(timeout=2)
            self.assertFalse(second_thread.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(
                json.loads((root_dir / "stub" / "limit.json").read_text(encoding="utf-8"))["max_concurrent_global"],
                1,
            )

    def test_same_pid_with_different_process_start_time_is_treated_as_stale(self) -> None:
        module = self._load_module()
        owner_payload = {
            "pid": 4242,
            "process_started_at": "old-start",
        }

        self.assertFalse(
            module._owner_refers_to_live_process(
                owner_payload,
                identity_reader=lambda pid: ("new-start" if pid == 4242 else None),
            )
        )


if __name__ == "__main__":
    unittest.main()
