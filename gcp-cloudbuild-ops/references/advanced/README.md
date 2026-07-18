# Advanced References — Cloud Build

Advanced operational content for Cloud Build: FinOps cost optimization, AIOps anomaly detection, and SDK code snippets.

## Contents

| File | Description |
|------|-------------|
| [finops-cloudbuild-cost.md](finops-cloudbuild-cost.md) | Build minute cost analysis, caching strategies, parallel execution optimization, reserved capacity pricing |
| [aiops-cloudbuild-anomaly.md](aiops-cloudbuild-anomaly.md) | Build failure pattern detection, build time anomaly alerts, retry prediction using Cloud Monitoring + log-based metrics |
| [sdk-snippets.md](sdk-snippets.md) | Python SDK snippets (build submission, trigger CRUD, worker pool management) and Go SDK equivalents |

## Usage

Load these files when performing advanced Cloud Build operations:

- **FinOps**: When analyzing build costs or optimizing CI/CD spend
- **AIOps**: When setting up build monitoring, anomaly detection, or automated remediation
- **SDK**: When writing automation scripts for build management

## Relationship to SKILL.md

These files follow AGENTS.md §9 (TE-7): advanced content layered into `references/advanced/`, keeping SKILL.md lean and focused on core operations.

See also:
- [SKILL.md](../../SKILL.md) — Core Cloud Build operations
- [execution-flows.md](../execution-flows.md) — Pre-flight/Execute/Validate/Recover flows
- [troubleshooting.md](../troubleshooting.md) — Error diagnosis and recovery
- [monitoring.md](../monitoring.md) — Build monitoring and alerting
