<!---
load_condition: "[用户询问监控/成本时加载]"
token_cost_estimate: "~700 tokens"
dependencies: []
--->

# Monitoring — Terraform Operations

## Observability Sources

| Source | Use |
|--------|-----|
| Terraform plan output | Create/destroy/modify counts, resource types affected |
| Terraform state | Current resource inventory, state file size |
| GCS state file versioning | State change history, backup count |
| Cloud Logging | Terraform service account audit logs (storage, GCP API calls) |
| Cloud Monitoring | GCP resource-level metrics from managed resources |
| DynamoDB lock table | Lock acquisition/release frequency, stale locks |

## Plan Frequency Tracking

```bash
# Count plans per environment (via Cloud Logging filter)
gcloud logging read \
  'resource.type="project" AND "terraform plan" AND "environments/{{user.environment}}"' \
  --project={{env.CLOUDSDK_CORE_PROJECT}} \
  --format=json | python3 -c "
import json, sys
entries = [json.loads(l) for l in sys.stdin]
print(f'Plans in last 7d: {len(entries)}')
print(f'Unique requestors: {len(set(e[\"jsonPayload\"][\"structPayload\"].get(\"principal\", \"unknown\") for e in entries if \"structPayload\" in e))}')
"

# State file size monitoring
gsutil du gs://tf-state-{{user.environment}}-{project}-terraform/environments/{{user.environment}}/default.tfstate
```

## Cost Estimation from Plan

Terraform plan shows resource changes but does not directly show cost. Estimate from resource types:

| Resource Type | Cost Driver | Estimation Method |
|---------------|-------------|-------------------|
| Compute instances | Machine type + GPU + preemptible | GCP Pricing Calculator |
| Cloud SQL | Tier + storage + HA | `gcloud sql tiers list` |
| GKE | Node pool size + load balancer | `gke-cost-estimator` |
| Cloud Storage | Storage + egress | Bucket lifecycle + egress rates |
| BigQuery | Storage + queries | `bq show` dataset storage |
| Memorystore | Instance tier | `gcloud redis instances list` |

## Recommended Alerts

| Alert | Signal | Response |
|-------|--------|----------|
| Plan frequency spike | > 10 plans/day in prod environment | Verify automated pipelines; check for excessive manual runs |
| State lock held > 30 min | Lock not released | Investigate stuck Terraform process; check DynamoDB lock table |
| Plan shows destroy in prod | Any destroy in prod plan | Trigger GCL review; require explicit acknowledgement |
| State file size growth | `default.tfstate` > 10 MB | Investigate large state; consider splitting into modules |
| Terraform service account permission denied | Permission error in plan | Grant required GCP role via `gcp-iam-ops` |
| GCS bucket versioning disabled | No state backup history | Enable GCS bucket versioning: `gsutil versioning set on gs://tf-state-{env}-{project}-terraform` |

## Dashboard Panels

- Terraform plan frequency by environment (dev/staging/prod).
- Resource count by type per environment.
- State file size trend per environment.
- Lock acquisition/release timeline.
- Apply/destroy event count (via Cloud Logging).
- GCP cost estimate delta from plan (manual calculation, not automatic).

## State File Safety

- GCS bucket must have **versioning enabled** — `gsutil versioning set on gs://tf-state-{env}-{project}-terraform`
- GCS bucket must have **lifecycle policy** — delete non-current versions after 90 days
- State file must have **server-side encryption** — GCS default encryption (AES-256) or CMEK
- State file must **never be world-readable** — `gsutil iam ch allUsers:objectViewer gs://tf-state-{env}-{project}-terraform` is NOT allowed