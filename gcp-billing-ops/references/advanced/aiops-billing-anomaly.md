# AIOps Anomaly Detection — Google Cloud Billing

> Provides finance and operations teams with a guide to implementing AIOps-driven anomaly detection for Cloud Billing — spend anomaly detection, budget threshold prediction, cost spike alerting, and automated remediation.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Spend Anomaly Detection](#spend-anomaly-detection)
5. [Budget Threshold Prediction](#budget-threshold-prediction)
6. [Cost Spike Detection](#cost-spike-detection)
7. [Real-Time Alerting](#real-time-alerting)
8. [Automated Remediation](#automated-remediation)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [See Also](#see-also)

## Overview

AIOps for Cloud Billing detects unusual spending patterns and predicts budget overruns. With Cloud Billing APIs and Cloud Monitoring, you can:

- Detect unexpected spend anomalies (sudden cost spikes)
- Predict budget threshold breaches (forecasting)
- Monitor cost allocation across projects
- Track unusual usage patterns by service
- Automate cost control responses

### Detection Capabilities

| Anomaly Type | Detection Method | Severity |
|--------------|-----------------|----------|
| Daily spend spike | Z-score analysis | High |
| Service cost anomaly | Per-service baseline | Medium |
| Budget overrun prediction | Linear regression | Critical |
| Unused resource detection | Activity monitoring | Medium |
| Currency fluctuation | Exchange rate tracking | Low |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Cost Data Pipeline                             │
│                                                                          │
│  Cloud Billing Export                                                   │
│  ┌────────────────┐    ┌────────────────┐    ┌──────────────────────┐   │
│  │ Billing API    │───►│ BigQuery       │───►│ Cloud Monitoring    │   │
│  │ (Cost Data)    │    │ (Analytics)    │    │ (Metrics)           │   │
│  └────────────────┘    └────────────────┘    └──────────────────────┘   │
│                                                       │                  │
│              ┌────────────────────────────────────────┤                  │
│              │                     │                   │                 │
│       ┌──────▼──────┐      ┌──────▼──────┐     ┌──────▼──────┐        │
│       │ Anomaly     │      │ Budget      │     │ Alert       │        │
│       │ Detection   │      │ Prediction  │     │ Policy      │        │
│       └─────────────┘      └──────┬──────┘     └─────────────┘        │
│                                   │                                     │
│                          ┌────────▼────────┐                           │
│                          │ Automated       │                           │
│                          │ Cost Control    │                           │
│                          └─────────────────┘                           │
└────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# 1. Enable required APIs
gcloud services enable cloudbilling.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable monitoring.googleapis.com

# 2. Set billing account
export BILLING_ACCOUNT_ID=$(gcloud billing accounts list --format="value(name)" | head -1)

# 3. Verify billing access
gcloud billing accounts describe $BILLING_ACCOUNT_ID
```

## Spend Anomaly Detection

### Daily Spend Analysis

```bash
# Query daily spend from BigQuery export
bq query --use_legacy_sql=false \
  "SELECT
    DATE(usage_start_time) as day,
    SUM(cost) as daily_cost,
    SUM(usage_amount) as usage_amount
  FROM \`my_project.billing_dataset.gcp_billing_export_v1_XXXXXX\`
  WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY 1
  ORDER BY 1 DESC"
```

### Anomaly Detection Query

```bash
# Detect spend anomalies using z-score
bq query --use_legacy_sql=false \
  "WITH daily_costs AS (
    SELECT
      DATE(usage_start_time) as day,
      SUM(cost) as daily_cost
    FROM \`my_project.billing_dataset.gcp_billing_export_v1_XXXXXX\`
    WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    GROUP BY 1
  ),
  stats AS (
    SELECT
      AVG(daily_cost) as mean_cost,
      STDDEV(daily_cost) as stddev_cost
    FROM daily_costs
  )
  SELECT
    d.day,
    d.daily_cost,
    (d.daily_cost - s.mean_cost) / NULLIF(s.stddev_cost, 0) as z_score,
    CASE
      WHEN ABS((d.daily_cost - s.mean_cost) / NULLIF(s.stddev_cost, 0)) > 3 THEN 'CRITICAL'
      WHEN ABS((d.daily_cost - s.mean_cost) / NULLIF(s.stddev_cost, 0)) > 2 THEN 'HIGH'
      ELSE 'NORMAL'
    END as anomaly_level
  FROM daily_costs d
  CROSS JOIN stats s
  WHERE ABS((d.daily_cost - s.mean_cost) / NULLIF(s.stddev_cost, 0)) > 2
  ORDER BY d.day DESC"
```

## Budget Threshold Prediction

### Linear Regression Prediction

```bash
# Predict monthly spend using linear regression
bq query --use_legacy_sql=false \
  "WITH daily_costs AS (
    SELECT
      DATE(usage_start_time) as day,
      SUM(cost) as daily_cost,
      ROW_NUMBER() OVER (ORDER BY DATE(usage_start_time)) as day_num
    FROM \`my_project.billing_dataset.gcp_billing_export_v1_XXXXXX\`
    WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    GROUP BY 1
  ),
  regression AS (
    SELECT
      COUNT(*) as n,
      SUM(day_num) as sum_x,
      SUM(daily_cost) as sum_y,
      SUM(day_num * daily_cost) as sum_xy,
      SUM(day_num * day_num) as sum_x2
    FROM daily_costs
  )
  SELECT
    (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) as slope,
    (sum_y - slope * sum_x) / n as intercept,
    slope * 30 + intercept as projected_monthly_cost,
    (slope * 30 + intercept) * 1.2 as upper_bound_20pct
  FROM regression"
```

## Cost Spike Detection

### Service-Level Anomaly Detection

```bash
# Detect anomalies by service
bq query --use_legacy_sql=false \
  "WITH service_costs AS (
    SELECT
      service.description as service,
      DATE(usage_start_time) as day,
      SUM(cost) as daily_cost
    FROM \`my_project.billing_dataset.gcp_billing_export_v1_XXXXXX\`
    WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    GROUP BY 1, 2
  ),
  service_stats AS (
    SELECT
      service,
      AVG(daily_cost) as mean_cost,
      STDDEV(daily_cost) as stddev_cost
    FROM service_costs
    GROUP BY 1
  )
  SELECT
    sc.service,
    sc.day,
    sc.daily_cost,
    (sc.daily_cost - ss.mean_cost) / NULLIF(ss.stddev_cost, 0) as z_score
  FROM service_costs sc
  JOIN service_stats ss ON sc.service = ss.service
  WHERE ABS((sc.daily_cost - ss.mean_cost) / NULLIF(ss.stddev_cost, 0)) > 2
  ORDER BY z_score DESC"
```

## Real-Time Alerting

### Budget Alert Setup

```bash
# Create budget alert
gcloud billing budgets create \
  --billing-account=$BILLING_ACCOUNT_ID \
  --display-name="Monthly Budget Alert" \
  --budget-amount=1000 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100 \
  --all-updates-rule-pubsub-topic=projects/$CLOUDSDK_CORE_PROJECT/topics/budget-alerts
```

### Cloud Monitoring Alert

```bash
# Create cost anomaly alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="Billing Cost Anomaly" \
  --condition-display-name="Daily Cost > $200" \
  --condition-filter='metric.type="billing.googleapis.com/billing/total_cost" resource.type="global"' \
  --condition-threshold-value=200 \
  --condition-threshold-duration=3600s \
  --condition-threshold-comparison=COMPARISON_GT
```

## Automated Remediation

### Auto-Disable Unused Projects

```bash
#!/bin/bash
# auto-disable-unused.sh

# Find projects with no activity in 30 days
gcloud projects list --format="value(projectId)" | while read -r project; do
  LAST_ACTIVITY=$(gcloud logging read "protoPayload.serviceName=cloudresourcemanager.googleapis.com" \
    --project=$project --limit=1 --format="value(timestamp)" 2>/dev/null | head -1)
  
  if [ -z "$LAST_ACTIVITY" ]; then
    echo "Disabling unused project: $project"
    gcloud services disable compute.googleapis.com --project=$project
  fi
done
```

### Auto-Snapshot Before Delete

```bash
#!/bin/bash
# auto-snapshot-before-delete.sh

# Find VMs scheduled for deletion
gcloud compute instances list --format="value(name,zone,status)" | \
while read -r name zone status; do
  if [[ $name == *"delete"* ]] || [[ $name == *"temp"* ]]; then
    echo "Creating snapshot for: $name"
    gcloud compute disks snapshot $name --zone=$zone --snapshot-names=$name-snapshot
  fi
done
```

## Best Practices

1. **Export Billing Data**: Enable BigQuery export for detailed analysis
2. **Set Budget Alerts**: Configure multiple threshold alerts (80%, 90%, 100%)
3. **Monitor by Service**: Track costs per GCP service
4. **Use Labels**: Implement cost allocation with labels
5. **Review Monthly**: Conduct regular cost reviews
6. **Automate Cleanup**: Remove unused resources automatically
7. **Forecast Regularly**: Use historical data for budget planning

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Budget alerts not firing | Incorrect notification config | Check notification channels |
| Cost data delayed | Export latency | Wait 24-48 hours for full data |
| Missing cost data | Export not configured | Enable BigQuery export |
| High variance | Seasonal patterns | Use longer baseline period |

## See Also

- [Billing Monitoring](../monitoring.md)
- [Billing Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud FinOps Guide](https://cloud.google.com/architecture/cost-optimization)
