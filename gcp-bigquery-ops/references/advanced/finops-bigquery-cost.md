# FinOps Cost Optimization — Google Cloud BigQuery

> Provides data engineers with a complete guide to optimizing costs associated with Google Cloud BigQuery — slot pricing, storage tiers, query optimization, and cost governance.

## Table of Contents

1. [Overview](#overview)
2. [BigQuery Cost Model](#bigquery-cost-model)
3. [Slot Pricing Optimization](#slot-pricing-optimization)
4. [Storage Cost Optimization](#storage-cost-optimization)
5. [Query Cost Optimization](#query-cost-optimization)
6. [Cost Monitoring](#cost-monitoring)
7. [Automated Cost Control](#automated-cost-control)
8. [Troubleshooting High Costs](#troubleshooting-high-costs)
9. [See Also](#see-also)

## Overview

BigQuery costs primarily come from:

- **Query Processing** — on-demand ($5/TB) or flat-rate (slot-based)
- **Storage** — active ($0.02/GB/month) and long-term ($0.01/GB/month)
- **Data Transfer** — ingestion and export charges
- **Streaming Inserts** — per-GB cost for real-time data

Optimizing these costs can reduce BigQuery spend by 40-70% for most workloads.

### Cost Drivers

| Resource | Pricing Model | Typical Monthly Cost | Optimization Potential |
|----------|---------------|---------------------|------------------------|
| On-demand queries | $5/TB processed | $100-1000+ | 50-70% |
| Flat-rate slots | $0.04/slot/hour | $300-3000+ | 30-50% |
| Active storage | $0.02/GB/month | $50-500 | 40-60% |
| Long-term storage | $0.01/GB/month | $25-250 | 20-30% |
| Streaming inserts | $0.05/GB | $50-500 | 30-50% |

## BigQuery Cost Model

### Pricing Breakdown

| Resource | Cost Component | Rate |
|----------|---------------|------|
| On-demand queries | Per TB processed | $5.00/TB |
| Flat-rate slots | Per slot/hour | $0.04/slot |
| Active storage | Per GB/month | $0.02/GB |
| Long-term storage | Per GB/month | $0.01/GB |
| Streaming inserts | Per GB | $0.05/GB |
| Data transfer | Per GB | $0.05-0.12/GB |
| Exports | Per GB | $0.05/GB |

### Cost Calculator

```bash
# Estimate query cost (dry run)
bq query --use_legacy_sql=false --dry_run \
  "SELECT * FROM \`bigquery-public-data.samples.gsod\`" 2>&1 | \
  grep "This query will process"

# Calculate storage cost
echo "Storage cost: $(echo "scale=2; 100 * 0.02" | bc) GB/month for 100GB"
```

## Slot Pricing Optimization

### On-Demand vs Flat-Rate Analysis

```bash
# Analyze slot usage for pricing decision
bq query --use_legacy_sql=false \
  "WITH daily_usage AS (
    SELECT
      DATE(creation_time) as day,
      SUM(total_slot_ms) / 3600000 as slot_hours
    FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
    WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    GROUP BY 1
  )
  SELECT
    AVG(slot_hours) as avg_daily_slots,
    MAX(slot_hours) as peak_daily_slots,
    AVG(slot_hours) * 30 as monthly_slots,
    AVG(slot_hours) * 30 * 0.04 as flat_rate_cost,
    AVG(slot_hours) * 30 * 0.04 * 0.7 as committed_cost_70pct
  FROM daily_usage"
```

### Reservation Optimization

```bash
# Check reservation utilization
bq show --format=json my_reservation | \
  jq '{slots: .slots, assigned: .assignedSlots, utilization: (.assignedSlots / .slots * 100)}'

# Right-size reservation
bq update --reservation_id=my_reservation --slots=100
```

## Storage Cost Optimization

### Storage Tier Analysis

```bash
# Analyze storage tiers
bq query --use_legacy_sql=false \
  "SELECT
    table_catalog as project_id,
    table_schema as dataset_id,
    COUNT(*) as table_count,
    SUM(CASE WHEN age_in_days <= 90 THEN total_logical_bytes ELSE 0 END) / 1073741824 as active_gb,
    SUM(CASE WHEN age_in_days > 90 THEN total_logical_bytes ELSE 0 END) / 1073741824 as long_term_gb,
    SUM(total_logical_bytes) / 1073741824 as total_gb
  FROM (
    SELECT *,
      DATE_DIFF(CURRENT_DATE(), DATE(last_modified_time), DAY) as age_in_days
    FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
  )
  GROUP BY 1, 2
  ORDER BY total_gb DESC"
```

### Lifecycle Policy Setup

```bash
# Set table expiration for 90 days
bq update --table \
  --expiration_days=90 \
  my_project:my_dataset.my_table

# Set dataset default expiration
bq update --default_table_expiration_days=90 \
  my_project:my_dataset
```

## Query Cost Optimization

### Partition Pruning

```bash
# Query with partition filter (cost reduction)
bq query --use_legacy_sql=false \
  "SELECT *
   FROM \`my_project.my_dataset.my_table\`
   WHERE _PARTITIONTIME >= TIMESTAMP('2024-01-01')
     AND _PARTITIONTIME < TIMESTAMP('2024-02-01')"
```

### Query Cost Analysis

```bash
# Analyze query cost by user
bq query --use_legacy_sql=false \
  "SELECT
    user_email,
    COUNT(*) as query_count,
    SUM(total_bytes_processed) / 1073741824 as total_gb_processed,
    SUM(total_bytes_processed) / 1073741824 * 5 as estimated_cost
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    AND job_type = 'QUERY'
  GROUP BY 1
  ORDER BY estimated_cost DESC"
```

### Cost Limit Enforcement

```bash
# Set maximum bytes billed
bq query --use_legacy_sql=false \
  --maximum_bytes_billed=10737418240 \
  "SELECT * FROM \`my_project.my_dataset.my_table\`"
```

## Cost Monitoring

### Budget Alerts

```bash
# Create BigQuery budget alert
gcloud billing budgets create \
  --billing-account=$BILLING_ACCOUNT_ID \
  --display-name="BigQuery Monthly Budget" \
  --budget-amount=1000 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100 \
  --all-updates-rule-pubsub-topic=projects/$CLOUDSDK_CORE_PROJECT/topics/budget-alerts
```

### Cost Dashboard

```bash
# Query cost trends
bq query --use_legacy_sql=false \
  "SELECT
    TIMESTAMP_TRUNC(creation_time, DAY) as day,
    SUM(total_bytes_processed) / 1073741824 as gb_processed,
    SUM(total_bytes_processed) / 1073741824 * 5 as daily_cost
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    AND job_type = 'QUERY'
  GROUP BY 1
  ORDER BY 1"
```

## Automated Cost Control

### Auto-Archive Old Data

```bash
#!/bin/bash
# archive-old-data.sh

bq query --use_legacy_sql=false \
  "SELECT table_catalog, table_schema, table_name
   FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
   WHERE age_in_days > 90
     AND type = 'BASE TABLE'" | \
while read -r project dataset table; do
  echo "Archiving: $project.$dataset.$table"
  bq cp --destination_table_rotation_days=30 \
    $project.$dataset.$table \
    $project.$dataset.${table}_archive
done
```

### Auto-Delete Expired Data

```bash
#!/bin/bash
# auto-delete-expired.sh

bq query --use_legacy_sql=false \
  "SELECT table_catalog, table_schema, table_name
   FROM \`region-us\`.INFORMATION_SCHEMA.TABLE_STORAGE
   WHERE expiration_time < TIMESTAMP_MICROS(UNIX_MICROS(CURRENT_TIMESTAMP()))" | \
while read -r project dataset table; do
  echo "Deleting expired: $project.$dataset.$table"
  bq rm -f -t $project.$dataset.$table
done
```

## Troubleshooting High Costs

### Common Cost Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High query cost | Full table scans | Add partition filters |
| Unexpected streaming cost | High-volume inserts | Use batch loading |
| Storage cost spike | Uncontrolled growth | Implement lifecycle policies |
| Slot cost increase | Over-provisioning | Right-size reservations |

### Cost Investigation

```bash
# Find most expensive queries
bq query --use_legacy_sql=false \
  "SELECT
    job_id,
    user_email,
    query,
    total_bytes_processed / 1073741824 as gb_processed,
    total_bytes_processed / 1073741824 * 5 as cost
  FROM \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_ORGANIZATION
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND job_type = 'QUERY'
  ORDER BY total_bytes_processed DESC
  LIMIT 10"
```

## See Also

- [BigQuery Monitoring](../monitoring.md)
- [BigQuery Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud FinOps Guide](https://cloud.google.com/architecture/cost-optimization)
