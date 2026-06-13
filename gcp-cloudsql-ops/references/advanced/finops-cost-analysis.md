# FinOps Cost Optimization — Google Cloud SQL

> Provides database administrators with a complete guide to optimizing costs associated with Google Cloud SQL — storage tier optimization, instance right-sizing, backup cost analysis, and high availability optimization.

## Table of Contents

1. [Overview](#overview)
2. [Cloud SQL Cost Model](#cloud-sql-cost-model)
3. [Storage Optimization](#storage-optimization)
4. [Instance Right-Sizing](#instance-right-sizing)
5. [Backup Cost Analysis](#backup-cost-analysis)
6. [High Availability Optimization](#high-availability-optimization)
7. [Cost Monitoring](#cost-monitoring)
8. [Troubleshooting High Costs](#troubleshooting-high-costs)
9. [See Also](#see-also)

## Overview

Cloud SQL costs primarily come from:

- **Compute** — instance hours (CPU + memory)
- **Storage** — SSD/HDD storage per GB
- **Network** — egress charges
- **Backups** — backup storage beyond free tier
- **High Availability** — standby instance costs

Optimizing these costs can reduce Cloud SQL spend by 30-60% for most workloads.

### Cost Drivers

| Resource | Pricing Model | Typical Monthly Cost | Optimization Potential |
|----------|---------------|---------------------|------------------------|
| Instance (db-f1-micro) | $0.015/hr | $11 | 40-60% |
| Instance (db-n1-standard-1) | $0.05/hr | $36 | 30-50% |
| SSD Storage | $0.17/GB/month | $17/100GB | 40-60% |
| HDD Storage | $0.04/GB/month | $4/100GB | 20-40% |
| Backups | $0.08/GB/month | $8/100GB | 30-50% |

## Cloud SQL Cost Model

### Pricing Breakdown

| Resource | Cost Component | Rate |
|----------|---------------|------|
| db-f1-micro | Per-hour | $0.015/hr |
| db-g1-small | Per-hour | $0.025/hr |
| db-n1-standard-1 | Per-hour | $0.05/hr |
| db-n1-standard-2 | Per-hour | $0.10/hr |
| db-n1-standard-4 | Per-hour | $0.20/hr |
| SSD Storage | Per GB/month | $0.17/GB |
| HDD Storage | Per GB/month | $0.04/GB |
| Backups | Per GB/month | $0.08/GB |
| Data Transfer | Per GB | $0.12/GB |

### Cost Calculator

```bash
# Calculate instance cost
echo "db-n1-standard-1 monthly: $(echo "scale=2; 0.05 * 730" | bc) = $36.50"

# Calculate storage cost
echo "100GB SSD monthly: $(echo "scale=2; 100 * 0.17" | bc) = $17.00"
echo "100GB HDD monthly: $(echo "scale=2; 100 * 0.04" | bc) = $4.00"
```

## Storage Optimization

### Storage Tier Analysis

```bash
# Analyze storage usage
gcloud sql instances describe my-instance \
  --format="json" | jq '{diskType: .databaseDiskType, diskSize: .diskSize, diskUsage: .diskUsage}'

# Calculate storage utilization
DISK_SIZE=$(gcloud sql instances describe my-instance --format="value(diskSize)")
DISK_USAGE=$(gcloud sql instances describe my-instance --format="value(diskUsage)")
UTILIZATION=$(echo "scale=2; $DISK_USAGE / $DISK_SIZE * 100" | bc)
echo "Storage utilization: ${UTILIZATION}%"
```

### Storage Type Optimization

```bash
# Switch to HDD for cold data
gcloud sql instances patch my-instance \
  --database-version=MYSQL_8_0 \
  --storage-type=HDD \
  --storage-size=100GB

# Use SSD for hot data
gcloud sql instances patch my-instance \
  --database-version=MYSQL_8_0 \
  --storage-type=SSD \
  --storage-size=50GB
```

## Instance Right-Sizing

### CPU/Memory Analysis

```bash
# Analyze CPU usage
gcloud sql operations list --instance=my-instance \
  --filter="operationType=QUERY" \
  --format="json" | \
  jq 'map(.cpuUsage) | {avg: (add / length), max: max}'

# Analyze memory usage
gcloud sql instances describe my-instance \
  --format="json" | jq '.settings.machineType'
```

### Right-Sizing Recommendations

```bash
# Get machine type recommendations
gcloud sql instances describe my-instance \
  --format="json" | jq '.settings.machineType'

# List available machine types
gcloud sql sizes list --format="table(name,memoryGb,vcpuCount)"
```

## Backup Cost Analysis

### Backup Storage Analysis

```bash
# Analyze backup storage
gcloud sql backups list --instance=my-instance \
  --format="json" | \
  jq 'map(.backupSize) | {total: (add / 1073741824), count: length}'

# Calculate backup cost
BACKUP_SIZE=$(gcloud sql backups list --instance=my-instance --format="json" | \
  jq 'map(.backupSize) | add / 1073741824')
echo "Monthly backup cost: $(echo "scale=2; $BACKUP_SIZE * 0.08" | bc)"
```

### Backup Optimization

```bash
# Configure backup retention
gcloud sql instances patch my-instance \
  --backup-start-time=02:00 \
  --no-enable-point-in-time-recovery

# Delete old backups
gcloud sql backups delete BACKUP_ID --instance=my-instance
```

## High Availability Optimization

### HA Cost Analysis

```bash
# Analyze HA costs
gcloud sql instances describe my-instance \
  --format="json" | jq '.settings.availabilityType'

# Calculate HA premium
STANDARD_COST=36
HA_COST=$(echo "scale=2; $STANDARD_COST * 2" | bc)
echo "HA premium: $(echo "scale=2; $HA_COST - $STANDARD_COST" | bc)"
```

### HA vs Regional Deployment

```bash
# Compare HA vs regional
echo "HA (single zone): $36/month"
echo "Regional (multi-zone): $72/month"
echo "Regional with failover: $108/month"
```

## Cost Monitoring

### Cost Dashboard

```bash
# Query Cloud SQL costs from BigQuery
bq query --use_legacy_sql=false \
  "SELECT
    service.description,
    SUM(cost) as total_cost
  FROM \`my_project.billing_dataset.gcp_billing_export_v1_XXXXXX\`
  WHERE service.description = 'Cloud SQL'
    AND usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY 1"
```

### Budget Alerts

```bash
# Create Cloud SQL budget alert
gcloud billing budgets create \
  --billing-account=$BILLING_ACCOUNT_ID \
  --display-name="Cloud SQL Budget" \
  --budget-amount=500 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100
```

## Troubleshooting High Costs

### Common Cost Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High compute costs | Over-provisioned instance | Right-size instance |
| Storage cost spike | Uncontrolled growth | Implement cleanup |
| Backup costs | Excessive retention | Reduce backup retention |
| HA costs | Unnecessary HA | Disable HA if not needed |

### Cost Investigation

```bash
# Find cost breakdown
gcloud sql instances describe my-instance \
  --format="json" | jq '{
    machineType: .settings.machineType,
    storageType: .databaseDiskType,
    storageSize: .diskSize,
    availabilityType: .settings.availabilityType
  }'
```

## See Also

- [Cloud SQL Monitoring](../monitoring.md)
- [Cloud SQL Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud FinOps Guide](https://cloud.google.com/architecture/cost-optimization)
