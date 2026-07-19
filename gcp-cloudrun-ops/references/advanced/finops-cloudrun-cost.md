> Cloud Run cost optimization runbook for agents. Mirror of `gcp-gcs-ops/references/advanced/finops-storage-cost.md`. Use `gcloud` to detect waste; never fabricate exact prices (use relative tiers).

# FinOps — Cloud Run Cost Optimization

## Table of Contents
- [Overview](#overview)
- [Cost Drivers](#cost-drivers)
- [Idle & Waste Detection](#idle--waste-detection)
- [Sizing & Commitment Recommendations](#sizing--commitment-recommendations)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

## Overview

Cloud Run bills per vCPU-second, GB-second, requests, and egress. Largest levers: `min-instances=0` for sporadic traffic, right-sizing CPU/memory, concurrency tuning, and revision traffic cleanup.

### Cost Drivers

| Driver | Billing Unit | Lever |
|--------|--------------|-------|
| vCPU allocation | vCPU-second | Right-size; concurrency |
| Memory allocation | GB-second | Right-size |
| Requests | per million | Reduce idle invocations |
| Min instances | always-on vCPU/mem | Set 0 for non-critical |
| Egress | GB | In-region traffic |

## Idle & Waste Detection

```bash
# Services with min-instances > 0 but low traffic (idle always-on)
gcloud run services list --platform=managed \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(metadata.name)" \
  | jq -r '.[] .metadata.name' \
  | while read s; do
      mi=$(gcloud run services describe "$s" --platform=managed \
        --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="value(spec.template.metadata.annotations.autoscaling.knative.dev/minScale)" 2>/dev/null)
      [ "${mi:-0}" != "0" ] && echo "$s minScale=$mi"
    done

# Revisions receiving 0 traffic (stale)
gcloud run revisions list --service=SERVICE --platform=managed \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json(metadata.name,status.traffic)"

# Over-provisioned memory (right-size via recommender)
gcloud recommender recommendations list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --location=REGION \
  --recommender=google.run.service.Recommender --format="json(recommendationId,content.overview)"
```

## Sizing & Commitment Recommendations

```bash
# Set min-instances=0 for sporadic workloads (saves idle cost)
gcloud run services update SERVICE --platform=managed \
  --min-instances=0 --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Right-size memory + raise concurrency (fewer instances)
gcloud run services update SERVICE --platform=managed \
  --memory=256Mi --concurrency=80 --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Route all traffic to latest revision, retire stale ones
gcloud run services update-traffic SERVICE --platform=managed \
  --to-latest --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Delete stale revision (HALT: confirm 0 traffic)
gcloud run revisions delete REVISION --platform=managed \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

| Scenario | Action | Est. Savings |
|----------|--------|--------------|
| min-instances>0, idle | Set 0 | 100% idle cost |
| Memory over-provisioned | Halve memory | ~50% compute cost |
| Low concurrency | Raise to 80 | 30–70% fewer instances |
| Stale revision | Retire | Frees quota, avoids confusion |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Always-on cost | min-instances>0 | Set 0 unless latency-critical |
| Cold start complaints | min=0 + low CPU | Raise min to 1 for critical paths |
| High GB-second | Over-allocated memory | Right-size via recommender |
| Egress spike | Cross-region calls | Co-locate dependencies |

## See Also
- [gcp-cloudfunctions-ops finops-functions-cost.md](../gcp-cloudfunctions-ops/references/advanced/finops-functions-cost.md)
- [well-architected-assessment.md](../gcp-cloudrun-ops/references/well-architected-assessment.md) §2.3
