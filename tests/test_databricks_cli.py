import unittest
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


if __name__ == "__main__":
    unittest.main()
