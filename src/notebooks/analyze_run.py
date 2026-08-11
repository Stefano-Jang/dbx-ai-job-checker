# Databricks notebook source
import hashlib
import base64
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
from databricks.sdk.service.workspace import ExportFormat

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
source_job_id = int(dbutils.widgets.get("source_job_id"))
source_run_id = int(dbutils.widgets.get("source_run_id"))
scenario = dbutils.widgets.get("scenario")
locale = dbutils.widgets.get("report_locale")
endpoint = dbutils.widgets.get("serving_endpoint")
policy_path_value = dbutils.widgets.get("policy_path")
table = lambda name: f"`{catalog}`.`{schema}`.`{name}`"

policy_path = Path(policy_path_value)
policy_snapshot = policy_path.read_text(encoding="utf-8")
policy_hash = hashlib.sha256(policy_snapshot.encode()).hexdigest()
policy = yaml.safe_load(policy_snapshot)

w = WorkspaceClient()
run = w.jobs.get_run(source_run_id)
duration_ms = max(0, (run.end_time or 0) - (run.start_time or 0))
result_state = run.state.result_state.value if run.state and run.state.result_state else "UNKNOWN"

# Capture the actual task source for this run. This makes remediation portable to
# customer Jobs instead of coupling the analyzer to the bundled demo notebook.
source_snapshots = []
run_tasks = list(run.tasks or [])
if not run_tasks:
    job = w.jobs.get(source_job_id)
    run_tasks = list(job.settings.tasks or []) if job.settings else []
for task in run_tasks:
    notebook_task = getattr(task, "notebook_task", None)
    source_path = getattr(notebook_task, "notebook_path", None)
    if not source_path:
        continue
    try:
        exported = w.workspace.export(source_path, format=ExportFormat.SOURCE)
        source_text = base64.b64decode(exported.content).decode("utf-8", errors="replace")
        source_snapshots.append((getattr(task, "task_key", "unknown"), source_path, source_text[:50000]))
    except Exception as exc:
        evidence_note = f"Unable to capture {source_path}: {str(exc)[:300]}"
        source_snapshots.append((getattr(task, "task_key", "unknown"), source_path, evidence_note))

spark.sql(f"DELETE FROM {table('source_snapshots')} WHERE source_run_id={source_run_id}")
if source_snapshots:
    source_df = spark.createDataFrame(
        [(source_run_id, task_key, path, text, datetime.now(timezone.utc))
         for task_key, path, text in source_snapshots],
        "source_run_id long, task_key string, source_path string, source_text string, captured_at timestamp",
    )
    source_df.write.mode("append").saveAsTable(f"{catalog}.{schema}.source_snapshots")

metrics = []
evidence = [{"source": "jobs_api", "metric": "result_state", "value": result_state},
            {"source": "jobs_api", "metric": "duration_ms", "value": duration_ms}]

if result_state != "SUCCESS":
    completeness, freshness_days, null_ids, duplicate_ids, negative_ltv = 0.0, 999.0, 0.0, 0.0, 0.0
else:
    row = spark.sql(f"""
      SELECT COUNT(*) rows, COUNT(DISTINCT customer_id) distinct_customers,
             SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) null_ids,
             SUM(CASE WHEN ltv < 0 THEN 1 ELSE 0 END) negative_ltv,
             DATEDIFF(current_date(), MAX(as_of_date)) freshness_days
      FROM `{catalog}`.`demo`.`customer_ltv` WHERE source_run_id={source_run_id}
    """).first()
    input_customers = 100
    completeness = float(row.distinct_customers or 0) / max(float(input_customers or 0), 1.0)
    freshness_days = float(999 if row.freshness_days is None else row.freshness_days)
    null_ids = float(row.null_ids or 0)
    duplicate_ids = float((row.rows or 0) - (row.distinct_customers or 0))
    negative_ltv = float(row.negative_ltv or 0)

