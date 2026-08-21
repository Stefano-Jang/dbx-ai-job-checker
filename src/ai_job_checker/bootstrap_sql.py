from __future__ import annotations

import re


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


OPERATIONAL_TABLES = {
    "watched_jobs": """
      job_id BIGINT, job_name STRING, enabled BOOLEAN, status STRING,
      policy_version STRING, output_table_overrides STRING, added_by STRING,
      added_at TIMESTAMP, updated_at TIMESTAMP
    """,
    "watcher_state": """
      job_id BIGINT, last_end_time TIMESTAMP, last_run_id BIGINT,
      last_checked_at TIMESTAMP, status STRING
    """,
    "analysis_requests": """
      source_run_id BIGINT, source_job_id BIGINT, scenario STRING,
      report_locale STRING, status STRING, analyzer_run_id BIGINT,
      requested_at TIMESTAMP, updated_at TIMESTAMP, error STRING
    """,
    "run_reports": """
      report_id STRING, source_run_id BIGINT, source_job_id BIGINT, scenario STRING,
      report_locale STRING, verdict STRING, severity STRING, score DOUBLE,
      summary STRING, evidence_json STRING, suggested_diff STRING,
      policy_version STRING, policy_hash STRING, policy_snapshot STRING,
      model_endpoint STRING, created_at TIMESTAMP
    """,
    "quality_metrics": """
      source_run_id BIGINT, metric_key STRING, metric_value DOUBLE,
      threshold_value DOUBLE, passed BOOLEAN, measured_at TIMESTAMP
    """,
    "source_snapshots": """
      source_run_id BIGINT, task_key STRING, source_path STRING,
      source_text STRING, captured_at TIMESTAMP
    """,
    "llm_invocations": """
      source_run_id BIGINT, endpoint STRING, status STRING, latency_ms BIGINT,
      input_tokens BIGINT, output_tokens BIGINT, error STRING, invoked_at TIMESTAMP
    """,
    "analysis_policy_versions": """
      policy_version STRING, policy_hash STRING, policy_snapshot STRING,
      active BOOLEAN, created_at TIMESTAMP
    """,
    "app_settings": """
      setting_key STRING, setting_value STRING, updated_at TIMESTAMP
    """,
    "watch_audit_log": """
      event_id STRING, job_id BIGINT, action STRING, actor STRING,
      details_json STRING, event_time TIMESTAMP
    """,
}


def validate_identifier(value: object, label: str) -> str:
    identifier = str(value)
    if not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ValueError(f"{label}는 영문자, 숫자, underscore만 사용할 수 있습니다: {identifier}")
    return identifier


def initialization_statements(catalog_value: object, schema_value: object) -> list[str]:
    """Return idempotent DDL required before App resources are attached."""
    catalog = validate_identifier(catalog_value, "catalog")
    schema = validate_identifier(schema_value, "schema")
    statements = [
        f"CREATE CATALOG IF NOT EXISTS `{catalog}`",
        f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`",
        f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`demo`",
    ]
    statements.extend(
        f"CREATE TABLE IF NOT EXISTS `{catalog}`.`{schema}`.`{table}` ({columns}) USING DELTA"
        for table, columns in OPERATIONAL_TABLES.items()
    )
    statements.extend([
        f"""CREATE TABLE IF NOT EXISTS `{catalog}`.`demo`.`customer_events` (
          customer_id BIGINT, event_date DATE, event_type STRING, amount DOUBLE
        ) USING DELTA""",
        f"""CREATE TABLE IF NOT EXISTS `{catalog}`.`demo`.`customer_ltv` (
          customer_id BIGINT, ltv DOUBLE, as_of_date DATE, scenario STRING, source_run_id BIGINT
        ) USING DELTA""",
    ])
    return statements
