from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="AI Job Checker")
catalog = os.environ.get("APP_CATALOG", "ai_job_checker")
schema = os.environ.get("APP_SCHEMA", "ops")
static_dir = Path(__file__).parent / "static"


def _connection():
    config = Config()
    return sql.connect(
        server_hostname=config.host.replace("https://", ""),
        http_path=f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}",
        credentials_provider=lambda: config.authenticate,
    )


def query(statement: str, parameters: list[Any] | None = None) -> list[dict[str, Any]]:
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(statement, parameters or [])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/reports")
def reports(limit: int = 50) -> list[dict[str, Any]]:
    safe_limit = min(max(limit, 1), 100)
    return query(f"""
      SELECT report_id, source_run_id, source_job_id, scenario, report_locale,
             verdict, severity, score, summary, policy_version, policy_hash,
             model_endpoint, created_at
      FROM `{catalog}`.`{schema}`.`run_reports`
      ORDER BY created_at DESC LIMIT {safe_limit}
    """)


@app.get("/api/reports/{run_id}")
def report_detail(run_id: int) -> dict[str, Any]:
    rows = query(f"SELECT * FROM `{catalog}`.`{schema}`.`run_reports` WHERE source_run_id=?", [run_id])
    if not rows:
        raise HTTPException(404, "Report not found")
    report = rows[0]
    report["evidence"] = json.loads(report.pop("evidence_json") or "[]")
    report["metrics"] = query(
        f"SELECT metric_key, metric_value, threshold_value, passed FROM `{catalog}`.`{schema}`.`quality_metrics` WHERE source_run_id=? ORDER BY metric_key",
        [run_id],
    )
    return report


class DemoRequest(BaseModel):
    scenario: str


@app.post("/api/demo")
def run_demo(request: DemoRequest) -> dict[str, Any]:
    if request.scenario not in {"normal", "stale", "incomplete", "semantic_bug", "runtime_failure"}:
        raise HTTPException(400, "Unknown scenario")
    run = WorkspaceClient().jobs.run_now(
        job_id=int(os.environ["DATABRICKS_JOB_DEMO"]),
        job_parameters={"scenario": request.scenario},
    )
    return {"run_id": run.run_id, "scenario": request.scenario, "status": "PENDING"}


@app.get("/")
def index():
    return FileResponse(static_dir / "index.html")


@app.get("/{path:path}")
def static(path: str):
    candidate = (static_dir / path).resolve()
    if static_dir.resolve() not in candidate.parents or not candidate.is_file():
        return FileResponse(static_dir / "index.html")
    return FileResponse(candidate)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("DATABRICKS_APP_PORT", "8000")))

