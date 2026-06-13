# FinOps Cost Optimization — Google Cloud Storage

> Provides storage administrators with a complete guide to optimizing costs associated with Google Cloud Storage — storage class optimization, lifecycle policies, egress cost analysis, and retention cost modeling.

## Table of Contents

1. [Overview](#overview)
2. [GCS Cost Model](#gcs-cost-model)
3. [Storage Class Optimization](#storage-class-optimization)
4. [Lifecycle Policy Cost Reduction](#lifecycle-policy-cost-reduction)
5. [Egress Cost Analysis](#egress-cost-analysis)
6. [Cost Monitoring](#cost-monitoring)
7. [Troubleshooting High Costs](#troubleshooting-high-costs)
8. [See Also](#see-also)

## Overview

Cloud Storage costs primarily come from:

- **Storage** — per-GB cost based on storage class
- **Operations** — per-operation cost (class A and class B)
- **Network** — egress charges for data transfer
- **Retrieval** — data retrieval fees for Archive/Coldline

Optimizing these costs can reduce GCS spend by 40-70% for most workloads.

### Cost Drivers

| Resource | Pricing Model | Typical Monthly Cost | Optimization Potential |
|----------|---------------|---------------------|------------------------|
| Standard Storage | $0.020/GB/month | $20/1TB | 50-70% |
| Nearline Storage | $0.010/GB/month | $10/1TB | 30-50% |
| Coldline Storage | $0.004/GB/month | $4/1TB | 20-40% |
| Archive Storage | $0.0012/GB/month | $1.20/1TB | 10-30% |
| Class A Operations | $0.005/10K ops | $5/1M ops | 30-50% |
| Egress (internet) | $0.12/GB | $120/1TB | 40-60% |

## GCS Cost Model

### Pricing Breakdown

| Storage Class | Storage Cost | Retrieval Cost | Operations (A) | Operations (B) |
|---------------|--------------|----------------|----------------|----------------|
| Standard | $0.020/GB | Free | $0.005/10K | $0.0004/10K |
| Nearline | $0.010/GB | $0.01/GB | $0.010/10K | $0.001/10K |
| Coldline | $0.004/GB | $0.02/GB | $0.050/10K | $0.005/10K |
| Archive | $0.0012/GB | $0.05/GB | $0.50/10K | $0.05/10K |

### Cost Calculator

```bash
# Calculate storage cost
echo "1TB Standard: $(echo "scale=2; 1024 * 0.020" | bc) = $20.48/month"
echo "1TB Nearline: $(echo "scale=2; 1024 * 0.010" | bc) = $10.24/month"
echo "1TB Coldline: $(echo "scale=2; 1024 * 0.004" | bc) = $4.10/month"
echo "1TB Archive: $(echo "scale=2; 1024 * 0.0012" | bc) = $1.23/month"
```

## Storage Class Optimization

### Storage Class Analysis

```bash
# Analyze storage classes
gsutil ls -L -r gs://my-bucket | grep "Storage class:" | \
  awk '{print $NF}' | sort | uniq -c | sort -rn

# Calculate cost by storage class
gsutil du -s -L gs://my-bucket | grep "Storage class:" | \
  awk '{print $NF}' | sort | uniq -c
```

### Storage Class Recommendations

```bash
# Get storage class recommendations
gsutil ls -L -r gs://my-bucket | \
  awk '/Storage class:/{class=$NF} /Last modified:/{print class, $0}' | \
  awk '{
    class=$1
    date=$NF
    # Calculate age in days
    cmd="date -j -f "%Y-%m-%dT%H:%M:%S" " substr(date,1,19) " +%s"
    cmd | getline epoch
    close(cmd)
    age=(systime()-epoch)/86400
    if (age > 365) print "Archive: " $0
    else if (age > 90) print "Coldline: " $0
    else if (age > 30) print "Nearline: " $0
    else print "Standard: " $0
  }'
```

## Lifecycle Policy Cost Reduction

### Lifecycle Policy Setup

```bash
# Set lifecycle policy
cat << EOF > lifecycle.json
{
  "rule": [
    {
      "action": {
        "type": "SetStorageClass",
        "storageClass": "NEARLINE"
      },
      "condition": {
        "age": 30
      }
    },
    {
      "action": {
        "type": "SetStorageClass",
        "storageClass": "COLDLINE"
      },
      "condition": {
        "age": 90
      }
    },
    {
      "action": {
        "type": "SetStorageClass",
        "storageClass": "ARCHIVE"
      },
      "condition": {
        "age": 365
      }
    },
    {
      "action": {
        "type": "Delete"
      },
      "condition": {
        "age": 730
      }
    }
  ]
}
EOF

gsutil lifecycle set lifecycle.json gs://my-bucket
```

### Lifecycle Policy Analysis

```bash
# Analyze lifecycle policy savings
gsutil lifecycle get gs://my-bucket

# Calculate potential savings
echo "With lifecycle policy:"
echo "Standard (30 days): $(echo "scale=2; 1024 * 0.020 * 30/365" | bc) = $1.68"
echo "Nearline (60 days): $(echo "scale=2; 1024 * 0.010 * 60/365" | bc) = $1.69"
echo "Coldline (275 days): $(echo "scale=2; 1024 * 0.004 * 275/365" | bc) = $3.04"
echo "Archive (365 days): $(echo "scale=2; 1024 * 0.0012 * 365/365" | bc) = $1.23"
```

## Egress Cost Analysis

### Egress Analysis

```bash
# Analyze egress costs
bq query --use_legacy_sql=false \
  "SELECT
    resource.labels.bucket_name,
    SUM(protoPayload.bytesSent) / 1073741824 as egress_gb,
    SUM(protoPayload.bytesSent) / 1073741824 * 0.12 as egress_cost
  FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    AND protoPayload.methodName = 'storage.objects.get'
  GROUP BY 1
  ORDER BY egress_gb DESC"
```

### Egress Optimization

```bash
# Use Cloud CDN for caching
gsutil cors set cors-config.json gs://my-bucket

# Set cache control headers
gsutil setmeta -h "Cache-Control:public, max-age=3600" gs://my-bucket/*
```

## Cost Monitoring

### Cost Dashboard

```bash
# Query GCS costs from BigQuery
bq query --use_legacy_sql=false \
  "SELECT
    service.description,
    SUM(cost) as total_cost
  FROM \`my_project.billing_dataset.gcp_billing_export_v1_XXXXXX\`
  WHERE service.description = 'Cloud Storage'
    AND usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY 1"
```

### Budget Alerts

```bash
# Create GCS budget alert
gcloud billing budgets create \
  --billing-account=$BILLING_ACCOUNT_ID \
  --display-name="GCS Budget" \
  --budget-amount=200 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100
```

## Troubleshooting High Costs

### Common Cost Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High storage costs | Wrong storage class | Use lifecycle policies |
| Egress cost spike | Excessive downloads | Use CDN, optimize access |
| Operation costs | Too many small objects | Batch operations |
| Retrieval costs | Frequent Archive access | Use appropriate storage class |

### Cost Investigation

```bash
# Find most accessed objects
gsutil ls -L gs://my-bucket | \
  awk '/Last modified:/{date=$0} /Name:/{print date, $0}' | \
  sort -k2 -r | head -10

# Check storage class distribution
gsutil du -s -L gs://my-bucket | grep "Storage class:" | \
  awk '{print $NF}' | sort | uniq -c
```

## See Also

- [GCS Monitoring](../monitoring.md)
- [GCS Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud FinOps Guide](https://cloud.google.com/architecture/cost-optimization)
