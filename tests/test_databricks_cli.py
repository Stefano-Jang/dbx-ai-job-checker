import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

from ai_job_checker import cli
from ai_job_checker.databricks_cli import Profile, parse_version


class VersionTest(unittest.TestCase):
    def test_modern_cli_version(self) -> None:
        self.assertEqual(parse_version("Databricks CLI v1.11.0"), (1, 11, 0))

    def test_node_version(self) -> None:
        self.assertEqual(parse_version("v22.18.0"), (22, 18, 0))

    def test_unparseable_version(self) -> None:
        self.assertIsNone(parse_version("unknown"))


class ProfileSelectionTest(unittest.TestCase):
    @patch("ai_job_checker.cli.sys.stdin")
    @patch("ai_job_checker.cli.databricks_cli.list_profiles")
    def test_noninteractive_mode_never_auto_selects_profile(
        self, list_profiles: MagicMock, stdin: MagicMock
    ) -> None:
        list_profiles.return_value = [Profile("only-profile", "https://example.com", True)]
        stdin.isatty.return_value = False
        with self.assertRaisesRegex(RuntimeError, "자동 선택하지 않습니다"):
            cli._choose_profile(None)

    @patch("ai_job_checker.cli.databricks_cli.list_profiles")
    def test_requested_profile_must_exist(self, list_profiles: MagicMock) -> None:
        list_profiles.return_value = [Profile("customer", "https://example.com", True)]
        with self.assertRaisesRegex(RuntimeError, "알 수 없는 profile"):
            cli._choose_profile("DEFAULT")


class BundleVariablesTest(unittest.TestCase):
    def test_all_configurable_values_are_forwarded(self) -> None:
        self.assertEqual(
            cli._bundle_vars({
                "warehouse_id": "abc123",
                "catalog": "customer_catalog",
                "schema": "job_ops",
                "model": "databricks-claude-sonnet-4-6",
                "default_report_locale": "en",
            }),
            [
                "--var", "warehouse_id=abc123",
                "--var", "catalog=customer_catalog",
                "--var", "schema=job_ops",
                "--var", "serving_endpoint=databricks-claude-sonnet-4-6",
                "--var", "report_locale=en",
            ],
        )


class FreshDeploymentTest(unittest.TestCase):
    @patch("ai_job_checker.cli._run_checked")
    def test_uc_objects_are_initialized_idempotently_before_bundle_deploy(self, run_checked: MagicMock) -> None:
        config = {
            "warehouse_id": "warehouse-123",
            "catalog": "customer_catalog",
            "schema": "job_ops",
        }
        cli._initialize_uc(config, "customer")

        commands = [call.args[0] for call in run_checked.call_args_list]
        self.assertGreater(len(commands), 3)
        self.assertEqual(
            commands[0],
            [
                "databricks", "experimental", "aitools", "tools", "query",
                "--warehouse", "warehouse-123", "--profile", "customer",
                "CREATE CATALOG IF NOT EXISTS `customer_catalog`",
            ],
        )
        self.assertTrue(all("IF NOT EXISTS" in command[-1] for command in commands))
        self.assertTrue(any("`customer_catalog`.`job_ops`.`run_reports`" in command[-1] for command in commands))

    def test_invalid_catalog_is_rejected_before_sql_execution(self) -> None:
        with self.assertRaisesRegex(ValueError, "catalog"):
            cli._initialize_uc(
                {"warehouse_id": "warehouse-123", "catalog": "bad-name", "schema": "ops"},
                "customer",
            )

    @patch("ai_job_checker.cli.save_json")
    @patch("ai_job_checker.cli._run_checked")
    @patch("ai_job_checker.cli._configured")
    def test_deploy_initializes_tables_before_bundle_resources(
        self, configured: MagicMock, run_checked: MagicMock, _save_json: MagicMock
    ) -> None:
        configured.return_value = {
            "profile": "customer",
            "warehouse_id": "warehouse-123",
            "catalog": "customer_catalog",
            "schema": "job_ops",
            "model": "databricks-claude-sonnet-4-6",
            "default_report_locale": "ko",
        }

        self.assertEqual(0, cli.deploy(Namespace(yes=True, target="nexon", force_lock=False)))

        commands = [call.args[0] for call in run_checked.call_args_list]
        first_bundle_command = next(index for index, command in enumerate(commands) if command[1] == "bundle")
        self.assertGreater(first_bundle_command, 0)
        self.assertTrue(all(command[1:5] == ["experimental", "aitools", "tools", "query"] for command in commands[:first_bundle_command]))
        self.assertEqual("validate", commands[first_bundle_command][2])
        deploy_call = next(call for call in run_checked.call_args_list if call.args[0][1:3] == ["bundle", "deploy"])
        self.assertEqual({"DATABRICKS_BUNDLE_ENGINE": "terraform"}, deploy_call.kwargs["env"])
        self.assertNotIn("--force-lock", deploy_call.args[0])


if __name__ == "__main__":
    unittest.main()
