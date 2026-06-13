# FinOps Cost Optimization — Google Cloud Pub/Sub

> Provides messaging administrators with a complete guide to optimizing costs associated with Cloud Pub/Sub — message volume cost optimization, snapshot cost analysis, and streaming vs batch cost comparison.

## Table of Contents

1. [Overview](#overview)
2. [Pub/Sub Cost Model](#pubsub-cost-model)
3. [Message Volume Optimization](#message-volume-optimization)
4. [Snapshot Cost Analysis](#snapshot-cost-analysis)
5. [Streaming vs Batch Comparison](#streaming-vs-batch-comparison)
6. [Cost Monitoring](#cost-monitoring)
7. [Troubleshooting High Costs](#troubleshooting-high-costs)
8. [See Also](#see-also)

## Overview

Pub/Sub costs primarily come from:

- **Message Ingestion** — per-GB cost for message data
- **Message Delivery** — per-GB cost for delivered messages
- **Snapshot Storage** — per-GB cost for snapshots
- **BigQuery Ingestion** — per-GB cost for BigQuery subscriptions

Optimizing these costs can reduce Pub/Sub spend by 30-50% for most workloads.

### Cost Drivers

| Resource | Pricing Model | Typical Monthly Cost | Optimization Potential |
|----------|---------------|---------------------|------------------------|
| Message Ingestion | $40/TB | $40/TB | 30-50% |
| Message Delivery | $40/TB | $40/TB | 20-40% |
| Snapshot Storage | $0.02/GB/month | $2/100GB | 40-60% |
| BigQuery Ingestion | $0.05/GB | $50/1TB | 30-50% |

## Pub/Sub Cost Model

### Pricing Breakdown

| Resource | Cost Component | Rate |
|----------|---------------|------|
| Message Ingestion | Per GB | $0.04/GB |
| Message Delivery | Per GB | $0.04/GB |
| Snapshot Storage | Per GB/month | $0.02/GB |
| BigQuery Ingestion | Per GB | $0.05/GB |
| Message Retention | Per GB/month | $0.02/GB |

### Cost Calculator

```bash
# Calculate message cost
echo "1TB ingestion: $(echo "scale=2; 1024 * 0.04" | bc) = $40.96"
echo "1TB delivery: $(echo "scale=2; 1024 * 0.04" | bc) = $40.96"

# Calculate snapshot cost
echo "100GB snapshot: $(echo "scale=2; 100 * 0.02" | bc) = $2.00/month"
```

## Message Volume Optimization

### Message Size Analysis

```bash
# Analyze message sizes
bq query --use_legacy_sql=false \
  "SELECT
    resource.labels.topic_id as topic,
    AVG(protoPayload.messageSize) as avg_size,
    MAX(protoPayload.messageSize) as max_size,
    SUM(protoPayload.messageSize) / 1073741824 as total_gb
  FROM \`my_project.logging_bucket/pubsub.googleapis.com_activity\`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  GROUP BY 1
  ORDER BY total_gb DESC"
```

### Message Batching

```bash
# Configure batching
gcloud pubsub subscriptions update my-subscription \
  --batching-max-messages=100 \
  --batching-max-duration=10s
```

## Snapshot Cost Analysis

### Snapshot Inventory

```bash
# List snapshots
gcloud pubsub snapshots list --format="table(name,topic,expireTime)"

# Calculate snapshot costs
gcloud pubsub snapshots list --format="json" | \
  jq '.[] | {
    name: .name,
    topic: .topic,
    expireTime: .expireTime
  }'
```

### Snapshot Optimization

```bash
# Delete old snapshots
gcloud pubsub snapshots delete old-snapshot

# Set snapshot expiration
gcloud pubsub snapshots create my-snapshot \
  --topic=my-topic \
  --retain-duration=3600
```

## Streaming vs Batch Comparison

### Cost Comparison

```bash
# Compare streaming vs batch costs
echo "Streaming (1TB/month):"
echo "  - Ingestion: $40.96"
echo "  - Delivery: $40.96"
echo "  - Total: $81.92"
echo ""
echo "Batch (1TB/month):"
echo "  - Ingestion: $40.96"
echo "  - Delivery: $40.96"
echo "  - Total: $81.92"
echo ""
echo "Note: Batch can reduce costs by 20-40% through batching"
```

### Batch Configuration

```bash
# Configure batch for cost optimization
gcloud pubsub subscriptions update my-subscription \
  --batching-max-messages=1000 \
  --batching-max-duration=60s \
  --batching-max-bytes=1048576
```

## Cost Monitoring

### Cost Dashboard

```bash
# Query Pub/Sub costs from BigQuery
bq query --use_legacy_sql=false \
  "SELECT
    service.description,
    SUM(cost) as total_cost
  FROM \`my_project.billing_dataset.gcp_billing_export_v1_XXXXXX\`
  WHERE service.description = 'Cloud Pub/Sub'
    AND usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY 1"
```

### Budget Alerts

```bash
# Create Pub/Sub budget alert
gcloud billing budgets create \
  --billing-account=$BILLING_ACCOUNT_ID \
  --display-name="Pub/Sub Budget" \
  --budget-amount=500 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100
```

## Troubleshooting High Costs

### Common Cost Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High message volume | Excessive publishing | Optimize message frequency |
| Large message sizes | Payload bloat | Compress, use references |
| Snapshot costs | Too many snapshots | Delete unused snapshots |
| BigQuery costs | Frequent ingestion | Batch BigQuery subscriptions |

### Cost Investigation

```bash
# Find most expensive topics
bq query --use_legacy_sql=false \
  "SELECT
    resource.labels.topic_id as topic,
    SUM(protoPayload.messageSize) / 1073741824 as total_gb,
    SUM(protoPayload.messageSize) / 1073741824 * 0.04 as estimated_cost
  FROM \`my_project.logging_bucket/pubsub.googleapis.com_activity\`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY 1
  ORDER BY total_gb DESC"
```

## See Also

- [Pub/Sub Monitoring](../monitoring.md)
- [Pub/Sub Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud FinOps Guide](https://cloud.google.com/architecture/cost-optimization)
