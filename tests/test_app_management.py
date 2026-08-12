import importlib.util
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request


os.environ.setdefault("DATABRICKS_WAREHOUSE_ID", "test-warehouse")
APP_PATH = Path(__file__).parents[1] / "src" / "app" / "app.py"
SPEC = importlib.util.spec_from_file_location("job_checker_app", APP_PATH)
app_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(app_module)


def request(email="operator@databricks.com"):
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [(b"x-forwarded-email", email.encode())]})


class FakeJobs:
    def __init__(self):
        self.jobs = [
            SimpleNamespace(job_id=101, settings=SimpleNamespace(name="Customer 360")),
            SimpleNamespace(job_id=202, settings=SimpleNamespace(name="Finance LTV")),
        ]

    def list(self, **_kwargs):
        return iter(self.jobs)

    def get(self, job_id):
        return next(job for job in self.jobs if job.job_id == job_id)


class WatchedJobApiTest(unittest.TestCase):
    def setUp(self):
        self.client = SimpleNamespace(jobs=FakeJobs())

    def test_available_jobs_filters_by_name_or_id(self):
        with patch.object(app_module, "workspace_client", return_value=self.client):
            self.assertEqual([202], [row["job_id"] for row in app_module.available_jobs("ltv")])
            self.assertEqual([101], [row["job_id"] for row in app_module.available_jobs("101")])

    def test_register_uses_parameters_and_writes_audit(self):
        statements = []

        def record(statement, parameters=None):
            statements.append((statement, parameters or []))
            return []

        with (
            patch.object(app_module, "workspace_client", return_value=self.client),
            patch.object(app_module, "query", side_effect=record),
        ):
            result = app_module.register_watched_job(
                app_module.WatchedJobCreate(job_id=202, policy_version="finance-2.1"),
                request(),
            )

        self.assertEqual("Finance LTV", result["job_name"])
        self.assertEqual(2, len(statements))
        self.assertIn("MERGE INTO", statements[0][0])
        self.assertEqual([202, "Finance LTV", "finance-2.1", "operator@databricks.com"], statements[0][1])
        self.assertIn("watch_audit_log", statements[1][0])
        self.assertEqual("REGISTERED", statements[1][1][2])

    def test_invalid_policy_version_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            app_module._validate_policy_version("policy version with spaces")
        self.assertEqual(400, raised.exception.status_code)

    def test_pause_preserves_policy_and_records_actor(self):
        calls = []

        def query(statement, parameters=None):
            calls.append((statement, parameters or []))
            if "SELECT job_id, enabled" in statement:
                return [{"job_id": 202, "enabled": True, "policy_version": "finance-2.1"}]
            return []

        with patch.object(app_module, "query", side_effect=query):
            result = app_module.update_watched_job(
                202,
                app_module.WatchedJobUpdate(enabled=False),
                request("admin@databricks.com"),
            )

        self.assertFalse(result["enabled"])
        self.assertEqual([False, "PAUSED", "finance-2.1", 202], calls[1][1])
        self.assertEqual("PAUSED", calls[2][1][2])
        self.assertEqual("admin@databricks.com", calls[2][1][3])


if __name__ == "__main__":
    unittest.main()
