> Memorystore for Redis cost optimization runbook for agents. Mirror of `gcp-gcs-ops/references/advanced/finops-storage-cost.md`. Use `gcloud` to detect waste; never fabricate exact prices (use relative tiers).

# FinOps — Memorystore for Redis Cost Optimization

## Table of Contents
- [Overview](#overview)
- [Cost Drivers](#cost-drivers)
- [Idle & Waste Detection](#idle--waste-detection)
- [Sizing & Commitment Recommendations](#sizing--commitment-recommendations)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

## Overview

Memorystore bills per GB-hour by tier, plus read-replica and export-snapshot costs. Largest levers: tier selection (Basic vs Standard), right-sizing memory, and deleting unused instances.

### Cost Drivers

| Driver | Billing Unit | Lever |
|--------|--------------|-------|
| Instance capacity | $/GB-hour | Basic for dev, Standard for HA |
| Standard tier | ~2x Basic (primary+replica) | Use Basic where HA unneeded |
| Read replicas | $/replica-hour | Add only for read-heavy |
| Export snapshots | GB-month in GCS | Snapshot only when needed |
| Idle instance | GB-hour 24/7 | Delete unused |

## Idle & Waste Detection

```bash
# Instances with low memory usage (<40% — over-provisioned)
gcloud redis instances list --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,memorySizeGb,tier)" \
  | jq -r '.[] | "\(.name) \(.memorySizeGb)GB \(.tier)"'

# Memory usage ratio via monitoring
gcloud monitoring query \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  "fetch redis_instance | metric 'redis.googleapis.com/stats/memory/usage_ratio' | within 7d | group_by (resource.instance_id), (max_ratio: max(value.utilization))" \
  --format="json" | jq -r '.[] | select(.max_ratio < 0.4) | .resource.instance_id'

# Standard tier used for dev/test (over-pay for HA)
gcloud redis instances list --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,tier)" \
  | jq -r '.[] | select(.tier=="STANDARD_HA") | .name'
```

## Sizing & Commitment Recommendations

```bash
# Right-size: scale memory down (test on non-prod first)
gcloud redis instances update INSTANCE --region=REGION \
  --memory-size=4GB --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Downgrade dev/test from Standard to Basic (HALT: loses HA)
gcloud redis instances update INSTANCE --region=REGION \
  --tier=basic --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Delete unused instance (HALT: export first if needed)
gcloud redis instances delete INSTANCE --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

| Scenario | Action | Est. Savings |
|----------|--------|--------------|
| Memory <40% used | Scale down | Proportional GB-hour |
| Standard for dev/test | Downgrade Basic | ~50% instance cost |
| Unused instance | Delete | 100% instance cost |
| Frequent exports | Snapshot on schedule only | GCS storage cost |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| High bill, low usage | Over-provisioned memory | Scale down per detection |
| HA cost on dev | Standard tier | Downgrade to Basic |
| Snapshot creep | Unmanaged exports | Set retention; delete stale |
| Replica unused | Read replica idle | Remove replica |

## See Also
- [gcp-gce-ops finops-compute-cost.md](../gcp-gce-ops/references/advanced/finops-compute-cost.md)
- [well-architected-assessment.md](../gcp-memorystore-ops/references/well-architected-assessment.md) §2.3
