# Databricks notebook source
from datetime import datetime, timezone

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
demo_job_id = int(dbutils.widgets.get("demo_job_id"))
watcher_job_id = int(dbutils.widgets.get("watcher_job_id"))
analysis_job_id = int(dbutils.widgets.get("analysis_job_id"))
report_locale = dbutils.widgets.get("report_locale")

if not catalog.replace("_", "").isalnum() or not schema.replace("_", "").isalnum():
    raise ValueError("catalog and schema must be alphanumeric identifiers")

spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog}`")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`demo`")

ddl = {
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

for table, columns in ddl.items():
    spark.sql(f"CREATE TABLE IF NOT EXISTS `{catalog}`.`{schema}`.`{table}` ({columns}) USING DELTA")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS `{catalog}`.`demo`.`customer_events` (
  customer_id BIGINT, event_date DATE, event_type STRING, amount DOUBLE
) USING DELTA
""")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS `{catalog}`.`demo`.`customer_ltv` (
  customer_id BIGINT, ltv DOUBLE, as_of_date DATE, scenario STRING, source_run_id BIGINT
) USING DELTA
""")

now = datetime.now(timezone.utc)
principal = spark.sql("SELECT current_user()").first()[0]
watched = spark.createDataFrame(
    [(demo_job_id, "[AI Job Checker] Demo Customer LTV", True, "ACTIVE", "1.0.0", None, principal, now, now)],
    "job_id long, job_name string, enabled boolean, status string, policy_version string, output_table_overrides string, added_by string, added_at timestamp, updated_at timestamp",
)
watched.createOrReplaceTempView("bootstrap_watched_job")
spark.sql(f"""
MERGE INTO `{catalog}`.`{schema}`.`watched_jobs` AS target
USING bootstrap_watched_job AS source ON target.job_id = source.job_id
WHEN MATCHED THEN UPDATE SET target.job_name=source.job_name, target.enabled=true,
  target.status='ACTIVE', target.updated_at=source.updated_at
WHEN NOT MATCHED THEN INSERT *
""")

settings = spark.createDataFrame(
    [("default_report_locale", report_locale, now), ("watcher_job_id", str(watcher_job_id), now), ("analysis_job_id", str(analysis_job_id), now)],
    "setting_key string, setting_value string, updated_at timestamp",
)
settings.createOrReplaceTempView("bootstrap_settings")
spark.sql(f"""
MERGE INTO `{catalog}`.`{schema}`.`app_settings` target
USING bootstrap_settings source ON target.setting_key = source.setting_key
WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *
""")

print(f"Bootstrap complete for {catalog}.{schema}; watching demo job {demo_job_id}")
