> Filestore cost optimization runbook for agents. Mirror of `gcp-gcs-ops/references/advanced/finops-storage-cost.md`. Use `gcloud` to detect waste; never fabricate exact prices (use relative tiers).

# FinOps — Filestore Cost Optimization

## Table of Contents
- [Overview](#overview)
- [Cost Drivers](#cost-drivers)
- [Idle & Waste Detection](#idle--waste-detection)
- [Sizing & Commitment Recommendations](#sizing--commitment-recommendations)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

## Overview

Filestore bills provisioned capacity (GiB-hour) by tier, plus backups and snapshots (GiB-month). Largest levers: tier selection, right-sizing capacity, and deleting stale backups/snapshots.

### Cost Drivers

| Driver | Billing Unit | Lever |
|--------|--------------|-------|
| Provisioned capacity | GiB-hour | BASIC_HDD cheapest; Enterprise premium |
| Tier premium | fixed multiplier | Use BASIC for non-prod |
| Backups | GiB-month | Delete stale |
| Snapshots | GiB-month | Cap count; delete old |
| Egress | GB | In-region mounts |

## Idle & Waste Detection

```bash
# Instances with low used capacity (<40% — over-provisioned)
gcloud filestore instances list --zone=ZONE \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,tier,fileShares)" \
  | jq -r '.[] | "\(.name) \(.tier) \(.fileShares[0].capacityGb)GB"'

# Used-space ratio via monitoring
gcloud monitoring query \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  "fetch filestore_instance | metric 'filestore.googleapis.com/instance/used_bytes' | within 7d | group_by (resource.instance_name), (max_used: max(value.used_bytes))" \
  --format="json" | jq -r '.[] | select(.max_used < 0.4 * (.capacityBytes // 1)) | .resource.instance_name'

# Stale backups (older than 30 days)
gcloud filestore backups list --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,createTime)" \
  | jq -r '.[] | select((now - (.createTime|fromdateiso8601)) > 2592000) | .name'

# Snapshot count per instance (cap 240)
gcloud filestore instances snapshots list --instance=INSTANCE --zone=ZONE \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,createTime)"
```

## Sizing & Commitment Recommendations

```bash
# Right-size: reduce file share capacity (increase only for most tiers; decrease where supported)
gcloud filestore instances update INSTANCE --zone=ZONE \
  --file-share=name=share1,capacity=512GB --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Use BASIC_HDD for non-prod (HALT: recreate — tier change needs new instance)
gcloud filestore instances create INSTANCE --zone=ZONE \
  --tier=BASIC_HDD --file-share=name=share1,capacity=1024GB \
  --network=name=default --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Delete stale backup (HALT: confirm not needed for DR)
gcloud filestore backups delete BACKUP --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Delete old snapshot
gcloud filestore instances snapshots delete SNAP --instance=INSTANCE --zone=ZONE \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

| Scenario | Action | Est. Savings |
|----------|--------|--------------|
| Capacity <40% used | Shrink share | Proportional GiB-hour |
| Regional/Enterprise for dev | BASIC_HDD | Tier premium removed |
| Stale backups >30d | Delete | GiB-month cost |
| Snapshot sprawl | Cap + prune | GiB-month cost |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| High bill, low usage | Over-provisioned capacity | Shrink file share |
| Premium tier on dev | Regional/Enterprise | Recreate as BASIC_HDD |
| Backup creep | No retention policy | Delete stale; set schedule |
| Snapshot limit hit | >240 snapshots | Prune oldest |

## See Also
- [gcp-gcs-ops finops-storage-cost.md](../gcp-gcs-ops/references/advanced/finops-storage-cost.md)
- [well-architected-assessment.md](../gcp-filestore-ops/references/well-architected-assessment.md) §2.3
