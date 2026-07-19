# FinOps Cost Optimization — Google Cloud IAM

> Provides security administrators with a complete guide to optimizing costs associated with Google Cloud IAM — service account cost analysis, workload identity federation savings, role optimization, and unused permission cleanup.

## Table of Contents

1. [Overview](#overview)
2. [IAM Cost Model](#iam-cost-model)
3. [Service Account Cost Analysis](#service-account-cost-analysis)
4. [Workload Identity Federation Savings](#workload-identity-federation-savings)
5. [Role Optimization](#role-optimization)
6. [Unused Permission Cleanup](#unused-permission-cleanup)
7. [Cost Monitoring](#cost-monitoring)
8. [Troubleshooting High Costs](#troubleshooting-high-costs)
9. [See Also](#see-also)

## Overview

Cloud IAM costs primarily come from:

- **Service Account Keys** — key management overhead
- **Workload Identity** — federation costs
- **Policy Bindings** — policy evaluation overhead
- **Audit Logging** — logging storage costs

Optimizing these costs can reduce IAM overhead by 30-50% for most workloads.

### Cost Drivers

| Resource | Pricing Model | Typical Monthly Cost | Optimization Potential |
|----------|---------------|---------------------|------------------------|
| Service Account Keys | Free (management) | $0 | 100% (remove unused) |
| Workload Identity | Free (federation) | $0 | N/A |
| Policy Bindings | Free (evaluation) | $0 | N/A |
| Audit Logging | $0.50/GB | $50-500 | 40-60% |

## IAM Cost Model

### Pricing Breakdown

| Resource | Cost Component | Rate |
|----------|---------------|------|
| Service Accounts | Free | $0 |
| Service Account Keys | Free | $0 |
| Workload Identity | Free | $0 |
| Policy Bindings | Free | $0 |
| Audit Logging | Per GB | $0.50/GB |
| Policy Intelligence | Free | $0 |

### Cost Calculator

```bash
echo "10GB audit logs: $(echo "scale=2; 10 * 0.50" | bc) = $5.00/month"
echo "100GB audit logs: $(echo "scale=2; 100 * 0.50" | bc) = $50.00/month"
```

## Service Account Cost Analysis

### Key Inventory

```bash
# List all service accounts with key counts
gcloud iam service-accounts list --format="json" | \
  jq '.accounts[] | {email: .email, name: .name}' | \
  jq -s '.' | \
  jq '.[] | {
    email: .email,
    keyCount: (gcloud iam service-accounts keys list --iam-account=.email --format="json" | jq '.keys | length')
  }'
```

### Key Age Analysis

```bash
# Analyze key age — correct field names: .keys[].validAfterTime, .keys[].validBeforeTime, .keys[].keyType
gcloud iam service-accounts keys list \
  --iam-account=my-sa@my-project.iam.gserviceaccount.com \
  --format="json" | \
  jq '.keys[] | {
    keyId: .name,
    createdAt: .validAfterTime,
    ageDays: ((now - (.validAfterTime | fromdateiso8601)) / 86400 | floor),
    status: .keyType
  }'
```

### Unused Key Detection

```bash
# Detect unused keys — correct field names: .keys[].name, .keys[].keyType
gcloud iam service-accounts keys list \
  --iam-account=my-sa@my-project.iam.gserviceaccount.com \
  --format="json" | \
  jq '.keys[] | select(.keyType == "USER_MANAGED") | .name' | \
  while read -r key; do
    LAST_USED=$(gcloud logging read "protoPayload.request.name=$key" --limit=1 --format="value(timestamp)" 2>/dev/null)
    if [ -z "$LAST_USED" ]; then
      echo "Unused key: $key"
    fi
  done
```

## Workload Identity Federation Savings

### Federation Analysis

```bash
# List workload identity pools
gcloud iam workload-identity-pools list --format="table(name,displayName)"

# Analyze federation usage
gcloud logging read "protoPayload.methodName=google.iam.credentials.v1.GenerateAccessToken" \
  --limit=100 --format="json" | \
  jq 'map(.resource.labels) | group_by(.pool_id) | map({pool: .[0].pool_id, count: length})'
```

### Federation vs Key Comparison

```bash
echo "Service Account Key management:"
echo "  - Key rotation overhead: ~2 hours/month"
echo "  - Security risk: Medium"
echo "  - Cost: \$0 (but operational overhead)"
echo ""
echo "Workload Identity Federation:"
echo "  - No key management"
echo "  - Security risk: Low"
echo "  - Cost: \$0 (and lower operational overhead)"
```

## Role Optimization

### Role Usage Analysis

```bash
# Analyze role usage via Cloud Audit Logs
bq query --use_legacy_sql=false \
  "SELECT
    protoPayload.principalEmail as user,
    protoPayload.resourceName as resource,
    COUNT(*) as access_count
  FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    AND protoPayload.methodName LIKE 'getIamPolicy%'
  GROUP BY 1, 2
  ORDER BY access_count DESC"
```

### Unused Role Detection

```bash
# Detect unused roles
gcloud projects get-iam-policy "$CLOUDSDK_CORE_PROJECT" --format="json" | \
  jq '.bindings[] | {
    role: .role,
    members: .members,
    memberCount: (.members | length)
  }' | \
  jq 'select(.memberCount == 1)'
```

## Unused Permission Cleanup

### Permission Audit

```bash
# Audit permissions
gcloud iam roles describe roles/viewer --format="json" | \
  jq '.includedPermissions | length'

# List all roles
gcloud iam roles list --format="table(name,title,stage)"
```

### Custom Role Optimization

```bash
# Analyze custom roles — correct field: .roles[].stage, not .[].stage
gcloud iam roles list --format="json" | \
  jq '.roles[] | select(.stage == "GA")' | \
  jq '{name: .name, permissions: (.includedPermissions | length)}'
```

## Cost Monitoring

### Audit Log Cost Analysis

```bash
# Analyze audit log costs
bq query --use_legacy_sql=false \
  "SELECT
    log_name,
    COUNT(*) as entry_count,
    COUNT(*) * 0.5 / 1024 as estimated_cost_gb
  FROM \`my_project.logging_bucket.cloudaudit.googleapis.com_activity\`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY 1
  ORDER BY entry_count DESC"
```

### Budget Alerts

```bash
# Create IAM budget alert
gcloud billing budgets create \
  --billing-account="$BILLING_ACCOUNT_ID" \
  --display-name="IAM Audit Log Budget" \
  --budget-amount=100 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100
```

## Troubleshooting High Costs

### Common Cost Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High audit log costs | Excessive logging | Filter audit logs |
| Key management overhead | Too many keys | Rotate and remove unused |
| Policy complexity | Too many bindings | Simplify IAM policies |
| Permission bloat | Over-privileged roles | Use least privilege |

### Cost Investigation

```bash
# Find audit log volume
bq query --use_legacy_sql=false \
  "SELECT
    COUNT(*) as total_entries,
    SUM(size) / 1073741824 as size_gb
  FROM \`my_project.logging_bucket._AllLogs\`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)"
```

## See Also

- [IAM Monitoring](../monitoring.md)
- [IAM Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud FinOps Guide](https://cloud.google.com/architecture/cost-optimization)
