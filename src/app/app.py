from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="AI Job Checker")
catalog = os.environ.get("APP_CATALOG", "ai_job_checker")
schema = os.environ.get("APP_SCHEMA", "ops")
static_dir = Path(__file__).parent / "static"
policy_version_pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")

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


def workspace_client() -> WorkspaceClient:
    return WorkspaceClient()


def _actor(request: Request) -> str:
    return (
        request.headers.get("x-forwarded-email")
        or request.headers.get("x-forwarded-user")
        or "app-service-principal"
    )[:255]


def _validate_policy_version(value: str) -> str:
    version = value.strip()
    if not policy_version_pattern.fullmatch(version):
        raise HTTPException(400, "Policy version must be 1-32 letters, numbers, dots, underscores, or hyphens")
    return version


def _job_name(job: Any) -> str:
    settings = getattr(job, "settings", None)
    return str(getattr(settings, "name", None) or f"Job {job.job_id}")


def _write_audit(job_id: int, action: str, actor: str, details: dict[str, Any]) -> None:
    query(
        f"""
        INSERT INTO `{catalog}`.`{schema}`.`watch_audit_log`
          (event_id, job_id, action, actor, details_json, event_time)
        VALUES (?, ?, ?, ?, ?, current_timestamp())
        """,
        [str(uuid.uuid4()), job_id, action, actor, json.dumps(details, ensure_ascii=False)],
    )


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


@app.get("/api/whoami")
def whoami(request: Request) -> dict[str, Any]:
    return {
        "email": request.headers.get("x-forwarded-email"),
        "user": request.headers.get("x-forwarded-user"),
        "execution_identity": "app_service_principal",
    }


@app.get("/api/jobs")
def available_jobs(search: str = "", limit: int = 40) -> list[dict[str, Any]]:
    term = search.strip().lower()
    safe_limit = min(max(limit, 1), 100)
    try:
        jobs = workspace_client().jobs.list(limit=100)
        result = []
        for job in jobs:
            job_id = int(job.job_id)
            name = _job_name(job)
            if term and term not in name.lower() and term not in str(job_id):
                continue
            result.append({"job_id": job_id, "job_name": name, "permission_ready": True})
            if len(result) >= safe_limit:
                break
        return result
    except Exception as exc:
        raise HTTPException(502, f"Unable to list Jobs visible to the App service principal: {str(exc)[:240]}") from exc


@app.get("/api/watched-jobs")
def watched_jobs() -> list[dict[str, Any]]:
    rows = query(f"""
      SELECT w.job_id, w.job_name, w.enabled, w.status, w.policy_version,
             w.added_by, w.added_at, w.updated_at,
             s.last_run_id, s.last_checked_at, s.status AS watcher_status
      FROM `{catalog}`.`{schema}`.`watched_jobs` w
      LEFT JOIN `{catalog}`.`{schema}`.`watcher_state` s ON w.job_id=s.job_id
      ORDER BY w.enabled DESC, w.updated_at DESC
    """)
    client = workspace_client()
    for row in rows:
        try:
            job = client.jobs.get(int(row["job_id"]))
            row["job_name"] = _job_name(job)
            row["permission_ready"] = True
            row["permission_message"] = None
        except Exception as exc:
            row["permission_ready"] = False
            row["permission_message"] = str(exc)[:180]
    return rows


@app.get("/api/watched-jobs/audit")
def watched_job_audit(limit: int = 30) -> list[dict[str, Any]]:
    safe_limit = min(max(limit, 1), 100)
    rows = query(f"""
      SELECT event_id, job_id, action, actor, details_json, event_time
      FROM `{catalog}`.`{schema}`.`watch_audit_log`
      ORDER BY event_time DESC LIMIT {safe_limit}
    """)
    for row in rows:
        try:
            row["details"] = json.loads(row.pop("details_json") or "{}")
        except json.JSONDecodeError:
            row["details"] = {}
    return rows


class WatchedJobCreate(BaseModel):
    job_id: int = Field(gt=0)
    policy_version: str = "1.1.0"


@app.post("/api/watched-jobs", status_code=201)
def register_watched_job(payload: WatchedJobCreate, request: Request) -> dict[str, Any]:
    version = _validate_policy_version(payload.policy_version)
    try:
        job = workspace_client().jobs.get(payload.job_id)
    except Exception as exc:
        raise HTTPException(
            403,
            "The App service principal cannot access this Job. Grant CAN_VIEW on the Job, then try again.",
        ) from exc
    name = _job_name(job)
    actor = _actor(request)
    query(
        f"""
        MERGE INTO `{catalog}`.`{schema}`.`watched_jobs` target
        USING (SELECT CAST(? AS BIGINT) job_id, ? job_name, ? policy_version,
                      ? actor, current_timestamp() event_time) source
        ON target.job_id=source.job_id
        WHEN MATCHED THEN UPDATE SET target.job_name=source.job_name, target.enabled=true,
          target.status='ACTIVE', target.policy_version=source.policy_version,
          target.updated_at=source.event_time
        WHEN NOT MATCHED THEN INSERT
          (job_id, job_name, enabled, status, policy_version, output_table_overrides,
           added_by, added_at, updated_at)
        VALUES
          (source.job_id, source.job_name, true, 'ACTIVE', source.policy_version, NULL,
           source.actor, source.event_time, source.event_time)
        """,
        [payload.job_id, name, version, actor],
    )
    _write_audit(payload.job_id, "REGISTERED", actor, {"job_name": name, "policy_version": version})
    return {"job_id": payload.job_id, "job_name": name, "enabled": True, "policy_version": version}


class WatchedJobUpdate(BaseModel):
    enabled: bool | None = None
    policy_version: str | None = None


@app.patch("/api/watched-jobs/{job_id}")
def update_watched_job(job_id: int, payload: WatchedJobUpdate, request: Request) -> dict[str, Any]:
    if payload.enabled is None and payload.policy_version is None:
        raise HTTPException(400, "Provide enabled or policy_version")
    current = query(
        f"SELECT job_id, enabled, policy_version FROM `{catalog}`.`{schema}`.`watched_jobs` WHERE job_id=?",
        [job_id],
    )
    if not current:
        raise HTTPException(404, "Watched Job not found")
    enabled = bool(current[0]["enabled"]) if payload.enabled is None else payload.enabled
    version = current[0]["policy_version"] if payload.policy_version is None else _validate_policy_version(payload.policy_version)
    if enabled:
        try:
            workspace_client().jobs.get(job_id)
        except Exception as exc:
            raise HTTPException(403, "Grant the App service principal CAN_VIEW before activating this Job") from exc
    query(
        f"""
        UPDATE `{catalog}`.`{schema}`.`watched_jobs`
        SET enabled=?, status=?, policy_version=?, updated_at=current_timestamp()
        WHERE job_id=?
        """,
        [enabled, "ACTIVE" if enabled else "PAUSED", version, job_id],
    )
    actor = _actor(request)
    previous = current[0]
    action = "ACTIVATED" if enabled and not previous["enabled"] else "PAUSED" if not enabled and previous["enabled"] else "POLICY_UPDATED"
    _write_audit(job_id, action, actor, {"policy_version": version, "enabled": enabled})
    return {"job_id": job_id, "enabled": enabled, "status": "ACTIVE" if enabled else "PAUSED", "policy_version": version}


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
        response = workspace_client().serving_endpoints.query(
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
    run = workspace_client().jobs.run_now(
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
