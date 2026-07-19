> Load Balancing cost optimization runbook for agents. Mirror of `gcp-gcs-ops/references/advanced/finops-storage-cost.md`. Use `gcloud` to detect waste; never fabricate exact prices (use relative tiers).

# FinOps — Load Balancing Cost Optimization

## Table of Contents
- [Overview](#overview)
- [Cost Drivers](#cost-drivers)
- [Idle & Waste Detection](#idle--waste-detection)
- [Sizing & Commitment Recommendations](#sizing--commitment-recommendations)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

## Overview

GCP LB bills per forwarding rule (hourly), per provisioned NEG, and per data processed (GB). Largest levers: deleting unused forwarding rules, consolidating backends, and choosing the right LB type (classic vs Envoy/advanced).

### Cost Drivers

| Driver | Billing Unit | Lever |
|--------|--------------|-------|
| Forwarding rule | hourly per rule | Delete unused rules |
| Provisioned NEG | hourly per NEG | Consolidate backends |
| Data processed | GB | Keep traffic in-region |
| LB type premium | fixed premium | Use appropriate tier (HTTP vs TCP) |

## Idle & Waste Detection

```bash
# Forwarding rules with no backend service attached (waste)
gcloud compute forwarding-rules list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,region,target)"

# Backend services with 0 healthy backends (orphan)
gcloud compute backend-services list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,backends)"

# Unused NEGs (no attached backend service)
gcloud compute network-endpoint-groups list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,zone,size)" \
  | jq -r '.[] | select(.size == 0) | .name'

# Global forwarding rules (cross-region premium) with low traffic
gcloud compute forwarding-rules list --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,target)"
```

## Sizing & Commitment Recommendations

```bash
# Delete unused forwarding rule (HALT: confirm no traffic)
gcloud compute forwarding-rules delete RULE --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --quiet=false

# Consolidate multiple backend services behind one URL map
gcloud compute url-maps add-path-matcher URL_MAP \
  --path-matcher-name=pm --default-service=BACKEND \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Remove empty NEGs
gcloud compute network-endpoint-groups delete NEG --zone=ZONE \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

| Scenario | Action | Est. Savings |
|----------|--------|--------------|
| Forwarding rule, 0 traffic | Delete | 100% of rule cost |
| Empty NEG | Delete | 100% of NEG cost |
| Many small LBs | Consolidate via URL map | Rule + mgmt overhead |
| Cross-region premium unused | Use regional LB | Lower premium |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| LB bill high, low traffic | Orphan forwarding rules | Run detection query, delete |
| NEG charges with no endpoints | Forgotten test NEG | Delete empty NEG |
| Premium tier unused | Global LB where regional suffices | Switch to regional |

## See Also
- [gcp-gce-ops finops-compute-cost.md](../gcp-gce-ops/references/advanced/finops-compute-cost.md)
- [well-architected-assessment.md](../gcp-lb-ops/references/well-architected-assessment.md) §2.3
