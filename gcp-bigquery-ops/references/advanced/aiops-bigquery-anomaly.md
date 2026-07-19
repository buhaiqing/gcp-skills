# AIOps Anomaly Detection — Google Cloud BigQuery

> Provides data engineers with a guide to implementing AIOps-driven anomaly detection for BigQuery — slot utilization monitoring, query performance anomalies, storage growth prediction, and automated remediation.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Slot Utilization Monitoring](#slot-utilization-monitoring)
5. [Query Performance Anomalies](#query-performance-anomalies)
6. [Storage Growth Prediction](#storage-growth-prediction)
7. [Job Failure Pattern Detection](#job-failure-pattern-detection)
8. [Real-Time Alerting](#real-time-alerting)
9. [Automated Remediation](#automated-remediation)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [Cost Optimization](#cost-optimization)
13. [See Also](#see-also)

## Overview

AIOps (Artificial Intelligence for IT Operations) uses machine learning and data analysis to detect anomalies in BigQuery workloads. With BigQuery's built-in monitoring and integration with Cloud Monitoring, you can:

- Detect slot utilization spikes (potential query performance degradation)
- Identify query performance anomalies (slow queries, resource exhaustion)
- Monitor storage growth patterns (cost prediction, quota management)
- Track job failure patterns (retry logic, root cause analysis)
- Automate remediation responses

### Detection Capabilities

| Anomaly Type | Detection Method | Severity |
|--------------|-----------------|----------|
| Slot utilization spike | ML baseline + threshold | High |
| Query timeout increase | Time-series analysis | Medium |
| Storage growth anomaly | Linear regression prediction | Medium |
| Job failure pattern | Cluster analysis | High |
| Cost spike | Daily spend deviation | Critical |
| Quota exhaustion | Predictive modeling | Critical |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Data Pipeline                                  │
│                                                                          │
│  BigQuery Jobs                                                          │
│  ┌────────────────┐    ┌────────────────┐    ┌──────────────────────┐   │
│  │ Query Jobs     │───►│ BigQuery       │───►│ Cloud Monitoring    │   │
│  │ Load Jobs      │    │ Information    │    │ (Metrics)           │   │
│  │ Export Jobs    │    │ Schema         │    │                     │   │
│  └────────────────┘    └────────────────┘    └──────────────────────┘   │
│                                                       │                  │
│              ┌────────────────────────────────────────┤                  │
│              │                     │                   │                 │
│       ┌──────▼──────┐      ┌──────▼──────┐     ┌──────▼──────┐        │
│       │ BigQuery    │      │ Cloud       │     │ Alert       │        │
│       │ ML Models   │      │ Logging     │     │ Policy      │        │
│       └─────────────┘      └──────┬──────┘     └─────────────┘        │
│                                   │                                     │
│                          ┌────────▼────────┐                           │
│                          │ Automated       │                           │
│                          │ Remediation     │                           │
│                          └─────────────────┘                           │
└────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# 1. Enable required APIs
gcloud services enable bigquery.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com

# 2. Set project
export CLOUDSDK_CORE_PROJECT=my-bigquery-project

# 3. Verify BigQuery access
bq ls --project_id=$CLOUDSDK_CORE_PROJECT | head -5
```

## Slot Utilization Monitoring

### Query Slot Usage

```bash
# Get current slot usage
bq query --use_legacy_sql=false \
  "SELECT 
    job_type,
    COUNT(*) as job_count,
    SUM(total_slot_ms) as total_slot_ms,
    AVG(total_slot_ms) as avg_slot_ms
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
  GROUP BY job_type
  ORDER BY total_slot_ms DESC"
```

### Slot Reservation Monitoring

```bash
# Check slot reservations
bq show --format=json my-project:my_reservation | \
  jq '.slots, .assignedSlots'

# Monitor slot assignment over time
bq query --use_legacy_sql=false \
  "SELECT
    TIMESTAMP_TRUNC(creation_time, HOUR) as hour,
    reservation_name,
    SUM(total_slot_ms) / 3600000 as slot_hours
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  GROUP BY 1, 2
  ORDER BY 1 DESC"
```

### Anomaly Detection Query

```bash
# Detect slot usage anomalies (z-score method)
bq query --use_legacy_sql=false \
  "WITH slot_stats AS (
    SELECT
      TIMESTAMP_TRUNC(creation_time, HOUR) as hour,
      SUM(total_slot_ms) / 3600000 as slot_hours
    FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
    WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    GROUP BY 1
  ),
  stats AS (
    SELECT
      AVG(slot_hours) as mean_slots,
      STDDEV(slot_hours) as stddev_slots
    FROM slot_stats
  )
  SELECT
    s.hour,
    s.slot_hours,
    (s.slot_hours - st.mean_slots) / NULLIF(st.stddev_slots, 0) as z_score
  FROM slot_stats s
  CROSS JOIN stats st
  WHERE ABS((s.slot_hours - st.mean_slots) / NULLIF(st.stddev_slots, 0)) > 2
  ORDER BY s.hour DESC"
```

## Query Performance Anomalies

### Slow Query Detection

```bash
# Find queries exceeding time thresholds
bq query --use_legacy_sql=false \
  "SELECT
    job_id,
    user_email,
    query,
    TIMESTAMP_DIFF(end_time, start_time, SECOND) as duration_sec,
    total_slot_ms,
    bytes_processed
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    AND TIMESTAMP_DIFF(end_time, start_time, SECOND) > 300
    AND job_type = 'QUERY'
  ORDER BY duration_sec DESC
  LIMIT 20"
```

### Query Resource Analysis

```bash
# Analyze query resource consumption
bq query --use_legacy_sql=false \
  "SELECT
    job_id,
    query,
    total_bytes_processed,
    total_bytes_billed,
    total_slot_ms,
    TIMESTAMP_DIFF(end_time, start_time, SECOND) as duration_sec,
    CASE
      WHEN total_bytes_billed > 1073741824 THEN 'HIGH'
      WHEN total_bytes_billed > 10737418240 THEN 'CRITICAL'
      ELSE 'NORMAL'
    END as cost_level
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    AND job_type = 'QUERY'
  ORDER BY total_bytes_billed DESC"
```

## Storage Growth Prediction

### Storage Usage Analysis

```bash
# Analyze storage growth by dataset
bq query --use_legacy_sql=false \
  "SELECT
    table_catalog as project_id,
    table_schema as dataset_id,
    SUM(total_logical_bytes) / 1073741824 as logical_gb,
    SUM(total_physical_bytes) / 1073741824 as physical_gb,
    COUNT(DISTINCT table_name) as table_count,
    MAX(last_modified_time) as last_modified
  FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
  GROUP BY 1, 2
  ORDER BY logical_gb DESC"
```

### Growth Prediction Query

```bash
# Predict storage growth (linear regression)
bq query --use_legacy_sql=false \
  "WITH daily_growth AS (
    SELECT
      DATE(creation_time) as day,
      SUM(total_bytes_processed) as daily_bytes
    FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
    WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
      AND job_type = 'LOAD'
    GROUP BY 1
  ),
  stats AS (
    SELECT
      AVG(daily_bytes) as mean_growth,
      STDDEV(daily_bytes) as stddev_growth,
      COUNT(*) as days
    FROM daily_growth
  )
  SELECT
    mean_growth,
    stddev_growth,
    mean_growth * 30 as projected_monthly_growth_gb,
    (mean_growth + 2 * stddev_growth) * 30 as upper_bound_gb
  FROM stats"
```

## Job Failure Pattern Detection

### Failure Analysis

```bash
# Analyze job failure patterns
bq query --use_legacy_sql=false \
  "SELECT
    error_result.reason,
    error_result.message,
    COUNT(*) as failure_count,
    MIN(creation_time) as first_seen,
    MAX(creation_time) as last_seen
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND error_result IS NOT NULL
  GROUP BY 1, 2
  ORDER BY failure_count DESC"
```

### User Failure Patterns

```bash
# Identify users with high failure rates
bq query --use_legacy_sql=false \
  "WITH user_stats AS (
    SELECT
      user_email,
      COUNT(*) as total_jobs,
      COUNTIF(error_result IS NOT NULL) as failed_jobs
    FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
    WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    GROUP BY 1
  )
  SELECT
    user_email,
    total_jobs,
    failed_jobs,
    ROUND(SAFE_DIVIDE(failed_jobs, total_jobs) * 100, 2) as failure_rate
  FROM user_stats
  WHERE failed_jobs > 5
  ORDER BY failure_rate DESC"
```

## Real-Time Alerting

### Cloud Monitoring Alert Policy

```bash
# Create slot utilization alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="BigQuery Slot Utilization High" \
  --condition-display-name="Slot Usage > 80%" \
  --condition-filter='metric.type="bigquery.googleapis.com/job/slot_ms_used" resource.type="global"' \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_GT
```

### Cost Alert Setup

```bash
# Create cost alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="BigQuery Cost Alert" \
  --condition-display-name="Daily Cost > $100" \
  --condition-filter='metric.type="billing.googleapis.com/billing/total_cost" resource.type="global"' \
  --condition-threshold-value=100 \
  --condition-threshold-duration=3600s \
  --condition-threshold-comparison=COMPARISON_GT
```

## Automated Remediation

### Auto-Scale Slots

```bash
#!/bin/bash
# auto-scale-slots.sh

CURRENT_SLOTS=$(bq show --format=json my_reservation | jq -r '.slots')
USED_SLOTS=$(bq query --use_legacy_sql=false --format=json \
  "SELECT SUM(total_slot_ms) / 3600000 as used_slots
   FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
   WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)" | \
  jq -r '.[0].used_slots')

USAGE_RATIO=$(echo "scale=2; $USED_SLOTS / $CURRENT_SLOTS" | bc)

if (( $(echo "$USAGE_RATIO > 0.8" | bc -l) )); then
  NEW_SLOTS=$((CURRENT_SLOTS + 100))
  echo "Scaling up: $CURRENT_SLOTS -> $NEW_SLOTS slots"
  bq update --reservation_id=my_reservation --slots=$NEW_SLOTS
fi
```

### Auto-Cancel Long Queries

```bash
#!/bin/bash
# auto-cancel-long-queries.sh

bq query --use_legacy_sql=false \
  "SELECT job_id, user_email, query
   FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
   WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
     AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), start_time, MINUTE) > 60
     AND job_type = 'QUERY'
     AND state = 'RUNNING'" | \
while read -r job_id user_email query; do
  echo "Cancelling job: $job_id (user: $user_email)"
  bq cancel $job_id
done
```

## Best Practices

1. **Set Slot Reservations**: Use dedicated reservations for predictable workloads
2. **Monitor Information Schema**: Regularly query `INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION`
3. **Use Dry-Run**: Always test queries with `--dry_run` flag
4. **Partition Tables**: Reduce scanned data with partitioning
5. **Cluster Tables**: Improve query performance with clustering
6. **Set Query Limits**: Use `--maximum_bytes_billed` to prevent cost spikes
7. **Archive Old Data**: Use table expiration for historical data

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Slot utilization high | Concurrent heavy queries | Queue queries, use reservations |
| Query timeout | Insufficient slots | Increase slots or optimize query |
| Storage quota exceeded | Uncontrolled growth | Implement lifecycle policies |
| Job failures | Quota exceeded | Check `gcloud bigquery quotas` |

### Debug Queries

```bash
# Check current slots
bq show --format=json my_reservation | jq '.slots'

# List recent failed jobs
bq query --use_legacy_sql=false \
  "SELECT job_id, error_result
   FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
   WHERE error_result IS NOT NULL
   ORDER BY creation_time DESC
   LIMIT 10"
```

## Cost Optimization

### Slot Cost Analysis

```bash
# Analyze slot cost by project
bq query --use_legacy_sql=false \
  "SELECT
    project_id,
    SUM(total_slot_ms) / 3600000 as slot_hours,
    SUM(total_slot_ms) / 3600000 * 0.04 as estimated_cost
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY 1
  ORDER BY estimated_cost DESC"
```

### Storage Cost Optimization

```bash
# Identify storage optimization opportunities
bq query --use_legacy_sql=false \
  "SELECT
    table_catalog as project_id,
    table_schema as dataset_id,
    table_name,
    total_logical_bytes / 1073741824 as logical_gb,
    total_physical_bytes / 1073741824 as physical_gb,
    ROUND((1 - total_physical_bytes / total_logical_bytes) * 100, 2) as compression_pct
  FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
  WHERE total_logical_bytes > 10737418240
  ORDER BY total_logical_bytes DESC"
```

## Self-Healing Playbook

> **Scope**: This playbook converts the detections above into closed-loop remediation. Every action follows **detect → DRY-RUN preview → gate → idempotent apply**. No mutation is applied without a preview and a gate decision. See blast-radius rules in [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) and error taxonomy in [docs/error-taxonomy.md](../../../docs/error-taxonomy.md).

### Safety Invariants (apply to ALL playbooks)

| Invariant | Rule |
|-----------|------|
| **Credential masking** | Never print SA key / token. Verify only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`. See AGENTS.md §0.1. |
| **Dry-run first** | Every mutating command MUST emit a preview (`--dry_run`, `bq show` before `bq update`, IAM `--dry-run` policy diff) before apply. |
| **Idempotency** | Re-run produces no extra effect: use `--replace` on loads, check existence before create, cancel only RUNNING jobs. |
| **Gate** | Auto-apply only for Low/Medium reversible ops. **HALT** on dataset delete / IAM change / any cross-project effect — require explicit human confirmation. |
| **Blast radius** | Before apply, compute affected datasets/tables/users; if >1 project or >10 tables, escalate to HALT. |

### Playbook 1 — Slot Quota Exhausted

**Detection**
```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT SUM(total_slot_ms)/3600000 AS used_slot_hours
   FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
   WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)"
# Compare used_slot_hours*3600000 against reservation .slots; flag if ratio > 0.95
```

**DRY-RUN preview**
```bash
CURRENT_SLOTS=$(bq show --format=json my_reservation | jq -r '.slots')
NEW_SLOTS=$((CURRENT_SLOTS + 100))
echo "PREVIEW: scale my_reservation $CURRENT_SLOTS -> $NEW_SLOTS (dry-run, not applied)"
```

**Gate**: Medium / reversible → auto-apply allowed (reservation scale-up is non-destructive).

**Idempotent apply**
```bash
# Re-check before apply to avoid double-scaling on repeated triggers
if [ "$(bq show --format=json my_reservation | jq -r '.slots')" -lt "$NEW_SLOTS" ]; then
  bq update --reservation_id=my_reservation --slots="$NEW_SLOTS"
fi
```

### Playbook 2 — Long-Running Query Blocking Slots

**Detection**
```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT job_id, user_email,
          TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), start_time, MINUTE) AS age_min
   FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
   WHERE job_type='QUERY' AND state='RUNNING'
     AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), start_time, MINUTE) > 60
   ORDER BY age_min DESC"
```

**DRY-RUN preview**
```bash
echo "PREVIEW: would cancel job_id=$job_id (user=$user_email, age=${age_min}m) — dry-run, not applied"
```

**Gate**: Low / reversible (cancel is non-destructive, job can be re-submitted) → auto-apply allowed. Still notify the job owner via alert channel.

**Idempotent apply**
```bash
# Cancel only if still RUNNING — second trigger finds it DONE and no-ops
STATE=$(bq show -j "$job_id" --format=json | jq -r '.status.state')
[ "$STATE" = "RUNNING" ] && bq cancel "$job_id"
```

### Playbook 3 — Storage Anomaly Growth

**Detection**
```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT table_schema AS dataset_id, table_name,
          total_logical_bytes/1073741824 AS logical_gb,
          last_modified_time
   FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
   WHERE total_logical_bytes > 107374182400   -- >100GB
   ORDER BY total_logical_bytes DESC"
```

**DRY-RUN preview** (set/extend expiration — non-destructive)
```bash
echo "PREVIEW: set expiration 30d on ${dataset_id}.${table_name} (dry-run, not applied)"
```

**Gate**: Medium / reversible → auto-apply allowed **only** for expiration/lifecycle changes. **HALT** if the proposed fix is table deletion or dataset deletion.

**Idempotent apply**
```bash
# Idempotent: setting same expiration twice is a no-op
bq update --expiration=$((30*24*3600*1000)) "${dataset_id}.${table_name}"
```

### Playbook 4 — Export Failure

**Detection**
```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT job_id, error_result.reason, error_result.message
   FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
   WHERE job_type='EXTRACT' AND error_result IS NOT NULL
   ORDER BY creation_time DESC LIMIT 10"
```

**DRY-RUN preview** (re-extract to a verified GCS URI)
```bash
echo "PREVIEW: re-extract ${table_id} -> gs://${bucket}/${prefix}/ (dry-run, not applied)"
gsutil -q stat "gs://${bucket}/" && echo "✅ destination bucket reachable"
```

**Gate**: Low / reversible → auto-apply allowed **only** if destination bucket exists and SA has `roles/storage.objectAdmin`. **HALT** if export would overwrite an existing object without `--destination_format` append strategy.

**Idempotent apply**
```bash
# bq extract is naturally idempotent for full overwrite; guard with existence probe
bq extract --destination_format=CSV --compression=GZIP \
  "${table_id}" "gs://${bucket}/${prefix}/part-*.csv.gz"
```

### Closed-Loop Feedback

Every self-healing action is logged and fed back into the GCL runner for continuous scoring:
- Emit structured log: `[HH:MM:SS] [SELF_HEAL] playbook=<id> action=<op> result=<ok|halt> blast_radius=<n>`
- Push outcome to [gcp-gcl-runner-ops/trace_feedback.py](../../../gcp-gcl-runner-ops/trace_feedback.py) so the Critic can down-score false-positive remediations.
- If a playbook HALTs 3× for the same signature, suppress auto-apply and open a human ticket.

### HALT Matrix (never auto-apply)

| Operation | Decision |
|-----------|----------|
| Delete dataset / table | **HALT** — explicit human confirmation with exact resource ID |
| Modify IAM binding (add/remove member/role) | **HALT** — preview policy diff, require sign-off |
| Cross-project slot reassignment | **HALT** — blast radius >1 project |
| Scale-up reservation / cancel job / set expiration / re-extract | Auto-apply (reversible, Low/Medium) |

## See Also

- [BigQuery Monitoring](../monitoring.md)
- [BigQuery Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Error Taxonomy](../../../docs/error-taxonomy.md)
- [Cross-Skill Blast Radius](../../../docs/cross-skill-blast-radius.md)
- [GCL Runner — trace_feedback](../gcp-gcl-runner-ops/trace_feedback.py)
- [Google Cloud Architecture Framework — Performance](https://cloud.google.com/architecture/framework/performance)
