<!---
load_condition: "[架构评审时加载]"
token_cost_estimate: "~700 tokens"
dependencies: []
--->

# Well-Architected Assessment — Security Command Center

## Pillar Summary

| Pillar | Controls | Evidence |
|--------|----------|----------|
| Security | Least-privilege SCC roles, org/folder hierarchy scoping, VPC-SC integration, audit log review, finding state transitions | IAM checks, sanitized traces, muted finding review |
| Stability | Notification configs as DR (multi-region Pub/Sub), BigQuery export as cold backup, idempotent mute configs, finding state validation | Notification config topic review, BQ dataset review, mute config filter |
| Cost | Tier-aware pricing, finding cardinality, BigQuery export storage cost, container/anomaly detector selection | Tier comparison, BQ dataset size, detector enablement |
| Efficiency | Filtered list with `--filter`, pagination, batch finding updates, project/folder scoping | Filter expressions, page_size tuning |
| Performance | Indexing by `event_time`, state=ACTIVE prefilter, parent resource scoping, dataset partition pruning for exports | Finding query patterns, BQ export partition strategy |

## Security

| Check | Method | Target |
|-------|--------|--------|
| SCC roles least privilege | Verify roles at the minimum required scope | No org-level admin unless required |
| Mute config review | Audit all mute configs quarterly | No critical findings silently suppressed |
| Notification config topic IAM | Check SCC service agent has only publisher on topic | No overprivileged IAM on notification topic |
| BigQuery export dataset IAM | Check SCC service agent has only data editor on dataset | No overprivileged IAM on export dataset |
| Audit log review | Query audit logs for SCC mutations | All mute/notification/BQ export changes approved |
| Finding state transitions | Verify state changes are intentional and not silencing live threats | State change trace reviewed |
| VPC-SC perimeter | [VERIFY: whether SCC API supports VPC-SC perimeters — check current docs] | SCC API access restricted to authorized perimeters |

## Stability

- Validate notification configs route to multi-region or redundant Pub/Sub topics.
- Validate BQ export dataset has sufficient retention for compliance and audit needs.
- Validate mute config filters do not unintentionally suppress critical/high severity findings.
- For finding state changes, always describe the finding first and validate the target state before applying.
- Re-enable disabled custom modules promptly to maintain detection coverage.

## Cost

- Review SCC tier and detector set; disable unused Premium detectors if not needed.
- Monitor BigQuery export dataset size; set table expiration if historical data retention is limited.
- Review mute config effectiveness; overly broad mute rules suppress findings that would otherwise justify their cost.
- [VERIFY: exact pricing model for SCC Standard/Premium/Enterprise — check current docs]

## Efficiency

- Use `state="ACTIVE"` as a default filter to reduce result set.
- Use `severity` and `category` filters to narrow scope for triage operations.
- For batch finding updates, use the SDK to process findings in pages of 100.
- Scope mute configs and notification configs at the folder level when coverage spans multiple projects.
- Use BigQuery exports for long-term trend analysis rather than real-time list queries for historical views.

## Performance

- SCC findings are indexed by `event_time` and `state`; use these in filters for best query performance.
- For large finding sets, use `page_size` of 100-500 and follow `nextPageToken` for pagination.
- BigQuery export writes use partitioned tables by finding event time; use partition pruning in queries to reduce scan cost.
- Custom module execution frequency is managed by SCC; no tuning available via this skill.
- Resource value configs affect severity scoring but do not impact query performance.

## FinOps Considerations

- SCC tier pricing varies significantly between Standard (free), Premium, and Enterprise.
- BigQuery export storage costs scale with finding volume and retention period.
- Unused or overly broad mute configs reduce the value of SCC; review quarterly.
- Notification config Pub/Sub message volume scales with finding count and filter specificity.