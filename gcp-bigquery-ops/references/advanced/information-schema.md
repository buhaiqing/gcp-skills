# INFORMATION_SCHEMA Reference — Google Cloud BigQuery

> Provides data engineers with a guide to querying BigQuery's INFORMATION_SCHEMA tables for job analytics, storage introspection, table metadata, and object-level auditing.

## Table of Contents

1. [Overview](#overview)
2. [JOBS_BY_PROJECT](#jobs_by_project)
3. [JOBS_BY_USER](#jobs_by_user)
4. [TABLE_STORAGE](#table_storage)
5. [TABLE_METADATA](#table_metadata)
6. [OBJECT_TABLE](#object_table)
7. [OBJECT_METADATA](#object_metadata)
8. [Python SDK Examples](#python-sdk-examples)
9. [Common Patterns](#common-patterns)
10. [See Also](#see-also)

## Overview

INFORMATION_SCHEMA provides read-only visibility into BigQuery metadata across projects, datasets, and tables. All views use standard SQL and support filtering by time range.

| View | Scope | Use Case |
|------|-------|----------|
| `JOBS_BY_PROJECT` | Project-level | Slot usage, cost analysis, job auditing |
| `JOBS_BY_USER` | User-level | Per-user query analysis, chargeback |
| `TABLE_STORAGE` | Table-level | Storage size, compression, physical vs logical |
| `TABLE_METADATA` | Table-level | Schema, partitioning, clustering, expiration |
| `OBJECT_TABLE` | Dataset-level | Object table listing |
| `OBJECT_METADATA` | Dataset-level | Object table metadata |

> **Region prefix**: Views are prefixed with region (e.g., `region-us`, `region-eu-west1`). Replace with your dataset region.

## JOBS_BY_PROJECT

### Schema

```sql
job_id, creation_time, start_time, end_time, user_email, project_id,
job_type, priority, state, reservation_id, timeline, total_slot_ms,
total_bytes_processed, total_bytes_billed, total_roundup_bytes_billed,
cache_hit, referenced_tables, referenced_routines, destination_table,
error_result
```

### Slot Usage by Project

```bash
bq query --use_legacy_sql=false \
  "SELECT
    project_id,
    reservation_id,
    SUM(total_slot_ms) / 3600000 AS slot_hours,
    SUM(total_bytes_processed) / 1073741824 AS tb_processed,
    COUNT(*) AS job_count
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  GROUP BY 1, 2
  ORDER BY slot_hours DESC"
```

### Cost Analysis by Day

```bash
bq query --use_legacy_sql=false \
  "SELECT
    DATE(creation_time) AS job_date,
    SUM(total_bytes_billed) / 1099511627776 AS tb_billed,
    SUM(total_bytes_billed) / 1099511627776 * 5 AS estimated_cost_usd
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY 1
  ORDER BY 1 DESC"
```

### Cache Hit Rate

```bash
bq query --use_legacy_sql=false \
  "SELECT
    COUNT(*) AS total_jobs,
    COUNTIF(cache_hit = TRUE) AS cached_jobs,
    ROUND(COUNTIF(cache_hit = TRUE) / COUNT(*) * 100, 2) AS cache_hit_pct
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)"
```

## JOBS_BY_USER

### Schema

Same as JOBS_BY_PROJECT plus `user_email`.

### User Query Patterns

```bash
bq query --use_legacy_sql=false \
  "SELECT
    user_email,
    COUNT(*) AS total_jobs,
    SUM(total_slot_ms) / 3600000 AS slot_hours,
    SUM(total_bytes_processed) / 1073741824 AS tb_processed,
    ROUND(AVG(TIMESTAMP_DIFF(end_time, start_time, SECOND)), 2) AS avg_duration_sec
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_USER
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  GROUP BY 1
  ORDER BY slot_hours DESC
  LIMIT 20"
```

### Expensive Queries per User

```bash
bq query --use_legacy_sql=false \
  "SELECT
    user_email,
    job_id,
    query,
    total_bytes_processed / 1073741824 AS tb_processed,
    total_slot_ms / 3600000 AS slot_hours,
    TIMESTAMP_DIFF(end_time, start_time, SECOND) AS duration_sec
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_USER
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    AND total_bytes_processed > 107374182400  -- 100GB
  ORDER BY total_bytes_processed DESC
  LIMIT 20"
```

## TABLE_STORAGE

### Schema

```sql
table_catalog, table_schema, table_name, table_type, total_logical_bytes,
total_physical_bytes, total_long_term_storage_bytes, active_logical_bytes,
total_rows, last_modified_time, last_check_time, storage_tier
```

### Storage by Dataset

```bash
bq query --use_legacy_sql=false \
  "SELECT
    table_catalog AS project_id,
    table_schema AS dataset_id,
    SUM(total_logical_bytes) / 1073741824 AS logical_gb,
    SUM(total_physical_bytes) / 1073741824 AS physical_gb,
    SUM(total_long_term_storage_bytes) / 1073741824 AS lts_gb,
    COUNT(*) AS table_count
  FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
  GROUP BY 1, 2
  ORDER BY logical_gb DESC"
```

### Compression Analysis

```bash
bq query --use_legacy_sql=false \
  "SELECT
    table_catalog,
    table_schema,
    table_name,
    total_logical_bytes / 1073741824 AS logical_gb,
    total_physical_bytes / 1073741824 AS physical_gb,
    ROUND((1 - SAFE_DIVIDE(total_physical_bytes, total_logical_bytes)) * 100, 2) AS compression_pct
  FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
  WHERE total_logical_bytes > 10737418240  -- 10GB+
  ORDER BY compression_pct ASC
  LIMIT 20"
```

### Long-Term Storage Candidates

```bash
bq query --use_legacy_sql=false \
  "SELECT
    table_catalog,
    table_schema,
    table_name,
    total_long_term_storage_bytes / 1073741824 AS lts_gb,
    total_logical_bytes / 1073741824 AS logical_gb,
    last_modified_time
  FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
  WHERE total_long_term_storage_bytes > 0
  ORDER BY lts_gb DESC"
```

## TABLE_METADATA

### Schema

```sql
table_catalog, table_schema, table_name, table_type, is_insertable,
is_ddl, ddl, clustering_columns, time_partitioning, range_partitioning,
expiration_time, default_collation, partition_count, total_partition_rows,
total_cols, total_hidden_cols, total_temp_cols, row_length_bytes,
last_modified_time, creation_time, labels
```

### Partition Info

```bash
bq query --use_legacy_sql=false \
  "SELECT
    table_catalog,
    table_schema,
    table_name,
    table_type,
    time_partitioning,
    range_partitioning,
    partition_count,
    total_partition_rows,
    expiration_time
  FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_METADATA
  WHERE table_schema = 'my_dataset'
  ORDER BY table_name"
```

### Expiration Policy Audit

```bash
bq query --use_legacy_sql=false \
  "SELECT
    table_catalog,
    table_schema,
    table_name,
    expiration_time,
    last_modified_time
  FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_METADATA
  WHERE expiration_time IS NOT NULL
    AND table_schema = 'my_dataset'"
```

## OBJECT_TABLE

### Schema

```sql
table_catalog, table_schema, table_name, table_type, object_type,
object_uri, last_modified_time
```

### List Object Tables

```bash
bq query --use_legacy_sql=false \
  "SELECT
    table_catalog,
    table_schema,
    table_name,
    object_type,
    object_uri,
    last_modified_time
  FROM \`region-us\`.INFORMATION_SCHEMA.OBJECT_TABLE
  WHERE table_schema = 'my_dataset'"
```

## OBJECT_METADATA

### Schema

```sql
table_catalog, table_schema, table_name, object_type, object_uri,
last_modified_time, size_bytes, md5_hash, media_link, content_type
```

### Object Details

```bash
bq query --use_legacy_sql=false \
  "SELECT
    table_name,
    object_type,
    object_uri,
    size_bytes / 1073741824 AS size_gb,
    md5_hash,
    last_modified_time
  FROM \`region-us\`.INFORMATION_SCHEMA.OBJECT_METADATA
  WHERE table_schema = 'my_dataset'"
```

## Python SDK Examples

### Query JOBS_BY_PROJECT

```python
from google.cloud import bigquery

client = bigquery.Client()

query = """
SELECT
  project_id,
  SUM(total_slot_ms) / 3600000 AS slot_hours,
  COUNT(*) AS job_count
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY 1
ORDER BY slot_hours DESC
"""
results = client.query(query).result()
for row in results:
    print(f"{row.project_id}: {row.slot_hours:.2f} slot-hours, {row.job_count} jobs")
```

### Query TABLE_STORAGE

```python
from google.cloud import bigquery

client = bigquery.Client()

query = """
SELECT
  table_schema,
  table_name,
  total_logical_bytes / 1073741824 AS logical_gb,
  total_physical_bytes / 1073741824 AS physical_gb,
  total_rows
FROM `region-us`.INFORMATION_SCHEMA.TABLE_STORAGE
WHERE table_schema = 'my_dataset'
ORDER BY logical_gb DESC
"""
results = client.query(query).result()
for row in results:
    print(f"{row.table_schema}.{row.table_name}: {row.logical_gb:.2f} GB, {row.total_rows} rows")
```

## Common Patterns

### Combined Job and Storage Analysis

```bash
bq query --use_legacy_sql=false \
  "WITH jobs AS (
    SELECT
      project_id,
      DATE(creation_time) AS job_date,
      SUM(total_slot_ms) / 3600000 AS slot_hours
    FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
    WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    GROUP BY 1, 2
  ),
  storage AS (
    SELECT
      table_catalog AS project_id,
      SUM(total_logical_bytes) / 1073741824 AS storage_gb
    FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
    GROUP BY 1
  )
  SELECT
    j.project_id,
    SUM(j.slot_hours) AS total_slot_hours,
    s.storage_gb
  FROM jobs j
  LEFT JOIN storage s ON j.project_id = s.project_id
  GROUP BY 1, s.storage_gb
  ORDER BY total_slot_hours DESC"
```

### User Chargeback Report

```bash
bq query --use_legacy_sql=false \
  "SELECT
    user_email,
    COUNT(*) AS total_jobs,
    SUM(total_bytes_billed) / 1099511627776 AS tb_billed,
    SUM(total_bytes_billed) / 1099511627776 * 5 AS cost_usd,
    SUM(total_slot_ms) / 3600000 AS slot_hours
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_USER
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY 1
  ORDER BY cost_usd DESC"
```

## See Also

- [AIOps Anomaly Detection](aiops-bigquery-anomaly.md)
- [FinOps Cost Optimization](finops-bigquery-cost.md)
- [BigQuery Monitoring](../monitoring.md)
- [BigQuery Core Concepts](../core-concepts.md)
- [INFORMATION_SCHEMA Reference](https://cloud.google.com/bigquery/docs/information-schema-intro)
