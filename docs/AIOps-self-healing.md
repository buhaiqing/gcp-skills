# AIOps Self-Healing Capabilities

Cross-skill AIOps self-healing layer for `gcp-skills`. Each product skill ships an
anomaly-detection + self-healing runbook under `references/advanced/`, wired to two
repo-wide shared assets and the GCL closed-loop feedback runner.

## Shared Assets (reference, do not duplicate)

| Asset | Path | Role |
|-------|------|------|
| Error Taxonomy | [docs/error-taxonomy.md](error-taxonomy.md) | Unified error codes, HALT vs retry classification |
| Cross-Skill Blast Radius | [docs/cross-skill-blast-radius.md](cross-skill-blast-radius.md) | Impact propagation across skills (merge/scale guardrails) |
| Closed-Loop Feedback | [gcp-gcl-runner-ops/trace_feedback.py](gcp-gcl-runner-ops/trace_feedback.py) | Critic scoring + trace replay |

## Self-Healing Contract

Every runbook follows the same four-phase loop:

```
detection → DRY-RUN preview → gate (human review / idempotency check) → idempotent apply
```

- **DRY-RUN first**: never mutate without a preview.
- **Idempotent**: probe target state; skip if already satisfied.
- **HALT**: destructive ops (failover, delete, IAM change, promote-replica) are blocked
  for auto-apply and escalated to human confirmation.
- **Credential masking**: per [AGENTS.md §0.1](AGENTS.md#01-credential-masking-security--mandatory) —
  paths/tokens masked as `****`, existence-only checks.

## Runbook Index

### Dimension 2 — Observability & Security
| Skill | Runbook |
|-------|---------|
| gcp-monitoring-ops | [aiops-alert-anomaly.md](gcp-monitoring-ops/references/advanced/aiops-alert-anomaly.md) |
| gcp-logging-ops | [aiops-log-pipeline-anomaly.md](gcp-logging-ops/references/advanced/aiops-log-pipeline-anomaly.md) |
| gcp-securitycenter-ops | [aiops-scc-anomaly.md](gcp-securitycenter-ops/references/advanced/aiops-scc-anomaly.md) |
| gcp-armor-ops | [adaptive-protection.md](gcp-armor-ops/references/advanced/adaptive-protection.md) |

### Dimension 3 — Data & App Platforms
| Skill | Runbook |
|-------|---------|
| gcp-cloudrun-ops | [aiops-cloudrun-anomaly.md](gcp-cloudrun-ops/references/advanced/aiops-cloudrun-anomaly.md) |
| gcp-composer-ops | [aiops-composer-anomaly.md](gcp-composer-ops/references/advanced/aiops-composer-anomaly.md) |
| gcp-memorystore-ops | [aiops-memorystore-anomaly.md](gcp-memorystore-ops/references/advanced/aiops-memorystore-anomaly.md) |
| gcp-cloudsql-ops | [aiops-query-insights.md](gcp-cloudsql-ops/references/advanced/aiops-query-insights.md) |
| gcp-gke-ops | [aiops-gke-anomaly.md](gcp-gke-ops/references/advanced/aiops-gke-anomaly.md) |
| gcp-pubsub-ops | [aiops-pubsub-anomaly.md](gcp-pubsub-ops/references/advanced/aiops-pubsub-anomaly.md) |
| gcp-bigquery-ops | [aiops-bigquery-anomaly.md](gcp-bigquery-ops/references/advanced/aiops-bigquery-anomaly.md) |

### Dimension 4 — Infrastructure
| Skill | Runbook |
|-------|---------|
| gcp-gce-ops | [aiops-gce-anomaly.md](gcp-gce-ops/references/advanced/aiops-gce-anomaly.md) |
| gcp-lb-ops | [aiops-lb-anomaly.md](gcp-lb-ops/references/advanced/aiops-lb-anomaly.md) |
| gcp-dns-ops | [aiops-dns-anomaly.md](gcp-dns-ops/references/advanced/aiops-dns-anomaly.md) |
| gcp-cloudfunctions-ops | [aiops-cloudfunctions-anomaly.md](gcp-cloudfunctions-ops/references/advanced/aiops-cloudfunctions-anomaly.md) |
| gcp-kms-ops | [aiops-kms-anomaly.md](gcp-kms-ops/references/advanced/aiops-kms-anomaly.md) |
| gcp-secretmanager-ops | [aiops-secretmanager-anomaly.md](gcp-secretmanager-ops/references/advanced/aiops-secretmanager-anomaly.md) |
| gcp-filestore-ops | [aiops-filestore-anomaly.md](gcp-filestore-ops/references/advanced/aiops-filestore-anomaly.md) |

### CDN (cross-dimension)
| Skill | Runbook |
|-------|---------|
| gcp-cdn-ops | [aiops-cdn-anomaly-detection.md](gcp-cdn-ops/references/advanced/aiops-cdn-anomaly-detection.md) · [aiops-cdn-prediction.md](gcp-cdn-ops/references/advanced/aiops-cdn-prediction.md) · [aiops-cdn-auto-remediation.md](gcp-cdn-ops/references/advanced/aiops-cdn-auto-remediation.md) · [finops-cdn-cost-analysis.md](gcp-cdn-ops/references/advanced/finops-cdn-cost-analysis.md) |

## Design Spec & Plan

- Spec: [docs/superpowers/aiops-selfhealing-spec.md](superpowers/aiops-selfhealing-spec.md)
- Plan: [docs/superpowers/aiops-selfhealing-plan.md](superpowers/aiops-selfhealing-plan.md)

## Known Gaps

- 16 pre-existing test failures in `gcp-gcl-runner-ops/tests/` (trigger-format audit +
  CLI arg standard) are tracked in `TODO.md` and are out of scope for this layer.
- eval_queries.json coverage for the above runbooks is being extended (see
  `feature/aiops-eval-coverage` branch).
