# Advanced Topics — Google Cloud Load Balancing

> Advanced content is lazy-loaded per TE-7. These topics extend the base skill for specialized scenarios.

## Available Topics

| Topic | File | Description |
|-------|------|-------------|
| AIOps Self-Healing | `aiops-lb-anomaly.md` | Health check failures, backend capacity exhaustion, SSL cert expiry detection + dry-run self-healing actions |
| FinOps Cost Optimization | `finops-lb-cost.md` | Forwarding rule waste detection, NEG consolidation, LB type cost comparison |

## Usage

These runbooks are loaded **on-demand** when the referenced operation is needed:

| Operation | Load Condition |
|-----------|----------------|
| Self-healing anomaly response | User reports LB health failures, backend errors, cert issues |
| Cost optimization | User asks about LB cost reduction or unused forwarding rules |

## Related References

- [execution-flows.md](../core-concepts.md) — LB types, architecture, quotas
- [monitoring.md](../monitoring.md) — Cloud Monitoring metrics and alert policies
- [troubleshooting.md](../troubleshooting.md) — Error diagnosis and recovery procedures
- [well-architected-assessment.md](../well-architected-assessment.md) — Five-pillar assessment (Cost §2.3)

## Token Efficiency

Per AGENTS.md §9 (TE-7): Advanced content requiring deep operational knowledge (FinOps, AIOps) is layered into `references/advanced/` to keep SKILL.md lean. Reference depth is capped at 2 layers (SKILL.md → references/advanced/).
