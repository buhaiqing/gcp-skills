> Compute Engine cost optimization runbook for agents. Mirror of `gcp-gcs-ops/references/advanced/finops-storage-cost.md`. Use `gcloud` to detect waste; never fabricate exact prices (use relative tiers).

# FinOps — Compute Engine Cost Optimization

## Table of Contents
- [Overview](#overview)
- [Cost Drivers](#cost-drivers)
- [Idle & Waste Detection](#idle--waste-detection)
- [Sizing & Commitment Recommendations](#sizing--commitment-recommendations)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

## Overview

Compute Engine bills by machine type (vCPU + memory), persistent disk, and network egress. Largest levers: committed use discounts (CUD), Spot/preemptible, right-sizing, and deleting idle resources.

### Cost Drivers

| Driver | Billing Unit | Lever |
|--------|--------------|-------|
| vCPU + memory | vCPU-hour / GB-hour | CUD 1yr ~57%, 3yr ~70% off; Spot 60–91% off |
| Persistent disk | GB-month + snapshot GB-month | Use balanced/standard HDD; delete orphan disks |
| Sustained use | automatic discount | Steady 24/7 workloads get automatic discount |
| External IP | hourly when unattached | Release unused reserved IPs |
| Network egress | GB | Keep traffic in-region / private |

## Idle & Waste Detection

```bash
# Instances with <5% CPU over 7 days (idle)
gcloud monitoring query \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  "fetch gce_instance | metric 'compute.googleapis.com/instance/cpu/utilization' | within 7d | every 1d | group_by (resource.instance_id), (mean_utilization: mean(value.utilization))" \
  --format="json" | jq -r '.[] | select(.mean_utilization < 0.05) | .resource.instance_id'

# Unattached persistent disks (waste)
gcloud compute disks list --filter="status=READY AND users=()" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,sizeGb,zone)"

# Reserved static IPs not bound to any instance
gcloud compute addresses list --filter="status=RESERVED" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,address,region)"

# Preemptible/Spot eligibility: list always-on standard instances
gcloud compute instances list --filter="scheduling.preemptible=false" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,machineType,zone)"
```

## Sizing & Commitment Recommendations

```bash
# Right-size: compare provisioned vs recommended (Recommender API)
gcloud recommender recommendations list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location=global --recommender=google.compute.instance.MachineTypeRecommender \
  --format="json(recommendationId,content.overview,primaryImpact)"

# Purchase 1-year CUD (regional, flexible) — DRY-RUN preview first
gcloud compute commitments describe REGION --format="json" 2>/dev/null || echo "no commitment yet"
# Actual purchase (HALT: requires finance confirmation):
# gcloud compute commitments create COMMIT_ID --region=REGION --resources=vcpu=10,memory=40GB --plan=twelve-month

# Convert fault-tolerant workload to Spot
gcloud compute instances set-scheduling INSTANCE --preemptible \
  --zone=ZONE --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

| Scenario | Action | Est. Savings |
|----------|--------|--------------|
| CPU <5% 7d | Stop or downsize | 100% of instance cost |
| Steady 24/7 | 1yr/3yr CUD | 57% / 70% |
| Fault-tolerant batch | Spot | 60–91% |
| Orphan disk | Delete | 100% of disk cost |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| High bill, low usage | Idle always-on instances | Stop / downsize per detection query |
| CUD not applied | Flexible CUD covers only matching region/type | Align instance family to commitment |
| Snapshot creep | Unmanaged snapshot chains | Set lifecycle; delete stale |
| Egress spike | Cross-region traffic | Co-locate; use VPC peering |

## See Also
- [gcp-gcs-ops finops-storage-cost.md](../gcp-gcs-ops/references/advanced/finops-storage-cost.md)
- [gcp-bigquery-ops finops-bigquery-cost.md](../gcp-bigquery-ops/references/advanced/finops-bigquery-cost.md)
- [well-architected-assessment.md](../gcp-gce-ops/references/well-architected-assessment.md) §2.3
