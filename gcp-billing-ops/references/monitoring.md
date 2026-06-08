---
name: billing-monitoring
description: Cloud Monitoring metrics, dashboards, and alert policies for Cloud Billing

<!---
load_condition: "[监控/告警操作时加载]"
token_cost_estimate: "~1000 tokens"
dependencies: []
--->
---

# Monitoring — Cloud Billing

## Key Billing Metrics

| Metric | Namespace | Description |
|--------|-----------|-------------|
| `billing.googleapis.com/monthly_spend` | Billing | Total monthly spend per billing account |
| `billing.googleapis.com/daily_spend` | Billing | Daily spend per billing account |
| `billing.googleapis.com/budget` | Billing Budgets | Budget amount, current spend, forecasted spend |
| `billing.googleapis.com/budget_alert` | Billing Budgets | Budget threshold breach events |

## Budget Alert Monitoring

Budget alerts are the primary monitoring mechanism. Configure via budget threshold rules:

```bash
# View budget alert status
gcloud alpha billing budgets describe "{{user.budget_id}}" \
  --billing-account="{{user.billing_account_id}}" \
  --format=json | jq '{name, displayName, amount: .amount.specifiedAmount.units, thresholds: [.thresholdRules[]]}'
```

### Alert Channels

Budget alerts can notify via:
- **Pub/Sub topic**: `projects/{project}/topics/{topic}` — for programmatic consumption
- **Monitoring notification channels**: Email, SMS, Slack, PagerDuty, Webhook — configured in Cloud Monitoring
- **Email recipients**: Direct email addresses (max 5 per threshold rule)

## Cloud Monitoring Dashboards

### Billing Spend Dashboard (MQL)

```bash
# Create a billing spend chart
gcloud monitoring dashboards create --config-from-file=billing-dashboard.json
```

Key metrics to monitor:
- `billing.googleapis.com/monthly_spend` grouped by service
- `billing.googleapis.com/daily_spend` with 30-day trend
- Budget utilization percentage (current spend / budget amount)

## Export Pipeline Monitoring

Monitor billing export health:

```bash
# Check if export tables are receiving data
bq query --nouse_legacy_sql \
  "SELECT DATE(usage_start_time) as date, SUM(cost) as daily_cost \
   FROM \`{{user.export_dataset}}.gcp_billing_export_v1*\` \
   WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) \
   GROUP BY date ORDER BY date DESC"
```

Alert if:
- No new data for > 48 hours
- Export table row count drops significantly
- Cost data shows unexpected spikes

## Alert Policy Examples

### Budget Threshold Alert (via Pub/Sub)

```bash
gcloud alpha billing budgets create \
  --billing-account="{{user.billing_account_id}}" \
  --display-name="production-monthly" \
  --budget-amount="5000" \
  --threshold-rule=percent=0.5,spend-basis=current-spend \
  --threshold-rule=percent=0.8,spend-basis=forecasted-spend \
  --threshold-rule=percent=1.0,spend-basis=current-spend \
  --pubsub-topic="projects/{{env.CLOUDSDK_CORE_PROJECT}}/topics/budget-alerts" \
  --calendar-period=MONTH
```

### Cost Anomaly Detection (Cloud Monitoring)

```bash
gcloud alpha monitoring policies create \
  --policy-from-file=cost-anomaly-policy.yaml
```

Example policy condition: `billing.googleapis.com/daily_spend` deviates > 30% from 7-day rolling average.

## Key Monitoring Checks

| Check | Command | Expected |
|-------|---------|----------|
| Budget status | `gcloud alpha billing budgets list --billing-account=...` | All budgets in active state |
| Export freshness | BigQuery query on latest partition | Data within 24-48h |
| Alert channel health | Verify Pub/Sub topic exists and has subscribers | Active subscriptions |
| Spend trend | Compare current month vs previous month | Within expected range |
