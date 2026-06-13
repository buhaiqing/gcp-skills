# FinOps Cost Optimization — Google Cloud Billing

> Provides finance and operations teams with a complete guide to optimizing costs associated with Google Cloud Billing — committed use discounts, sustained use optimization, cost allocation, and budget automation.

## Table of Contents

1. [Overview](#overview)
2. [Cost Model](#cost-model)
3. [Committed Use Discounts](#committed-use-discounts)
4. [Sustained Use Optimization](#sustained-use-optimization)
5. [Cost Allocation](#cost-allocation)
6. [Budget Automation](#budget-automation)
7. [Troubleshooting High Costs](#troubleshooting-high-costs)
8. [See Also](#see-also)

## Overview

Google Cloud Billing optimization focuses on reducing costs through:

- **Committed Use Discounts (CUDs)** — 1-3 year commitments for up to 57% savings
- **Sustained Use Discounts** — Automatic discounts for long-running workloads
- **Cost Allocation** — Track and attribute costs to teams/projects
- **Budget Automation** — Automated controls to prevent overspend

### Savings Potential

| Optimization | Savings | Commitment | Best For |
|--------------|---------|------------|----------|
| 1-year CUD | Up to 28% | 1 year | Predictable workloads |
| 3-year CUD | Up to 57% | 3 years | Long-term workloads |
| Sustained Use | Up to 30% | None | Always-on resources |
| Preemptible/Spot | Up to 80% | None | Fault-tolerant workloads |
| Right-sizing | 20-40% | None | Over-provisioned resources |

## Cost Model

### Pricing Components

| Resource | Pricing Model | Optimization |
|----------|---------------|--------------|
| Compute Engine | Per-hour + sustained use | CUDs, right-sizing |
| Cloud SQL | Per-hour + storage | CUDs, storage tiering |
| GCS | Per-GB storage + operations | Lifecycle policies |
| BigQuery | Per-TB queries + storage | Flat-rate slots, partitioning |
| Networking | Per-GB egress | CDN, caching |

### Cost Calculator

```bash
# Estimate compute cost
gcloud compute instances pricing --zone=us-central1-a | grep "n1-standard-1"

# Calculate CUD savings
echo "3-year CUD savings: $(echo "scale=2; 1000 * 0.57" | bc) = $570/month"
```

## Committed Use Discounts

### CUD Analysis

```bash
# List active CUDs
gcloud compute reservations list --format="table(name,zone,status,commitmentPlan)"

# Analyze CUD utilization
gcloud compute reservations describe my-reservation --zone=us-central1-a \
  --format="json" | jq '.specificReservation.count, .specificReservation.inUseCount'
```

### CUD Recommendations

```bash
# Get CUD recommendations
gcloud billing budgets suggest --billing-account=$BILLING_ACCOUNT_ID \
  --format="table(suggestion,estimatedSavings)"
```

### CUD Purchase

```bash
# Purchase 1-year CUD
gcloud compute reservations create my-cud \
  --zone=us-central1-a \
  --commitment-plan=YEAR \
  --count=10 \
  --machine-type=n1-standard-1

# Purchase 3-year CUD
gcloud compute reservations create my-3yr-cud \
  --zone=us-central1-a \
  --commitment-plan=THREE_YEARS \
  --count=10 \
  --machine-type=n1-standard-1
```

## Sustained Use Optimization

### Sustained Use Analysis

```bash
# Analyze sustained use discounts
gcloud compute instances list --format="json" | \
  jq '.[] | {name, machineType, status, scheduling}' | \
  jq 'select(.status == "RUNNING")' | \
  jq 'select(.scheduling.automaticRestart == true)'
```

### Always-On Optimization

```bash
# Find always-on instances
gcloud compute instances list --format="table(name,zone,status,scheduling.automaticRestart)" | \
  grep "true" | grep "RUNNING"
```

## Cost Allocation

### Label-Based Allocation

```bash
# Set labels for cost allocation
gcloud compute instances add-labels my-instance \
  --zone=us-central1-a \
  --labels=team=backend,project=webapp,cost-center=engineering

# Query costs by label
bq query --use_legacy_sql=false \
  "SELECT
    labels.value as team,
    SUM(cost) as total_cost
  FROM \`my_project.billing_dataset.gcp_billing_export_v1_XXXXXX\`
  WHERE labels.key = 'team'
  GROUP BY 1
  ORDER BY total_cost DESC"
```

### Project-Based Allocation

```bash
# List costs by project
bq query --use_legacy_sql=false \
  "SELECT
    project.name,
    SUM(cost) as total_cost
  FROM \`my_project.billing_dataset.gcp_billing_export_v1_XXXXXX\`
  GROUP BY 1
  ORDER BY total_cost DESC"
```

## Budget Automation

### Auto-Scale Down

```bash
#!/bin/bash
# auto-scale-down.sh

# Scale down non-production instances during off-hours
HOUR=$(date +%H)
if [ $HOUR -ge 20 ] || [ $HOUR -le 6 ]; then
  gcloud compute instances list --format="value(name,zone)" | \
  while read -r name zone; do
    if [[ $name == *"dev"* ]] || [[ $name == *"test"* ]]; then
      echo "Stopping: $name"
      gcloud compute instances stop $name --zone=$zone
    fi
  done
fi
```

### Auto-Delete Unused Resources

```bash
#!/bin/bash
# auto-delete-unused.sh

# Delete unattached disks older than 30 days
gcloud compute disks list --format="json" | \
  jq '.[] | select(.users == [])' | \
  jq -r '.name + " " + .zone' | \
while read -r name zone; do
  AGE=$(gcloud compute disks describe $name --zone=$zone --format="value(creationTimestamp)")
  echo "Deleting unattached disk: $name"
  gcloud compute disks delete $name --zone=$zone
done
```

## Troubleshooting High Costs

### Common Cost Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High compute costs | Over-provisioning | Right-size instances |
| Unexpected egress | Cross-region traffic | Use CDN, optimize placement |
| Storage cost spike | Uncontrolled growth | Implement lifecycle policies |
| CUD underutilization | Wrong commitment | Review and adjust CUDs |

### Cost Investigation

```bash
# Find most expensive resources
bq query --use_legacy_sql=false \
  "SELECT
    service.description,
    sku.description,
    SUM(cost) as total_cost
  FROM \`my_project.billing_dataset.gcp_billing_export_v1_XXXXXX\`
  WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY 1, 2
  ORDER BY total_cost DESC
  LIMIT 20"
```

## See Also

- [Billing Monitoring](../monitoring.md)
- [Billing Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud FinOps Guide](https://cloud.google.com/architecture/cost-optimization)
