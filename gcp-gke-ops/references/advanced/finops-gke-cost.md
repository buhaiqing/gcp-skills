> GKE cost optimization runbook for agents. Mirror of `gcp-gcs-ops/references/advanced/finops-storage-cost.md`. Use `gcloud` to detect waste; never fabricate exact prices (use relative tiers).

# FinOps — GKE Cost Optimization

## Table of Contents
- [Overview](#overview)
- [Cost Drivers](#cost-drivers)
- [Idle & Waste Detection](#idle--waste-detection)
- [Sizing & Commitment Recommendations](#sizing--commitment-recommendations)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

## Overview

GKE bills the underlying Compute Engine nodes plus cluster management fee (Autopilot bundles both). Largest levers: node auto-provisioning, Cluster Autoscaler, Vertical/Horizontal Pod Autoscaler, Autopilot mode, and CUD on node pools.

### Cost Drivers

| Driver | Billing Unit | Lever |
|--------|--------------|-------|
| Node pool VMs | vCPU-hour / GB-hour | CUD; Spot node pools; right-size |
| Cluster mgmt fee | $/cluster-hour | Autopilot removes node mgmt overhead |
| Autopilot vCPU/mem | vCPU-hour / GB-hour (pod-level) | Pay per pod, not per node |
| Egress | GB | In-cluster / private traffic |
| Idle nodes | node-hour | Scale-to-zero node pools |

## Idle & Waste Detection

```bash
# Node pools with low CPU allocation (over-provisioned)
gcloud container node-pools list --cluster=CLUSTER --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,config.machineType,initialNodeCount,autoscaling)"

# Pods requesting far more than used (VPA recommender)
gcloud recommender recommendations list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --location=CLUSTER_LOCATION \
  --recommender=google.kubernetes.engine.pod.VerticalPodAutoscalerRecommender \
  --format="json(recommendationId,content.overview)"

# Unused node pools (0 pods scheduled over 7d) — check autoscaler status
gcloud container clusters describe CLUSTER --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(autoscaling,nodePools.autoscaling)"
```

## Sizing & Commitment Recommendations

```bash
# Enable node auto-provisioning + Cluster Autoscaler (scale-to-zero)
gcloud container clusters update CLUSTER --region=REGION \
  --enable-autoscaling --min-nodes=0 --max-nodes=10 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Convert batch pool to Spot
gcloud container node-pools update BATCH_POOL --cluster=CLUSTER --region=REGION \
  --spot --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Enable VPA (recommendation mode, non-disruptive)
gcloud container clusters update CLUSTER --region=REGION \
  --enable-vertical-pod-autoscaling --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Consider Autopilot for new clusters (per-pod billing, no node mgmt fee)
gcloud container clusters create-auto CLUSTER --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

| Scenario | Action | Est. Savings |
|----------|--------|--------------|
| Idle node pool | Enable CA min=0 | Idle node cost → 0 |
| Batch/fault-tolerant | Spot node pool | 60–91% on pool |
| Steady baseline | CUD on node pool | 57% / 70% |
| Over-requested pods | VPA right-size | 20–40% pod resources |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Nodes never scale down | Pod disruption budget too strict | Relax PDB / add CA scale-down timeout |
| CUD unused | Node pool family mismatch | Align machine type to commitment |
| High mgmt fee | Many small zonal clusters | Consolidate / use Autopilot |
| Spot evictions | No fallback | Mix Spot + on-demand pools |

## See Also
- [gcp-gce-ops finops-compute-cost.md](../gcp-gce-ops/references/advanced/finops-compute-cost.md)
- [well-architected-assessment.md](../gcp-gke-ops/references/well-architected-assessment.md) §2.3
