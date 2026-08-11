# Databricks notebook source
from datetime import datetime, timezone
from databricks.sdk import WorkspaceClient

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
analysis_job_id = int(dbutils.widgets.get("analysis_job_id"))
table = lambda name: f"`{catalog}`.`{schema}`.`{name}`"
w = WorkspaceClient()
now = datetime.now(timezone.utc)

running_requests = spark.sql(f"""
  SELECT source_run_id, analyzer_run_id FROM {table('analysis_requests')}
  WHERE status='RUNNING' AND analyzer_run_id IS NOT NULL
""").collect()
for request in running_requests:
    analyzer = w.jobs.get_run(int(request.analyzer_run_id))
    lifecycle = analyzer.state.life_cycle_state.value if analyzer.state and analyzer.state.life_cycle_state else "UNKNOWN"
    result = analyzer.state.result_state.value if analyzer.state and analyzer.state.result_state else None
    if lifecycle in {"TERMINATED", "INTERNAL_ERROR", "SKIPPED"} and result != "SUCCESS":
        message = (analyzer.state.state_message or "Analyzer terminated without a report").replace("'", "''")[:1000]
        spark.sql(f"""UPDATE {table('analysis_requests')} SET status='FAILED', error='{message}',
          updated_at=current_timestamp() WHERE source_run_id={int(request.source_run_id)}""")

watched = spark.sql(f"SELECT job_id FROM {table('watched_jobs')} WHERE enabled = true AND status = 'ACTIVE'").collect()
for watched_row in watched:
    job_id = watched_row.job_id
    state = spark.sql(f"SELECT last_end_time, last_run_id FROM {table('watcher_state')} WHERE job_id={job_id}").first()
    last_run_id = state.last_run_id if state else 0
    last_end_time = state.last_end_time if state and state.last_end_time else datetime.fromtimestamp(0, timezone.utc).replace(tzinfo=None)
    runs = list(w.jobs.list_runs(job_id=job_id, completed_only=True, limit=25))
    for run in sorted(runs, key=lambda item: (item.end_time or 0, item.run_id or 0)):
        run_id = int(run.run_id)
        run_end_time = datetime.fromtimestamp((run.end_time or 0) / 1000, timezone.utc).replace(tzinfo=None)
        if (run_end_time, run_id) <= (last_end_time, last_run_id):
            continue
        state_name = run.state.result_state.value if run.state and run.state.result_state else "UNKNOWN"
        scenario = "unknown"
        for parameter in run.job_parameters or []:
            if parameter.name == "scenario":
                scenario = parameter.value
        locale_row = spark.sql(f"SELECT setting_value FROM {table('app_settings')} WHERE setting_key='default_report_locale'").first()
        locale = locale_row.setting_value if locale_row else "ko"
        request = spark.createDataFrame(
            [(run_id, job_id, scenario, locale, "PENDING", None, now, now, None)],
            "source_run_id long, source_job_id long, scenario string, report_locale string, status string, analyzer_run_id long, requested_at timestamp, updated_at timestamp, error string",
        )
        request.createOrReplaceTempView("new_analysis_request")
        spark.sql(f"""
        MERGE INTO {table('analysis_requests')} target USING new_analysis_request source
        ON target.source_run_id = source.source_run_id
        WHEN NOT MATCHED THEN INSERT *
        """)
        existing = spark.sql(f"SELECT status FROM {table('analysis_requests')} WHERE source_run_id={run_id}").first()
        if existing.status == "PENDING":
            launched = w.jobs.run_now(job_id=analysis_job_id, job_parameters={
                "source_job_id": str(job_id), "source_run_id": str(run_id),
                "scenario": scenario, "report_locale": locale,
            })
            spark.sql(f"""UPDATE {table('analysis_requests')}
              SET status='RUNNING', analyzer_run_id={int(launched.run_id)}, updated_at=current_timestamp()
              WHERE source_run_id={run_id}""")
        last_end_time, last_run_id = run_end_time, run_id
    state_df = spark.createDataFrame([(job_id, last_end_time, last_run_id, now, "OK")],
        "job_id long, last_end_time timestamp, last_run_id long, last_checked_at timestamp, status string")
    state_df.createOrReplaceTempView("new_watcher_state")
    spark.sql(f"""MERGE INTO {table('watcher_state')} target USING new_watcher_state source
      ON target.job_id=source.job_id WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *""")

print(f"Checked {len(watched)} watched jobs")
