# Committed Use Discount Analysis — Google Cloud Billing

> Provides FinOps practitioners with a guide to analyzing, purchasing, and managing Committed Use Discounts (CUDs) across Google Cloud — covered resources, savings calculations, commitment planning, and portfolio optimization.

## Table of Contents

1. [Overview](#overview)
2. [CUD Types](#cud-types)
3. [Commitment Analysis](#commitment-analysis)
4. [Coverage Calculation](#coverage-calculation)
5. [Savings Estimation](#savings-estimation)
6. [Commitment Planning](#commitment-planning)
7. [Portfolio Optimization](#portfolio-optimization)
8. [Monitoring & Validation](#monitoring--validation)
9. [Troubleshooting](#troubleshooting)
10. [See Also](#see-also)

## Overview

Committed Use Discounts (CUDs) allow organizations to exchange flexibility (no upfront, cancel anytime) for discounted rates on Google Cloud resources. CUDs can reduce costs by 30-70% compared to on-demand pricing.

### CUD Coverage by Product

| Product | Resource Type | Commitment Term | Typical Savings |
|---------|--------------|----------------|-----------------|
| Compute Engine | vCPU, GB memory | 1 or 3 years | 30-57% |
| Cloud SQL | Instance resources | 1 or 3 years | 30-57% |
| GKE | Node pool resources | 1 or 3 years | 30-57% |
| BigQuery | Flat-rate slots | 1 or 3 years | 17-70% |
| Dataproc | Instance resources | 1 or 3 years | 30-57% |
| Memorystore | Redis/Memcached | 1 or 3 years | 30-57% |

## CUD Types

### Resource-based CUDs (R-CUDs)

Apply to specific resource families (N2, N2D, E2, etc.) within a project or folder.

```bash
# List available CUD resources
gcloud billing projects describe $PROJECT_ID --format="yaml"

# View current commitments
gcloud compute commitments list --project=$PROJECT_ID --format="json"
```

### Spend-based CUDs (S-CUDs)

Applied at the billing account level as a monthly commitment against all eligible resources.

```bash
# View billing account CUD coverage
gcloud beta billing accounts describe $ACCOUNT_ID --format="yaml"
```

### Committed Use Reservations (for BigQuery)

```bash
# List flat-rate slot commitments
gcloud beta bigquery reservations assignments list \
  --project=$PROJECT_ID --format="json"
```

## Commitment Analysis

### Step 1: Gather Current Usage

```bash
# Export billing export to BigQuery
bq query --nouse_legacy_sql "
SELECT
  service.description AS service,
  sku.description AS sku,
  ROUND(SUM(cost), 2) AS total_cost,
  ROUND(SUM(usage.amount), 2) AS total_usage
FROM `billing_export_table`
WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY 1, 2
ORDER BY total_cost DESC
"
```

### Step 2: Calculate Utilization Rate

```bash
# Compute Engine utilization (CPU)
bq query --nouse_legacy_sql "
SELECT
  project.id,
  AVG(metric.value) AS avg_utilization
FROM `metrics_dataset.compute_instance_metrics`,
  UNNEST(metric) AS metric
WHERE metric.name = 'cpu.utilization'
  AND usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY project.id
"
```

### Step 3: Identify Commitment-eligible Resources

```bash
# List resources eligible for CUDs
bq query --nouse_legacy_sql "
SELECT
  resource.project_id,
  resource.location,
  resource.resource_type,
  SUM(resource.usage_amount) AS monthly_usage,
  SUM(resource.cost) AS monthly_cost
FROM `billing_export_table` resource
WHERE resource.service.description = 'Compute Engine'
  AND resource.sku.description LIKE '%Committed Use%'
GROUP BY 1, 2, 3
"
```

## Coverage Calculation

### CUD Coverage Formula

```
Coverage Rate = Committed Resources / Total Eligible Resources × 100
```

### Calculate Current Coverage

```python
# cud_coverage.py
import os
from google.cloud import bigquery

client = bigquery.Client()
project = os.environ["CLOUDSDK_CORE_PROJECT"]

query = """
SELECT
  service,
  SUM(on_demand_cost) AS on_demand_cost,
  SUM(committed_cost) AS committed_cost,
  ROUND(SUM(committed_cost) / SUM(on_demand_cost + committed_cost) * 100, 2) AS coverage_pct
FROM (
  SELECT
    service.description AS service,
    CASE WHEN sku.description LIKE '%Committed%' THEN cost ELSE 0 END AS committed_cost,
    CASE WHEN sku.description NOT LIKE '%Committed%' THEN cost ELSE 0 END AS on_demand_cost
  FROM `billing_export_table`
  WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
)
GROUP BY service
ORDER BY coverage_pct ASC
"""

results = client.query(query).result()
for row in results:
    print(f"{row.service}: {row.coverage_pct}% covered")
```

## Savings Estimation

### Break-even Analysis

```bash
# Calculate break-even point for CUD purchase
bq query --nouse_legacy_sql "
SELECT
  sku.description,
  ROUND(SUM(cost), 2) AS monthly_on_demand_cost,
  ROUND(SUM(cost) * 0.57, 2) AS estimated_monthly_cud_cost,
  ROUND(SUM(cost) - SUM(cost) * 0.57, 2) AS monthly_savings,
  ROUND((SUM(cost) * 0.43) / (SUM(cost) * 0.43), 0) AS break_even_months
FROM `billing_export_table`
WHERE sku.description LIKE '%On-demand%'
  AND service.description = 'Compute Engine'
GROUP BY sku.description
"
```

### 3-Year vs 1-Year Comparison

| Commitment Term | Typical Discount | Break-even | Best For |
|-----------------|------------------|------------|----------|
| 1-year | 30-43% | 4-6 months | New workloads, uncertain growth |
| 3-year | 50-57% | 8-12 months | Stable, predictable workloads |

## Commitment Planning

### Forecasting Tool

```python
# forecast_cud_needs.py
import os
import pandas as pd
from google.cloud import bigquery

client = bigquery.Client()

def forecast_commitment(project_id, service, months_ahead=12):
    """Forecast resource needs for CUD planning."""
    query = f"""
    SELECT
      DATE_TRUNC(usage_start_time, MONTH) AS month,
      SUM(cost) AS monthly_cost,
      SUM(usage.amount) AS monthly_usage
    FROM `billing_export_table`
    WHERE service.description = '{service}'
      AND usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 MONTH)
    GROUP BY 1
    ORDER BY 1
    """
    df = client.query(query).to_dataframe()

    # Simple linear regression for forecasting
    df['month_num'] = range(len(df))
    slope = (df['monthly_cost'].iloc[-1] - df['monthly_cost'].iloc[0]) / len(df)
    avg_monthly = df['monthly_cost'].mean()

    forecast_months = min(months_ahead, 36)
    projected_monthly = avg_monthly + (slope * len(df))

    return {
        'current_monthly': avg_monthly,
        'projected_monthly': projected_monthly,
        'recommended_commitment': round(projected_monthly * 0.8, 2),  # 80% of projected
        'term_recommendation': '3-year' if months_ahead >= 24 else '1-year'
    }
```

## Portfolio Optimization

### Identify Under-utilized Commitments

```bash
bq query --nouse_legacy_sql "
SELECT
  r.project_id,
  r.location,
  r.resource_name,
  r.committed_vcpus,
  r.used_vcpus,
  ROUND((r.used_vcpus / r.committed_vcpus) * 100, 2) AS utilization_pct,
  CASE
    WHEN (r.used_vcpus / r.committed_vcpus) < 0.5 THEN 'Critical - Review'
    WHEN (r.used_vcpus / r.committed_vcpus) < 0.7 THEN 'Warning - Monitor'
    ELSE 'Healthy'
  END AS status
FROM (
  SELECT
    project_id,
    location,
    resource_name,
    committed_vcpus,
    SUM(used_vcpus) AS used_vcpus
  FROM `commitment_utilization_table`
  GROUP BY 1, 2, 3, 4
) r
ORDER BY utilization_pct ASC
"
```

### Reallocate Unused Commitments

```bash
# Move commitments between projects (same organization)
gcloud compute commitments move $COMMITMENT_ID \
  --source-project=$SOURCE_PROJECT \
  --destination-project=$DEST_PROJECT
```

## Monitoring & Validation

### Monthly CUD Report

```bash
# Generate monthly CUD utilization report
bq query --nouse_legacy_sql "
SELECT
  DATE_TRUNC(usage_start_time, MONTH) AS month,
  service.description AS service,
  SUM(CASE WHEN sku.description LIKE '%Committed%' THEN cost ELSE 0 END) AS cud_cost,
  SUM(CASE WHEN sku.description LIKE '%On-demand%' THEN cost ELSE 0 END) AS od_cost,
  ROUND(
    SUM(CASE WHEN sku.description LIKE '%Committed%' THEN cost ELSE 0 END) /
    (SUM(cost) + 0.001) * 100, 2
  ) AS savings_rate
FROM `billing_export_table`
GROUP BY 1, 2
ORDER BY 1 DESC, savings_rate DESC
"
```

### Alert on Low Utilization

```bash
# Set up monitoring alert for CUD utilization < 60%
gcloud monitoring policies create \
  --notification-channels=$CHANNEL_ID \
  --display-name="Low CUD Utilization Alert" \
  --condition-display-name="CUD utilization below 60%" \
  --condition-filter='metric.type="compute.googleapis.com/commitment/utilization" AND metric.value < 0.6'
```

## Troubleshooting

| Issue | Diagnosis | Resolution |
|-------|-----------|------------|
| CUD not applied | Check resource family matches commitment | Use matching machine type family |
| Low utilization | Monitor shows <50% usage | Resize or reallocate commitments |
| No savings visible | Review billing report by SKU type | Ensure resources are CUD-eligible |
| Commitment too large | Usage decreased after purchase | Use shiftable analysis tools |
| Cannot modify commitment | Active commitment has min term | Wait for renewal window |

## See Also

- [FinOps Cost Analysis](finops-cost-analysis.md)
- [AIOps Billing Anomaly Detection](aiops-billing-anomaly.md)
- [Google Cloud CUD Documentation](https://cloud.google.com/compute/docs/instances/signing-up-committed-use-discounts)
