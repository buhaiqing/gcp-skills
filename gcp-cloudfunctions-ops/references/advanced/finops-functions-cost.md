> Cloud Functions cost optimization runbook for agents. Mirror of `gcp-gcs-ops/references/advanced/finops-storage-cost.md`. Use `gcloud` to detect waste; never fabricate exact prices (use relative tiers).

# FinOps — Cloud Functions Cost Optimization

## Table of Contents
- [Overview](#overview)
- [Cost Drivers](#cost-drivers)
- [Idle & Waste Detection](#idle--waste-detection)
- [Sizing & Commitment Recommendations](#sizing--commitment-recommendations)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

## Overview

Cloud Functions (2nd gen, backed by Cloud Run) bills per invocation, GB-second, and CPU-second. Largest levers: `min-instances=0`, memory/CPU right-sizing, concurrency tuning, and deleting unused functions.

### Cost Drivers

| Driver | Billing Unit | Lever |
|--------|--------------|-------|
| Invocations | per million | Free tier: 2M/mo |
| Memory | GB-second | Right-size memory |
| CPU | GHz-second / vCPU-second | Right-size CPU |
| Min instances | always-on vCPU/mem | Set 0 for sporadic |
| Timeout | GB-second for slow runs | Set to actual max |

## Idle & Waste Detection

```bash
# Functions with 0 invocations in 30 days (waste)
gcloud functions list --gen2 --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name)" \
  | jq -r '.[] .name' | while read f; do
      cnt=$(gcloud monitoring query \
        --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
        "fetch cloud_function | metric 'cloudfunctions.googleapis.com/function/execution_count' | filter resource.function_name=='${f}' | within 30d | count" 2>/dev/null | jq -r '.[].pointData.value.int64Value // "0"')
      [ "${cnt:-0}" = "0" ] && echo "$f: 0 invocations/30d"
    done

# Functions with min-instances > 0 (idle always-on)
gcloud functions list --gen2 --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,serviceConfig.minInstanceCount)" \
  | jq -r '.[] | select(.serviceConfig.minInstanceCount > 0) | "\(.name) min=\(.serviceConfig.minInstanceCount)"'

# Over-provisioned memory
gcloud functions list --gen2 --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(name,serviceConfig.availableMemory)"
```

## Sizing & Commitment Recommendations

```bash
# Set min-instances=0 for sporadic workloads
gcloud functions deploy FUNC --gen2 --region=REGION \
  --min-instances=0 --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Right-size memory (halve if over-provisioned)
gcloud functions deploy FUNC --gen2 --region=REGION \
  --memory=256Mi --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Raise concurrency (stateless functions → fewer instances)
gcloud functions deploy FUNC --gen2 --region=REGION \
  --concurrency=16 --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Delete unused function (HALT: confirm 0 invocations)
gcloud functions delete FUNC --gen2 --region=REGION \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

| Scenario | Action | Est. Savings |
|----------|--------|--------------|
| 0 invocations 30d | Delete | 100% function cost |
| min-instances>0 idle | Set 0 | 100% idle cost |
| Memory over-provisioned | Halve | ~50% compute cost |
| Low concurrency | Raise to 16 | 30–70% fewer instances |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Idle always-on cost | min-instances>0 | Set 0 unless latency-critical |
| High GB-second | Over-allocated memory | Right-size |
| Long billing per call | Timeout too high | Set to actual max |
| Free tier exceeded | Steady high volume | Consider Cloud Run / CUD |

## See Also
- [gcp-cloudrun-ops finops-cloudrun-cost.md](../gcp-cloudrun-ops/references/advanced/finops-cloudrun-cost.md)
- [well-architected-assessment.md](../gcp-cloudfunctions-ops/references/well-architected-assessment.md) §2.3
