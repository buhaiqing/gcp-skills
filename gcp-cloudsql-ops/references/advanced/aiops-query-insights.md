# AIOps Query Insights — Google Cloud SQL

> Provides database administrators with a guide to implementing AIOps-driven anomaly detection for Cloud SQL — query performance monitoring, storage growth prediction, connection pool anomalies, and automated remediation.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Query Performance Anomalies](#query-performance-anomalies)
5. [Storage Growth Prediction](#storage-growth-prediction)
6. [Connection Pool Monitoring](#connection-pool-monitoring)
7. [Real-Time Alerting](#real-time-alerting)
8. [Automated Remediation](#automated-remediation)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [See Also](#see-also)

## Overview

AIOps for Cloud SQL detects performance anomalies and predicts resource exhaustion. With Cloud SQL Insights and Cloud Monitoring, you can:

- Detect slow query patterns (performance regression)
- Monitor storage growth (quota management)
- Track connection pool exhaustion (availability)
- Identify lock contention issues (concurrency)
- Automate performance remediation

### Detection Capabilities

| Anomaly Type | Detection Method | Severity |
|--------------|-----------------|----------|
| Slow query increase | Time-series analysis | High |
| Storage growth spike | Linear regression | Medium |
| Connection pool exhaustion | Threshold monitoring | Critical |
| Lock contention | Wait event analysis | High |
| Replication lag | Metric deviation | Critical |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Database Monitoring                            │
│                                                                          │
│  Cloud SQL Instance                                                      │
│  ┌────────────────┐    ┌────────────────┐    ┌──────────────────────┐   │
│  │ Query Load     │───►│ Cloud SQL      │───►│ Cloud Monitoring    │   │
│  │ (Connections)  │    │ Insights       │    │ (Metrics)           │   │
│  └────────────────┘    └────────────────┘    └──────────────────────┘   │
│                                                       │                  │
│              ┌────────────────────────────────────────┤                  │
│              │                     │                   │                 │
│       ┌──────▼──────┐      ┌──────▼──────┐     ┌──────▼──────┐        │
│       │ Query       │      │ Storage     │     │ Alert       │        │
│       │ Analysis    │      │ Prediction  │     │ Policy      │        │
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
gcloud services enable sqladmin.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable cloudsql.googleapis.com

# 2. Set project
export CLOUDSDK_CORE_PROJECT=my-cloudsql-project

# 3. Verify Cloud SQL access
gcloud sql instances list --format="table(name,databaseVersion,region)"
```

## Query Performance Anomalies

### Slow Query Detection

```bash
# Find slow queries using Cloud SQL Insights
gcloud sql operations list \
  --instance=my-instance \
  --filter="operationType=QUERY" \
  --format="table(id,user,startTime,duration)"
```

### Query Performance Analysis

```bash
# Analyze query performance
gcloud sql operations list \
  --instance=my-instance \
  --filter="operationType=QUERY" \
  --format="json" | \
  jq '.[] | select(.duration > 300)' | \
  jq '{id, user, query, duration}'
```

### Performance Regression Detection

```bash
# Detect performance regression (queries getting slower)
gcloud sql operations list \
  --instance=my-instance \
  --filter="operationType=QUERY" \
  --format="json" | \
  jq 'group_by(.startTime[:10]) | map({day: .[0].startTime[:10], avgDuration: (map(.duration) | add / length)})' | \
  jq '.[] | select(.avgDuration > 60)'
```

## Storage Growth Prediction

### Storage Usage Analysis

```bash
# Analyze storage growth
gcloud sql instances describe my-instance \
  --format="json" | jq '.diskUsageBytes, .diskQuota'

# Calculate growth rate
echo "Current: $(gcloud sql instances describe my-instance --format="value(diskUsageBytes)") bytes"
echo "Quota: $(gcloud sql instances describe my-instance --format="value(diskQuota)") bytes"
```

### Growth Prediction

```bash
# Predict storage growth (linear regression)
cat << 'EOF' > predict_storage.sh
#!/bin/bash
INSTANCE=$1
DAYS=$2

# Get historical storage data
for i in $(seq 0 $DAYS); do
  DATE=$(date -v-${i}d +%Y-%m-%d)
  USAGE=$(gcloud sql operations list --instance=$INSTANCE \
    --filter="operationType=STORAGE" \
    --filter="startTime<=$DATE" \
    --format="value(diskUsageBytes)" | tail -1)
  echo "$DATE $USAGE"
done | awk '{
  sum_x += NR; sum_y += $2; sum_xy += NR*$2; sum_x2 += NR*NR; n++
}
END {
  slope = (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x*sum_x)
  intercept = (sum_y - slope*sum_x) / n
  printf "Projected daily growth: %.2f bytes\n", slope
  printf "Projected monthly growth: %.2f GB\n", slope*30/1073741824
}'
EOF
chmod +x predict_storage.sh
./predict_storage.sh my-instance 30
```

## Connection Pool Monitoring

### Connection Analysis

```bash
# Monitor active connections
gcloud sql operations list \
  --instance=my-instance \
  --filter="operationType=CONNECT" \
  --format="table(user,clientAddr,startTime)"

# Count connections by user
gcloud sql operations list \
  --instance=my-instance \
  --filter="operationType=CONNECT" \
  --format="json" | \
  jq 'group_by(.user) | map({user: .[0].user, count: length})'
```

### Connection Pool Exhaustion Detection

```bash
# Detect connection pool exhaustion
gcloud sql operations list \
  --instance=my-instance \
  --filter="operationType=CONNECT" \
  --format="json" | \
  jq 'map(select(.status == "REJECTED")) | length' | \
  xargs -I {} echo "Rejected connections: {}"
```

## Real-Time Alerting

### Storage Alert Setup

```bash
# Create storage usage alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="Cloud SQL Storage High" \
  --condition-display-name="Storage > 80%" \
  --condition-filter='metric.type="cloudsql.googleapis.com/database/disk/usage" resource.type="cloudsql_database"' \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_GT
```

### Connection Alert Setup

```bash
# Create connection alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="Cloud SQL Connections High" \
  --condition-display-name="Connections > 90%" \
  --condition-filter='metric.type="cloudsql.googleapis.com/database/connection_count" resource.type="cloudsql_database"' \
  --condition-threshold-value=0.9 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_GT
```

## Automated Remediation

### Auto-Scale Storage

```bash
#!/bin/bash
# auto-scale-storage.sh

INSTANCE=$1
CURRENT_SIZE=$(gcloud sql instances describe $INSTANCE --format="value(diskSize)")
USAGE=$(gcloud sql instances describe $INSTANCE --format="value(diskUsage)")
USAGE_PCT=$((USAGE * 100 / CURRENT_SIZE))

if [ $USAGE_PCT -gt 80 ]; then
  NEW_SIZE=$((CURRENT_SIZE + 50))
  echo "Scaling storage: ${CURRENT_SIZE}GB -> ${NEW_SIZE}GB"
  gcloud sql instances patch $INSTANCE --database-version=MYSQL_8_0 --storage-size=${NEW_SIZE}GB
fi
```

### Auto-Kill Long Queries

```bash
#!/bin/bash
# auto-kill-long-queries.sh

INSTANCE=$1
gcloud sql operations list --instance=$INSTANCE \
  --filter="operationType=QUERY" \
  --format="json" | \
  jq '.[] | select(.duration > 300) | .id' | \
while read -r op_id; do
  echo "Killing long query: $op_id"
  gcloud sql operations cancel $INSTANCE $op_id
done
```

## Best Practices

1. **Enable Cloud SQL Insights**: Use Query Insights for performance monitoring
2. **Set Connection Limits**: Configure max connections appropriately
3. **Monitor Storage Growth**: Set up alerts for storage thresholds
4. **Use Read Replicas**: Distribute read load across replicas
5. **Optimize Queries**: Use query analysis to identify slow queries
6. **Regular Backups**: Implement automated backup schedules
7. **Index Optimization**: Regularly review and optimize indexes

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High CPU usage | Slow queries, missing indexes | Optimize queries, add indexes |
| Storage full | Uncontrolled growth | Scale storage, implement cleanup |
| Connection exhaustion | Too many clients | Increase max_connections, use pooling |
| Replication lag | Heavy writes | Optimize writes, use batch operations |

### Debug Queries

```bash
# Check instance status
gcloud sql instances describe my-instance --format="table(name,state,backendType)"

# List recent operations
gcloud sql operations list --instance=my-instance --limit=10

# Check storage usage
gcloud sql instances describe my-instance --format="value(diskUsage,diskQuota)"
```

## See Also

- [Cloud SQL Monitoring](../monitoring.md)
- [Cloud SQL Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud Architecture Framework — Performance](https://cloud.google.com/architecture/framework/performance)
