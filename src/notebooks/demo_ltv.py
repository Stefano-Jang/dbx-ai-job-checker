# Databricks notebook source
from datetime import date, timedelta
import time

catalog = dbutils.widgets.get("catalog")
scenario = dbutils.widgets.get("scenario")
allowed = {"normal", "stale", "incomplete", "semantic_bug", "runtime_failure"}
if scenario not in allowed:
    raise ValueError(f"scenario must be one of {sorted(allowed)}")
if not catalog.replace("_", "").isalnum():
    raise ValueError("invalid catalog")

run_id = int(dbutils.widgets.get("source_run_id"))
today = date.today()
events = []
for customer_id in range(1, 101):
    event_date = today - timedelta(days=2 if scenario == "stale" else 0)
    events.extend([
        (customer_id, event_date, "purchase", float(100 + customer_id)),
        (customer_id, event_date, "refund", -10.0 if customer_id % 10 == 0 else 0.0),
    ])
frame = spark.createDataFrame(events, "customer_id long, event_date date, event_type string, amount double")
frame.write.mode("overwrite").saveAsTable(f"{catalog}.demo.customer_events")

if scenario == "runtime_failure":
    raise RuntimeError("Intentional demo failure: upstream customer feed is unavailable")

frame.createOrReplaceTempView("current_events")
aggregation = "SUM(ABS(amount))" if scenario == "semantic_bug" else "SUM(amount)"
result = spark.sql(f"""
SELECT customer_id, {aggregation} AS ltv, MAX(event_date) AS as_of_date,
       '{scenario}' AS scenario, {run_id} AS source_run_id
FROM current_events GROUP BY customer_id
""")
if scenario == "incomplete":
    result = result.where("customer_id <= 90")
spark.sql(f"DELETE FROM `{catalog}`.`demo`.`customer_ltv` WHERE source_run_id={run_id}")
result.write.mode("append").saveAsTable(f"{catalog}.demo.customer_ltv")
time.sleep(2)
print(f"scenario={scenario}, run_id={run_id}, rows={result.count()}")