metric_values = [
    ("completeness", completeness, 0.99, completeness >= 0.99),
    ("freshness_days", freshness_days, 1.0, freshness_days <= 1.0),
    ("customer_id_nulls", null_ids, 0.0, null_ids == 0),
    ("customer_id_duplicates", duplicate_ids, 0.0, duplicate_ids == 0),
    ("negative_ltv", negative_ltv, 0.0, negative_ltv == 0),
]
now = datetime.now(timezone.utc)
evidence.extend({"source": "quality_metrics", "metric": key, "value": value, "threshold": threshold, "passed": passed}
                for key, value, threshold, passed in metric_values)
suggested_diff = ""
semantic_failed = False
semantic_finding = ""

prompt = json.dumps({
    "output_language": locale, "scenario": scenario, "result_state": result_state,
    "policy_hash": policy_hash,
    "semantic_instructions": policy.get("semantics", {}).get("instructions", []),
    "evidence": evidence,
    "task_sources": [{"task_key": key, "path": path, "source": text}
                     for key, path, text in source_snapshots],
    "instruction": (
        "Evaluate the actual task source against every natural-language semantic instruction. Output "
        "exactly one <SEMANTIC_VERDICT>PASS|FAIL|UNKNOWN</SEMANTIC_VERDICT> and a concise "
        "<SEMANTIC_FINDING>...</SEMANTIC_FINDING>. Use FAIL only when source code directly contradicts "
        "an instruction; use UNKNOWN when source is unavailable or insufficient. Output <DIFF>...</DIFF> "
        "next. If and "
        "only if the evidence proves a code issue, place a valid unified diff inside it; otherwise "
        "return <DIFF></DIFF>. The diff must use the exact supplied source path, include ---/+++, a "
        "hunk header, and at least three unchanged context lines before and after the edit. Never "
        "invent a file or code. Then briefly state confirmed facts, inferences, and a recommended "
        "action inside <ANALYSIS>...</ANALYSIS>. Do not use markdown fences."
    ),
}, ensure_ascii=False)
llm_status, llm_error, latency_ms = "SKIPPED", None, 0
diff_validation = None
start = time.monotonic()
try:
    response = w.serving_endpoints.query(
        name=endpoint,
        messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
        max_tokens=1600,
    )
    latency_ms = int((time.monotonic() - start) * 1000)
    llm_status = "SUCCESS"
    if response.choices and response.choices[0].message.content:
        llm_text = response.choices[0].message.content
        verdict_start, verdict_end = llm_text.find("<SEMANTIC_VERDICT>"), llm_text.find("</SEMANTIC_VERDICT>")
        semantic_verdict = (llm_text[verdict_start + 18:verdict_end].strip().upper()
                            if 0 <= verdict_start < verdict_end else "UNKNOWN")
        finding_start, finding_end = llm_text.find("<SEMANTIC_FINDING>"), llm_text.find("</SEMANTIC_FINDING>")
        semantic_finding = (llm_text[finding_start + 18:finding_end].strip()[:2000]
                            if 0 <= finding_start < finding_end else "")
        semantic_failed = result_state == "SUCCESS" and semantic_verdict == "FAIL" and bool(source_snapshots)
        diff_start, diff_end = llm_text.find("<DIFF>"), llm_text.find("</DIFF>")
        candidate_diff = (llm_text[diff_start + 6:diff_end].strip()
                          if 0 <= diff_start < diff_end else "")
        if candidate_diff.startswith("```"):
            candidate_diff = candidate_diff.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        diff_lines = candidate_diff.splitlines()
        header = "\n".join(diff_lines[:2])
        matching_sources = [
            (path, text) for _, path, text in source_snapshots
            if (path in header or Path(path).name in header
                or f"{Path(path).name}.py" in header)
        ]
        removed_lines = [line[1:] for line in diff_lines if line.startswith("-") and not line.startswith("---")]
        context_lines = [line[1:] for line in diff_lines if line.startswith(" ")]
        source_verified = any(
            removed_lines and all(line in text for line in removed_lines)
            for _, text in matching_sources
        )
        if (candidate_diff.startswith("--- ") and "\n+++ " in candidate_diff
                and "\n@@" in candidate_diff and len(context_lines) >= 3 and source_verified):
            suggested_diff = candidate_diff[:20000]
        elif semantic_failed:
            llm_status = "REJECTED"
            diff_validation = {
                "reason": "suggested diff did not match captured source",
                "header": header[:500],
                "removed_lines": removed_lines[:10],
                "context_line_count": len(context_lines),
                "matching_source_count": len(matching_sources),
                "has_hunk": "\n@@" in candidate_diff,
            }
            llm_error = json.dumps(diff_validation, ensure_ascii=False)[:2000]
