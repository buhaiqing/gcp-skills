# AIOps Anomaly Detection — Google Cloud Storage

> Provides storage administrators with a guide to implementing AIOps-driven anomaly detection for Cloud Storage — access pattern anomalies, storage growth prediction, lifecycle policy violations, and automated remediation.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Access Pattern Anomalies](#access-pattern-anomalies)
5. [Storage Growth Prediction](#storage-growth-prediction)
6. [Lifecycle Policy Violations](#lifecycle-policy-violations)
7. [Real-Time Alerting](#real-time-alerting)
8. [Automated Remediation](#automated-remediation)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [See Also](#see-also)

## Overview

AIOps for Cloud Storage detects unusual access patterns and predicts storage growth. With Cloud Storage logs and Cloud Monitoring, you can:

- Detect access pattern anomalies (unusual reads/writes)
- Monitor storage growth (capacity planning)
- Track lifecycle policy violations (cost optimization)
- Identify unauthorized access attempts (security)
- Automate storage management responses

### Detection Capabilities

| Anomaly Type | Detection Method | Severity |
|--------------|-----------------|----------|
| Unusual read pattern | Volume deviation | Medium |
| Write spike detection | Threshold monitoring | High |
| Storage growth anomaly | Linear regression | Medium |
| Lifecycle violation | Policy audit | Low |
| Unauthorized access | Access log analysis | Critical |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Storage Monitoring                              │
│                                                                          │
│  Cloud Storage Buckets                                                   │
│  ┌────────────────┐    ┌────────────────┐    ┌──────────────────────┐   │
│  │ Object Access  │───►│ Cloud Logging  │───►│ Cloud Monitoring    │   │
│  │ Logs           │    │ (Log Router)   │    │ (Metrics)           │   │
│  └────────────────┘    └────────────────┘    └──────────────────────┘   │
│                                                       │                  │
│              ┌────────────────────────────────────────┤                  │
│              │                     │                   │                 │
│       ┌──────▼──────┐      ┌──────▼──────┐     ┌──────▼──────┐        │
│       │ Access      │      │ Storage     │     │ Alert       │        │
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
gcloud services enable storage.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com

# 2. Set project
export CLOUDSDK_CORE_PROJECT=my-gcs-project

# 3. Verify storage access
gsutil ls -p $CLOUDSDK_CORE_PROJECT
```

## Access Pattern Anomalies

### Access Log Analysis

```bash
# Enable access logging
gsutil logging set on -b gs://my-logging-bucket gs://my-data-bucket

# Query access logs
bq query --use_legacy_sql=false \
  "SELECT
    timestamp,
    protoPayload.methodName,
    protoPayload.resourceName,
    protoPayload.status.message
  FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
  WHERE resource.labels.bucket_name = 'my-data-bucket'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  ORDER BY timestamp DESC
  LIMIT 100"
```

### Read/Write Pattern Analysis

```bash
# Analyze access patterns
bq query --use_legacy_sql=false \
  "SELECT
    protoPayload.methodName as operation,
    COUNT(*) as count,
    MIN(timestamp) as first_access,
    MAX(timestamp) as last_access
  FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
  WHERE resource.labels.bucket_name = 'my-data-bucket'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  GROUP BY 1
  ORDER BY count DESC"
```

### Anomaly Detection Query

```bash
# Detect unusual access patterns
bq query --use_legacy_sql=false \
  "WITH hourly_access AS (
    SELECT
      TIMESTAMP_TRUNC(timestamp, HOUR) as hour,
      protoPayload.methodName as operation,
      COUNT(*) as access_count
    FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
    WHERE resource.labels.bucket_name = 'my-data-bucket'
      AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    GROUP BY 1, 2
  ),
  stats AS (
    SELECT
      operation,
      AVG(access_count) as mean_access,
      STDDEV(access_count) as stddev_access
    FROM hourly_access
    GROUP BY 1
  )
  SELECT
    ha.hour,
    ha.operation,
    ha.access_count,
    (ha.access_count - s.mean_access) / NULLIF(s.stddev_access, 0) as z_score
  FROM hourly_access ha
  JOIN stats s ON ha.operation = s.operation
  WHERE ABS((ha.access_count - s.mean_access) / NULLIF(s.stddev_access, 0)) > 2
  ORDER BY ha.hour DESC"
```

## Storage Growth Prediction

### Storage Usage Analysis

```bash
# Analyze storage growth
gsutil du -s gs://my-data-bucket

# Get bucket size over time
bq query --use_legacy_sql=false \
  "SELECT
    DATE(timestamp) as day,
    SUM(protoPayload.bytesDeleted) / 1073741824 as deleted_gb,
    SUM(protoPayload.bytesUploaded) / 1073741824 as uploaded_gb
  FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
  WHERE resource.labels.bucket_name = 'my-data-bucket'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY 1
  ORDER BY 1"
```

### Growth Prediction

```bash
# Predict storage growth
cat << 'EOF' > predict_gcs_growth.sh
#!/bin/bash
BUCKET=$1
DAYS=$2

for i in $(seq 0 $DAYS); do
  DATE=$(date -v-${i}d +%Y-%m-%d)
  SIZE=$(gsutil du -s gs://$BUCKET 2>/dev/null | awk '{print $1}')
  echo "$DATE $SIZE"
done | awk '{
  sum_x += NR; sum_y += $2; sum_xy += NR*$2; sum_x2 += NR*NR; n++
}
END {
  slope = (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x*sum_x)
  printf "Projected daily growth: %.2f bytes\n", slope
  printf "Projected monthly growth: %.2f GB\n", slope*30/1073741824
}'
EOF
chmod +x predict_gcs_growth.sh
./predict_gcs_growth.sh my-data-bucket 30
```

## Lifecycle Policy Violations

### Policy Audit

```bash
# Check lifecycle policies
gsutil lifecycle get gs://my-data-bucket

# Audit policy effectiveness
bq query --use_legacy_sql=false \
  "SELECT
    protoPayload.methodName,
    COUNT(*) as violation_count
  FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
  WHERE resource.labels.bucket_name = 'my-data-bucket'
    AND protoPayload.methodName LIKE '%lifecycle%'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  GROUP BY 1"
```

## Real-Time Alerting

### Storage Alert Setup

```bash
# Create storage usage alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="GCS Bucket Size High" \
  --condition-display-name="Storage > 1TB" \
  --condition-filter='metric.type="storage.googleapis.com/storage/total_bytes" resource.type="gcs_bucket"' \
  --condition-threshold-value=1099511627776 \
  --condition-threshold-duration=3600s \
  --condition-threshold-comparison=COMPARISON_GT
```

### Access Alert Setup

```bash
# Create access spike alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="GCS Access Spike" \
  --condition-display-name="Operations > 1000/min" \
  --condition-filter='metric.type="storage.googleapis.com/api/request_count" resource.type="gcs_bucket"' \
  --condition-threshold-value=1000 \
  --condition-threshold-duration=60s \
  --condition-threshold-comparison=COMPARISON_GT
```

## Automated Remediation

### Auto-Delete Old Objects

> ⚠️ **IRREVERSIBLE** — this deletes live data. A real delete can ONLY run after a dry-run preview AND an explicit confirmation gate. Never print credential values (see AGENTS.md §0.1 — mask SA key content with `****`).

```bash
#!/bin/bash
# auto-delete-old-objects.sh
# IRREVERSIBLE: deletes objects older than N days. Dry-run + explicit confirm required.
# Credential safety: never echo $GOOGLE_APPLICATION_CREDENTIALS content (AGENTS.md §0.1).
set -euo pipefail

BUCKET=${1:-}
DAYS=${2:-}
CONFIRM=${3:-}

# HALT if required args missing
if [[ -z "$BUCKET" || -z "$DAYS" ]]; then
  echo "[ERROR] Usage: $0 <BUCKET> <DAYS> [--confirm]" >&2
  exit 1
fi

PREFIX="gs://$BUCKET/**"
CUTOFF="gs://$(date -v-${DAYS}d +%Y-%m-%d)T*"

# DRY-RUN: list exactly what WOULD be deleted, no mutation
echo "[DRY-RUN] Objects that would be deleted (older than $DAYS days):"
gsutil -m ls "$PREFIX" "$CUTOFF" || true
echo "[DRY-RUN] Command that would execute:"
echo "  gsutil -m rm -r $PREFIX $CUTOFF"

# GATE: require explicit --confirm after operator reviews the dry-run
if [[ "$CONFIRM" != "--confirm" ]]; then
  echo "[CONFIRM] Review the dry-run above. To apply, re-run with the exact flag:"
  echo "  $0 $BUCKET $DAYS --confirm"
  echo "[HALT] No delete performed."
  exit 0
fi

# APPLY: real delete only after explicit confirmation
echo "[EXEC] Deleting objects older than $DAYS days from gs://$BUCKET"
gsutil -m rm -r "$PREFIX" "$CUTOFF"
echo "[RESULT] Done."
```

### Auto-Transition to Nearline

```bash
#!/bin/bash
# auto-transition-nearline.sh

BUCKET=$1

# Set lifecycle policy to move to Nearline after 30 days
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
    }
  ]
}
EOF

gsutil lifecycle set lifecycle.json gs://$BUCKET
```

## Best Practices

1. **Enable Access Logging**: Monitor all bucket access
2. **Set Lifecycle Policies**: Automate storage class transitions
3. **Use Labels**: Implement cost allocation with labels
4. **Monitor Growth**: Set up alerts for storage thresholds
5. **Review Access Patterns**: Regularly audit access logs
6. **Optimize Storage Classes**: Use appropriate storage tiers
7. **Implement Versioning**: Protect against accidental deletion

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High egress costs | Excessive downloads | Use CDN, optimize access |
| Storage cost spike | Uncontrolled growth | Implement lifecycle policies |
| Access denied errors | IAM misconfiguration | Check bucket permissions |
| Lifecycle not working | Policy misconfiguration | Verify policy syntax |

### Debug Commands

```bash
# Check bucket permissions
gsutil iam get gs://my-data-bucket

# List lifecycle policies
gsutil lifecycle get gs://my-data-bucket

# Check bucket size
gsutil du -s gs://my-data-bucket
```

## See Also

- [GCS Monitoring](../monitoring.md)
- [GCS Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud Architecture Framework — Performance](https://cloud.google.com/architecture/framework/performance)
