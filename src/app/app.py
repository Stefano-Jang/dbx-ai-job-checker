from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

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
    raw_evidence = json.loads(report.pop("evidence_json") or "[]")
    report["evidence"] = [item for item in raw_evidence if item.get("source") != "llm"]
    report["metrics"] = query(
        f"SELECT metric_key, metric_value, threshold_value, passed FROM `{catalog}`.`{schema}`.`quality_metrics` WHERE source_run_id=? ORDER BY metric_key",
        [run_id],
    )
    return report


class ChatRequest(BaseModel):
    message: str
    locale: str = "ko"
    history: list[dict[str, str]] = Field(default_factory=list)


@app.post("/api/reports/{run_id}/chat")
def report_chat(run_id: int, request: ChatRequest) -> dict[str, str]:
    message = request.message.strip()
    if not message:
        raise HTTPException(400, "Message is required")
    if len(message) > 2000:
        raise HTTPException(400, "Message is too long")
    report = report_detail(run_id)
    context = {
        key: report.get(key)
        for key in ("source_run_id", "source_job_id", "scenario", "verdict", "severity", "score",
                    "summary", "policy_version", "policy_hash", "policy_snapshot", "suggested_diff",
                    "metrics", "evidence")
    }
    language = "Korean" if request.locale == "ko" else "English"
    prior = [
        {"role": item.get("role"), "content": str(item.get("content", ""))[:2000]}
        for item in request.history[-6:]
        if item.get("role") in {"user", "assistant"}
    ]
    prompt = (
        f"You are a Databricks Code Agent explaining one Job run. Answer in {language}. "
        "Use ONLY the supplied run evidence; never invent logs, code, causes, or remediation. "
        "Clearly distinguish confirmed facts from inference. If evidence is insufficient, say so. "
        "Be concise and actionable.\n\n"
        f"RUN EVIDENCE:\n{json.dumps(context, ensure_ascii=False, default=str)}\n\n"
        f"CONVERSATION:\n{json.dumps(prior, ensure_ascii=False)}\n\nUSER QUESTION:\n{message}"
    )
    try:
        response = WorkspaceClient().serving_endpoints.query(
            name=os.environ["DATABRICKS_SERVING_ENDPOINT_NAME"],
            messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
            max_tokens=700,
        )
        answer = response.choices[0].message.content if response.choices else None
        if not answer:
            raise RuntimeError("Model returned an empty response")
        return {"answer": answer, "scope": "run_evidence_only"}
    except Exception as exc:
        raise HTTPException(502, f"Code Agent unavailable: {str(exc)[:300]}") from exc


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
