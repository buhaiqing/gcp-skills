# AIOps Anomaly Detection — Google Cloud IAM

> Provides security administrators with a guide to implementing AIOps-driven anomaly detection for Cloud IAM — privilege escalation detection, unusual API call patterns, service account key anomalies, and role binding drift detection.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Privilege Escalation Detection](#privilege-escalation-detection)
5. [API Call Pattern Anomalies](#api-call-pattern-anomalies)
6. [Service Account Key Anomalies](#service-account-key-anomalies)
7. [Role Binding Drift Detection](#role-binding-drift-detection)
8. [Real-Time Alerting](#real-time-alerting)
9. [Automated Remediation](#automated-remediation)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [See Also](#see-also)

## Overview

AIOps for Cloud IAM detects security anomalies and policy drift. With Cloud Audit Logs and Cloud Monitoring, you can:

- Detect privilege escalation attempts
- Monitor unusual API call patterns
- Track service account key anomalies
- Identify role binding drift
- Automate security responses

### Detection Capabilities

| Anomaly Type | Detection Method | Severity |
|--------------|-----------------|----------|
| Privilege escalation | Policy change analysis | Critical |
| Unusual API calls | Baseline deviation | High |
| Key rotation missing | Age monitoring | Medium |
| Role binding drift | Policy comparison | High |
| Service account abuse | Usage pattern analysis | Critical |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          IAM Security Monitoring                        │
│                                                                          │
│  Cloud IAM                                                               │
│  ┌────────────────┐    ┌────────────────┐    ┌──────────────────────┐   │
│  │ Policy Changes │───►│ Cloud Audit    │───►│ Cloud Monitoring    │   │
│  │ (Bindings)     │    │ Logs           │    │ (Metrics)           │   │
│  └────────────────┘    └────────────────┘    └──────────────────────┘   │
│                                                       │                  │
│              ┌────────────────────────────────────────┤                  │
│              │                     │                   │                 │
│       ┌──────▼──────┐      ┌──────▼──────┐     ┌──────▼──────┐        │
│       │ Privilege   │      │ API Call    │     │ Alert       │        │
│       │ Analysis    │      │ Analysis    │     │ Policy      │        │
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
gcloud services enable iam.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com

# 2. Set project
export CLOUDSDK_CORE_PROJECT=my-iam-project

# 3. Verify IAM access
gcloud projects get-iam-policy $CLOUDSDK_CORE_PROJECT
```

## Privilege Escalation Detection

### Policy Change Monitoring

```bash
# Monitor IAM policy changes
bq query --use_legacy_sql=false \
  "SELECT
    timestamp,
    protoPayload.methodName,
    protoPayload.principalEmail,
    protoPayload.resourceName
  FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
  WHERE protoPayload.methodName LIKE 'setIamPolicy%'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  ORDER BY timestamp DESC"
```

### Privilege Escalation Detection

```bash
# Detect privilege escalation
bq query --use_legacy_sql=false \
  "WITH policy_changes AS (
    SELECT
      timestamp,
      protoPayload.principalEmail as user,
      protoPayload.resourceName as resource,
      protoPayload.request.bindings as new_bindings
    FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
    WHERE protoPayload.methodName LIKE 'setIamPolicy%'
      AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  )
  SELECT
    user,
    resource,
    COUNT(*) as change_count,
    ARRAY_AGG(new_bindings) as all_bindings
  FROM policy_changes
  GROUP BY 1, 2
  HAVING change_count > 3
  ORDER BY change_count DESC"
```

## API Call Pattern Anomalies

### API Call Analysis

```bash
# Analyze API call patterns
bq query --use_legacy_sql=false \
  "SELECT
    protoPayload.methodName as api_method,
    COUNT(*) as call_count,
    protoPayload.principalEmail as user
  FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  GROUP BY 1, 3
  ORDER BY call_count DESC
  LIMIT 20"
```

### Anomaly Detection

```bash
# Detect unusual API calls
bq query --use_legacy_sql=false \
  "WITH api_stats AS (
    SELECT
      protoPayload.methodName as api_method,
      protoPayload.principalEmail as user,
      COUNT(*) as daily_count
    FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
    WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    GROUP BY 1, 2
  ),
  user_stats AS (
    SELECT
      user,
      AVG(daily_count) as mean_calls,
      STDDEV(daily_count) as stddev_calls
    FROM api_stats
    GROUP BY 1
  )
  SELECT
    a.user,
    a.api_method,
    a.daily_count,
    (a.daily_count - u.mean_calls) / NULLIF(u.stddev_calls, 0) as z_score
  FROM api_stats a
  JOIN user_stats u ON a.user = u.user
  WHERE ABS((a.daily_count - u.mean_calls) / NULLIF(u.stddev_calls, 0)) > 2
  ORDER BY z_score DESC"
```

## Service Account Key Anomalies

### Key Age Monitoring

```bash
# Monitor service account key age
gcloud iam service-accounts keys list \
  --iam-account=my-service-account@my-project.iam.gserviceaccount.com \
  --format="json" | \
  jq '.[] | {
    keyId: .name,
    createdAt: .validAfterTime,
    age: ((now - (.validAfterTime | fromdateiso8601)) / 86400 | floor)
  }' | \
  jq 'select(.age > 90)'
```

### Key Rotation Detection

```bash
# Detect keys needing rotation
gcloud iam service-accounts keys list \
  --iam-account=my-service-account@my-project.iam.gserviceaccount.com \
  --format="json" | \
  jq '.[] | select(
    ((now - (.validAfterTime | fromdateiso8601)) / 86400) > 90
  )' | \
  jq -r '.name + " needs rotation (age: " + ((now - (.validAfterTime | fromdateiso8601)) / 86400 | floor | tostring) + " days)"'
```

## Role Binding Drift Detection

### Policy Comparison

```bash
# Compare current vs desired policy
cat << EOF > desired_policy.json
{
  "bindings": [
    {
      "role": "roles/viewer",
      "members": ["user:viewer@example.com"]
    }
  ]
}

# Get current policy
gcloud projects get-iam-policy $CLOUDSDK_CORE_PROJECT --format=json > current_policy.json

# Compare policies
diff desired_policy.json current_policy.json
```

### Drift Detection Query

```bash
# Detect role binding drift
bq query --use_legacy_sql=false \
  "SELECT
    timestamp,
    protoPayload.methodName,
    protoPayload.principalEmail,
    protoPayload.request.bindings
  FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
  WHERE protoPayload.methodName LIKE 'setIamPolicy%'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  ORDER BY timestamp DESC"
```

## Real-Time Alerting

### Privilege Escalation Alert

```bash
# Create privilege escalation alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="IAM Privilege Escalation" \
  --condition-display-name="Policy Changes > 5/hour" \
  --condition-filter='metric.type="cloudaudit.googleapis.com/activity/policy_change_count" resource.type="global"' \
  --condition-threshold-value=5 \
  --condition-threshold-duration=3600s \
  --condition-threshold-comparison=COMPARISON_GT
```

### Key Age Alert

```bash
# Create key age alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="Service Account Key Old" \
  --condition-display-name="Key Age > 90 days" \
  --condition-filter='metric.type="iam.googleapis.com/service_account/key/age" resource.type="iam_service_account"' \
  --condition-threshold-value=7776000 \
  --condition-threshold-duration=0s \
  --condition-threshold-comparison=COMPARISON_GT
```

## Automated Remediation

### Auto-Revoke Old Keys

```bash
#!/bin/bash
# auto-revoke-old-keys.sh

ACCOUNT=$1
MAX_AGE=90

gcloud iam service-accounts keys list \
  --iam-account=$ACCOUNT \
  --format="json" | \
  jq -r ".[] | select(
    ((now - (.validAfterTime | fromdateiso8601)) / 86400) > $MAX_AGE
  ) | .name" | \
while read -r key; do
  echo "Revoking old key: $key"
  gcloud iam service-accounts keys delete $key --iam-account=$ACCOUNT
done
```

### Auto-Fix Role Binding

```bash
#!/bin/bash
# auto-fix-role-binding.sh

PROJECT=$1
DESIRED_ROLE=$2
DESIRED_MEMBER=$3

# Get current policy
CURRENT_POLICY=$(gcloud projects get-iam-policy $PROJECT --format=json)

# Add binding if missing
echo $CURRENT_POLICY | \
  jq --arg role "$DESIRED_ROLE" --arg member "$DESIRED_MEMBER" \
  '.bindings[] | select(.role == $role) | .members | index($member)' | \
  grep -q null && \
  gcloud projects add-iam-policy-binding $PROJECT \
    --member=$DESIRED_MEMBER \
    --role=$DESIRED_ROLE
```

## Best Practices

1. **Enable Audit Logging**: Log all IAM policy changes
2. **Monitor Key Age**: Set alerts for old service account keys
3. **Use Least Privilege**: Grant minimum required permissions
4. **Regular Policy Reviews**: Conduct monthly IAM audits
5. **Implement MFA**: Require multi-factor authentication
6. **Use Workload Identity**: Avoid service account key usage
7. **Automate Compliance**: Use Policy Intelligence for recommendations

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Access denied | Missing permissions | Check IAM roles |
| Key rotation failed | Invalid key | Delete and recreate |
| Policy drift | Manual changes | Use Terraform for IaC |
| Alert fatigue | Too many alerts | Tune thresholds |

### Debug Commands

```bash
# Check IAM policy
gcloud projects get-iam-policy $CLOUDSDK_CORE_PROJECT

# List service accounts
gcloud iam service-accounts list

# List keys for account
gcloud iam service-accounts keys list \
  --iam-account=my-sa@my-project.iam.gserviceaccount.com
```

## See Also

- [IAM Monitoring](../monitoring.md)
- [IAM Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud Security Best Practices](https://cloud.google.com/architecture/security-best-practices)
