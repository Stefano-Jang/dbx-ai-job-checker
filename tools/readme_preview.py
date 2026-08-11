"""Serve the production App UI with deterministic demo data for README screenshots."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).parents[1] / "src" / "app"))
import app as app_module  # noqa: E402


REPORTS = [
    ("semantic_bug", "FAIL", "MEDIUM", 50.0, 118664893924504),
    ("runtime_failure", "FAIL", "MEDIUM", 55.0, 10505),
    ("stale", "WARN", "LOW", 15.0, 10303),
    ("normal", "PASS", "NONE", 0.0, 10202),
    ("incomplete", "WARN", "LOW", 15.0, 10101),
]


def preview_query(statement: str, parameters=None):
    if "quality_metrics" in statement:
        return [
            {"metric_key": "completeness", "metric_value": 1.0, "threshold_value": 0.99, "passed": True},
            {"metric_key": "freshness_days", "metric_value": 0.0, "threshold_value": 1.0, "passed": True},
            {"metric_key": "semantic_policy_violations", "metric_value": 1.0, "threshold_value": 0.0, "passed": False},
        ]
    created_at = datetime(2026, 8, 12, 2, 40, tzinfo=timezone.utc)
    rows = [
        {
            "report_id": f"preview-{run_id}",
            "source_run_id": run_id,
            "source_job_id": 413874806864831,
            "scenario": scenario,
            "report_locale": "ko",
            "verdict": verdict,
            "severity": severity,
            "score": score,
            "summary": scenario.replace("_", " ").title(),
            "policy_version": "1.1.0",
            "policy_hash": "9b1e313cb37f",
            "model_endpoint": "databricks-claude-sonnet-4-6",
            "created_at": created_at,
            "evidence_json": '[{"source":"notebook_source","metric":"aggregation","value":"SUM(ABS(amount))"},{"source":"policy","metric":"ltv_definition","value":"sum of net revenue"}]',
            "suggested_diff": '''--- /Workspace/Jobs/customer_ltv/demo_ltv.py
+++ /Workspace/Jobs/customer_ltv/demo_ltv.py
@@ -28,7 +28,7 @@
 frame.createOrReplaceTempView("current_events")
-aggregation = "SUM(ABS(amount))" if scenario == "semantic_bug" else "SUM(amount)"
+aggregation = "SUM(amount)"
 result = spark.sql(f"""
 SELECT customer_id, {aggregation} AS ltv, MAX(event_date) AS as_of_date,
        '{scenario}' AS scenario, {run_id} AS source_run_id
 FROM current_events GROUP BY customer_id
 """)''',
            "policy_snapshot": "version: 1.1.0\nsemantics:\n  instructions:\n    - LTV must equal the per-customer sum of net revenue.",
        }
        for scenario, verdict, severity, score, run_id in REPORTS
    ]
    if "WHERE source_run_id" in statement:
        requested_run = int(parameters[0]) if parameters else rows[0]["source_run_id"]
        return [row for row in rows if row["source_run_id"] == requested_run]
    return rows


app_module.query = preview_query

if __name__ == "__main__":
    uvicorn.run(app_module.app, host="127.0.0.1", port=8765, log_level="warning")