except Exception as exc:
    latency_ms = int((time.monotonic() - start) * 1000)
    llm_status, llm_error = "FAILED", str(exc)[:2000]
    evidence.append({"source": "llm", "metric": "fallback", "value": llm_error})

if semantic_failed:
    metric_values.append(("semantic_policy_violations", 1.0, 0.0, False))
    evidence.append({"source": "semantic_policy", "metric": "semantic_policy_violations",
                     "value": 1.0, "threshold": 0.0, "passed": False,
                     "finding": semantic_finding})

metric_df = spark.createDataFrame(
    [(source_run_id, key, value, threshold, passed, now) for key, value, threshold, passed in metric_values],
    "source_run_id long, metric_key string, metric_value double, threshold_value double, passed boolean, measured_at timestamp",
)
spark.sql(f"DELETE FROM {table('quality_metrics')} WHERE source_run_id={source_run_id}")
metric_df.write.mode("append").saveAsTable(f"{catalog}.{schema}.quality_metrics")

known_summary = {
    "normal": "실행과 LTV 품질 기준이 정상 범위입니다.",
    "stale": "LTV 산출 데이터의 freshness 기준을 초과했습니다.",
    "incomplete": "입력 대비 산출 고객 completeness가 기준 미만입니다.",
    "semantic_bug": "LTV 구현이 자연어 semantic policy를 위반했습니다.",
    "runtime_failure": "원본 Job이 의도된 런타임 오류로 실패했습니다.",
}
if locale == "en":
    known_summary = {
        "normal": "The run and LTV quality checks are within policy.",
        "stale": "The LTV output exceeds the freshness threshold.",
        "incomplete": "Output customer completeness is below policy.",
        "semantic_bug": "The LTV implementation violates the natural-language semantic policy.",
        "runtime_failure": "The source job failed with the expected demo runtime error.",
    }

failed_count = sum(not passed for *_, passed in metric_values)
score = min(100.0, failed_count * 15.0 + (35.0 if semantic_failed else 0.0) + (25.0 if result_state != "SUCCESS" else 0.0))
severity = "CRITICAL" if score >= 80 else "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW" if score > 0 else "NONE"
verdict = "FAIL" if score >= 30 else "WARN" if score > 0 else "PASS"
summary = known_summary.get(scenario, "Run analysis completed from available evidence.")

llm_df = spark.createDataFrame([(source_run_id, endpoint, llm_status, latency_ms, None, None, llm_error, now)],
    "source_run_id long, endpoint string, status string, latency_ms long, input_tokens long, output_tokens long, error string, invoked_at timestamp")
llm_df.write.mode("append").saveAsTable(f"{catalog}.{schema}.llm_invocations")

report = spark.createDataFrame([(
    str(uuid.uuid4()), source_run_id, source_job_id, scenario, locale, verdict, severity, score,
    summary, json.dumps(evidence, ensure_ascii=False), suggested_diff, str(policy["version"]), policy_hash,
    policy_snapshot, endpoint, now,
)], "report_id string, source_run_id long, source_job_id long, scenario string, report_locale string, verdict string, severity string, score double, summary string, evidence_json string, suggested_diff string, policy_version string, policy_hash string, policy_snapshot string, model_endpoint string, created_at timestamp")
report.createOrReplaceTempView("new_run_report")
spark.sql(f"""MERGE INTO {table('run_reports')} target USING new_run_report source
  ON target.source_run_id=source.source_run_id
  WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *""")
spark.sql(f"""UPDATE {table('analysis_requests')} SET status='COMPLETED', updated_at=current_timestamp()
  WHERE source_run_id={source_run_id}""")
print(f"Analysis complete: run={source_run_id}, verdict={verdict}, severity={severity}, llm={llm_status}")
