import json
import tempfile
import unittest
from pathlib import Path

from ai_job_checker.state import load_json, save_json


class StateTest(unittest.TestCase):
    def test_tracked_example_has_required_non_sensitive_fields(self) -> None:
        example = load_json(Path(__file__).parents[1] / ".local" / "config.example.json")
        self.assertEqual(
            set(example),
            {"catalog", "default_report_locale", "model", "profile", "schema", "warehouse_id", "workspace_host"},
        )
        self.assertNotIn("token", json.dumps(example).lower())

    def test_round_trip_and_private_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_json(path, {"profile": "customer", "locale": "ko"})
            self.assertEqual(load_json(path)["profile"], "customer")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_rejects_nested_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            with self.assertRaisesRegex(ValueError, "sensitive field"):
                save_json(path, {"auth": {"access_token": "never-write-this"}})
            self.assertFalse(path.exists())

    def test_rejects_non_object_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps([]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                load_json(path)


if __name__ == "__main__":
    unittest.main()
