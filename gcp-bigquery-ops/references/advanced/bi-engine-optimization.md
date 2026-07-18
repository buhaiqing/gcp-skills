# BI Engine Optimization — Google Cloud BigQuery

> Provides data engineers with a guide to enabling BigQuery BI Engine for accelerated query performance, configuring reservations, and monitoring cache effectiveness.

## Table of Contents

1. [Overview](#overview)
2. [Enable BI Engine](#enable-bi-engine)
3. [Reservation Sizing](#reservation-sizing)
4. [Performance Comparison](#performance-comparison)
5. [Monitor Cache Hit Rates](#monitor-cache-hit-rates)
6. [Terraform Configuration](#terraform-configuration)
7. [Troubleshooting](#troubleshooting)
8. [See Also](#see-also)

## Overview

BigQuery BI Engine provides in-memory acceleration for dashboards and reporting workloads. BI Engine caches qualifying tables in memory, reducing slot consumption and query latency for repeated access patterns.

| Component | Description |
|-----------|-------------|
| **BI Engine reservation** | Memory allocated for BI Engine acceleration |
| **Accelerated tables** | Tables cached in BI Engine memory |
| **Cache hit** | Query served from BI Engine memory |
| **Cache miss** | Query falls back to standard BigQuery execution |

### Requirements

- BI Engine API must be enabled
- Reservation size: 50 GB minimum, 10 TB maximum
- Supported table types: Native tables, materialized views
- Supported queries: Standard SQL, read-only

## Enable BI Engine

### gcloud CLI

```bash
# 1. Enable BI Engine API
gcloud services enable bigquery BI Engine.googleapis.com

# 2. Create BI Engine reservation
gcloud bi report-configurations create \
  --project=$CLOUDSDK_CORE_PROJECT \
  --location=us \
  --display-name="bi-engine-reservation" \
  --capacity=100 \
  --size=GB
```

### Reservation Sizes

```bash
# Create 500 GB reservation
gcloud bi report-configurations create \
  --project=$CLOUDSDK_CORE_PROJECT \
  --location=us \
  --display-name="bi-engine-500gb" \
  --capacity=500 \
  --size=GB

# Create 2 TB reservation
gcloud bi report-configurations create \
  --project=$CLOUDSDK_CORE_PROJECT \
  --location=us \
  --display-name="bi-engine-2tb" \
  --capacity=2 \
  --size=TB
```

### Update Reservation

```bash
# Increase capacity to 1 TB
gcloud bi report-configurations update \
  projects/$CLOUDSDK_CORE_PROJECT/locations/us/reportConfigurations/REPORT_CONFIG_ID \
  --capacity=1000 \
  --size=GB
```

### List Reservations

```bash
# List all BI Engine reservations
gcloud bi report-configurations list \
  --project=$CLOUDSDK_CORE_PROJECT \
  --location=us
```

### Delete Reservation

```bash
gcloud bi report-configurations delete \
  projects/$CLOUDSDK_CORE_PROJECT/locations/us/reportConfigurations/REPORT_CONFIG_ID
```

## Reservation Sizing

### Estimate Required Size

Use historical TABLE_STORAGE data to estimate:

```bash
bq query --use_legacy_sql=false \
  "SELECT
    SUM(total_logical_bytes) / 1073741824 AS total_gb,
    COUNT(*) AS table_count,
    COUNTIF(total_logical_bytes <= 10737418240) AS small_tables,
    COUNTIF(total_logical_bytes > 10737418240 AND total_logical_bytes <= 107374182400) AS medium_tables,
    COUNTIF(total_logical_bytes > 107374182400) AS large_tables
  FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
  WHERE table_schema = 'my_dataset'"
```

### Capacity Planning Guide

| Dashboard Type | Recommended BI Engine Size |
|---------------|--------------------------|
| Simple (< 10 queries/sec) | 50-100 GB |
| Medium (10-50 queries/sec) | 100-500 GB |
| Complex (50-200 queries/sec) | 500 GB - 2 TB |
| Enterprise (> 200 queries/sec) | 2-10 TB |

### Tables Suitable for BI Engine

```bash
bq query --use_legacy_sql=false \
  "SELECT
    table_schema,
    table_name,
    total_logical_bytes / 1073741824 AS logical_gb,
    total_rows
  FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
  WHERE table_schema = 'my_dataset'
    AND total_logical_bytes <= 107374182400  -- <= 100 GB per table
  ORDER BY total_logical_bytes DESC"
```

### Tables NOT Suitable

- Tables > 10 TB (exceeds BI Engine maximum)
- Tables with frequent schema changes
- Tables with very low query frequency
- Streaming ingestion tables

## Performance Comparison

### Query with BI Engine (Cached)

```bash
# Run same query twice - second should hit BI Engine cache
bq query --use_legacy_sql=false \
  --use_bi_engine \
  --format=prettyjson \
  "SELECT customer_id, SUM(amount) AS total
   FROM \`my-project.my_dataset.transactions\`
   WHERE date >= '2026-01-01'
   GROUP BY customer_id
   ORDER BY total DESC
   LIMIT 100"
```

### Query without BI Engine

```bash
# Force non-BI Engine execution
bq query --use_legacy_sql=false \
  --no_use_bi_engine \
  --format=prettyjson \
  "SELECT customer_id, SUM(amount) AS total
   FROM \`my-project.my_dataset.transactions\`
   WHERE date >= '2026-01-01'
   GROUP BY customer_id
   ORDER BY total DESC
   LIMIT 100"
```

### Performance Metrics Comparison

| Metric | Without BI Engine | With BI Engine |
|--------|-------------------|----------------|
| Query latency | 2-10 sec | 200-800 ms |
| Slot utilization | 100% | 0% (cache hit) |
| Cost per query | $0.01-0.10 | ~$0 (cache hit) |
| Throughput | 10 qps | 500+ qps |

### Benchmark Script

```bash
#!/bin/bash
# benchmark-bi-engine.sh

PROJECT=$CLOUDSDK_CORE_PROJECT
DATASET="my_dataset"
TABLE="$PROJECT.$DATASET.transactions"

echo "=== BI Engine Benchmark ==="
echo

echo "Warm-up query (no cache):"
time bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM \`$TABLE\`" --format=csv --nouse_bi_engine

echo
echo "BI Engine query (cached):"
time bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM \`$TABLE\`" --format=csv --use_bi_engine

echo
echo "Non-BI Engine query:"
time bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM \`$TABLE\`" --format=csv --no_use_bi_engine
```

## Monitor Cache Hit Rates

### BI Engine Metrics via Cloud Monitoring

```bash
# List available BI Engine metrics
gcloud monitoring metrics list \
  --filter="metric.type:bigquery.googleapis.com/bi" \
  --project=$CLOUDSDK_CORE_PROJECT
```

### Query BI Engine Cache Hit Rate

```bash
bq query --use_legacy_sql=false \
  "SELECT
    COUNT(*) AS total_queries,
    COUNTIF(cache_hit = TRUE) AS bi_engine_hits,
    ROUND(COUNTIF(cache_hit = TRUE) / COUNT(*) * 100, 2) AS bi_engine_hit_rate
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)"
```

### Per-Table Cache Effectiveness

```bash
bq query --use_legacy_sql=false \
  "WITH table_references AS (
    SELECT
      job_id,
      reference_tables.table_name,
      reference_tables.project_id,
      reference_tables.dataset_id
    FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_PROJECT`,
    UNNEST(referenced_tables) AS reference_tables
    WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
      AND cache_hit = TRUE
  )
  SELECT
    dataset_id,
    table_name,
    COUNT(*) AS cache_hits
  FROM table_references
  GROUP BY 1, 2
  ORDER BY cache_hits DESC
  LIMIT 20"
```

### Cache Hit by Hour

```bash
bq query --use_legacy_sql=false \
  "SELECT
    TIMESTAMP_TRUNC(creation_time, HOUR) AS hour,
    COUNT(*) AS total_queries,
    COUNTIF(cache_hit = TRUE) AS bi_engine_hits,
    ROUND(COUNTIF(cache_hit = TRUE) / COUNT(*) * 100, 2) AS hit_rate_pct
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  GROUP BY 1
  ORDER BY 1 DESC"
```

### Alert on Low Cache Hit Rate

```bash
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/CHANNEL_ID" \
  --display-name="BI Engine Cache Hit Rate Low" \
  --condition-display-name="Cache Hit Rate < 70%" \
  --condition-filter='metric.type="bigquery.googleapis.com/bi_engine/cache_hit_rate"' \
  --condition-threshold-value=0.7 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_LT
```

## Terraform Configuration

### BI Engine Reservation

```hcl
resource "google_bi_report_configuration" "bi_engine" {
  project = var.project_id
  location = "us"
  display_name = "bi-engine-reservation"
  capacity  = 500  # GB
  size      = "GB"

  labels = {
    environment = var.environment
  }
}
```

### Variables

```hcl
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "environment" {
  description = "Environment label"
  type        = string
  default     = "prod"
}
```

### Outputs

```hcl
output "bi_engine_reservation_id" {
  description = "BI Engine reservation ID"
  value       = google_bi_report_configuration.bi_engine.name
}

output "bi_engine_capacity" {
  description = "BI Engine reservation capacity"
  value       = google_bi_report_configuration.bi_engine.capacity
}
```

### Import Existing Reservation

```bash
terraform import google_bi_report_configuration.bi_engine \
  projects/my-project/locations/us/reportConfigurations/REPORT_CONFIG_ID
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Slow queries despite BI Engine | Table > 10 TB | Exclude from BI Engine |
| 0% cache hit rate | BI Engine not enabled | Verify reservation status |
| Reservation size exceeded | Too many large tables | Increase capacity or reduce tables |
| High slot usage | BI Engine cache miss | Add frequently queried tables |
| BI Engine not available in region | Region not supported | Use supported region (us, eu, asia) |

### Verify BI Engine Status

```bash
# Check if BI Engine is enabled
gcloud bi report-configurations list \
  --project=$CLOUDSDK_CORE_PROJECT \
  --location=us

# Check BI Engine capacity
bq query --use_legacy_sql=false \
  "SELECT * FROM \`region-us\`.INFORMATION_SCHEMA.BI_ENGINE_CAPACITY"
```

### Check Table BI Engine Eligibility

```bash
bq query --use_legacy_sql=false \
  "SELECT
    table_name,
    total_logical_bytes / 1073741824 AS size_gb,
    CASE
      WHEN total_logical_bytes <= 10995116277760 THEN 'ELIGIBLE'
      ELSE 'TOO_LARGE'
    END AS bi_engine_eligibility
  FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
  WHERE table_schema = 'my_dataset'"
```

### Monitor BI Engine Memory Usage

```bash
# Check BI Engine memory utilization
gcloud monitoring metrics list \
  --filter="metric.type:bigquery.googleapis.com/bi_engine/memory_usage" \
  --project=$CLOUDSDK_CORE_PROJECT

# Get reservation details
gcloud bi report-configurations describe \
  projects/$CLOUDSDK_CORE_PROJECT/locations/us/reportConfigurations/REPORT_CONFIG_ID
```

## See Also

- [INFORMATION_SCHEMA Reference](information-schema.md)
- [AIOps Anomaly Detection](aiops-bigquery-anomaly.md)
- [FinOps Cost Optimization](finops-bigquery-cost.md)
- [BigQuery Monitoring](../monitoring.md)
- [BigQuery BI Engine Documentation](https://cloud.google.com/bigquery/docs/bi-engine-intro)
