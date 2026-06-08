---
name: billing-well-architected-assessment
description: Google Cloud Architecture Framework five-pillar assessment for Cloud Billing operations

<!---
load_condition: "[架构评估时加载]"
token_cost_estimate: "~1200 tokens"
dependencies: []
--->
---

# Well-Architected Assessment — Cloud Billing

## 1. Security

| Principle | Assessment | Recommendation |
|-----------|------------|----------------|
| Least privilege IAM | Billing roles are coarse-grained (viewer, admin, budgetAdmin, costsManager) | Grant at billing-account level, not org level; use conditions for project-scoped access |
| Credential protection | Access tokens and SA keys can expose billing data | Mask all credentials in logs; use ADC, never print token values |
| Export data access | BigQuery billing exports contain detailed cost data | Restrict dataset access to billing analysts only; enable audit logging on export tables |
| Budget alert sensitivity | Budget threshold notifications may reveal spending patterns | Use Pub/Sub with authorized subscribers; avoid exposing budget amounts in public channels |
| Audit logging | Billing account changes should be traceable | Enable Cloud Audit Logs for billing account; review Admin Activity logs regularly |

## 2. Stability

| Principle | Assessment | Recommendation |
|-----------|------------|----------------|
| Budget alert reliability | Budgets evaluated daily; alerts may have up to 24h delay | Use multiple threshold levels (50%, 80%, 100%); combine current + forecasted spend bases |
| Export pipeline resilience | Billing export is a fire-and-forget pipeline; no built-in retry | Monitor export table freshness; alert if no new data for > 48h |
| Multi-channel notification | Single Pub/Sub topic is a SPOF for budget alerts | Configure both Pub/Sub and email notifications; add dead-letter topic for undelivered messages |
| Project unlink impact | Unlinking disables all billable services immediately | Require explicit confirmation; suggest pre-unlink resource inventory |
| Billing account closure | Closed accounts cannot be reopened without support | Treat account closure as irreversible; require multi-step confirmation |

### Emergency Recovery Runbook

| Scenario | Recovery Steps | RTO |
|----------|---------------|-----|
| Budget alert not firing | 1) Describe budget; 2) Check threshold rules; 3) Verify Pub/Sub topic exists and has subscribers; 4) Test with manual Pub/Sub message | < 30 min |
| Export data missing | 1) Check export config exists; 2) Verify BigQuery dataset permissions; 3) Wait 24-48h for initial data; 4) Recreate export if needed | 24-48h |
| Accidental project unlink | 1) Re-link project to billing account; 2) Restart stopped resources; 3) Verify services resume | < 1h |
| Budget deleted accidentally | 1) Recreate budget with same config; 2) Verify threshold rules match; 3) No data recovery needed (budgets are configuration-only) | < 15 min |

## 3. Cost

| Principle | Assessment | Recommendation |
|-----------|------------|----------------|
| Budget right-sizing | Budgets should reflect actual spending patterns | Set budget at 110-120% of average monthly spend; review quarterly |
| Export cost | BigQuery storage costs for billing data | Use partitioned tables; set retention policy (e.g., 13 months); monitor dataset size |
| Alert noise reduction | Too many threshold rules cause alert fatigue | Use 3 thresholds max: 50% (warning), 80% (forecast), 100% (critical) |
| Pricing query efficiency | SKU queries can be expensive if unfiltered | Filter by service and region; cache results for repeated queries |
| Free tier awareness | Some services have free-tier usage | Budget scope should exclude free-tier credits if not relevant |

## 4. Efficiency

| Principle | Assessment | Recommendation |
|-----------|------------|----------------|
| Budget automation | Budgets should be created programmatically for multi-project setups | Use Terraform or gcloud scripts; apply consistent naming convention |
| Export pipeline automation | Manual export setup is error-prone | Automate export creation via Terraform `google_billing_budget` resource |
| Bulk project linking | Linking projects one-by-one is inefficient | Use `gcloud billing projects link` in a loop; validate with `gcloud billing projects list` |
| Idempotent budget management | Duplicate budgets waste quota and cause confusion | Check existing budgets by display name before create; use etag for safe updates |
| Pricing data caching | Repeated SKU queries waste API quota | Cache pricing data locally; refresh weekly |

## 5. Performance

| Principle | Assessment | Recommendation |
|-----------|------------|----------------|
| Budget evaluation latency | Budgets evaluated daily; not real-time | Set forecast-based thresholds for early warning; do not rely on budgets for real-time cost control |
| Export data freshness | Standard export: daily; Detailed export: hourly | Use detailed export for near-real-time cost monitoring |
| API rate limits | Billing APIs have per-minute quotas | Batch operations; use exponential backoff for 429 responses |
| BigQuery query performance | Large export tables can be slow to query | Use partitioned tables; filter by date range; create materialized views for common queries |
| Alert delivery latency | Pub/Sub delivers within seconds; email may have minutes of delay | Use Pub/Sub for programmatic alerting; email for human notification |

## Assessment Summary

| Pillar | Score (1-5) | Key Gap |
|--------|:-----------:|---------|
| Security | 4 | Coarse-grained IAM roles; use conditions for fine-grained access |
| Stability | 3 | Export pipeline has no built-in retry; budget alert delay up to 24h |
| Cost | 4 | Budget right-sizing requires manual review |
| Efficiency | 4 | Bulk operations supported; Terraform automation recommended |
| Performance | 3 | Budget evaluation is daily-only; no real-time cost control |
