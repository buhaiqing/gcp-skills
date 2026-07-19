# Advanced References

Advanced operational guides for Google Cloud Composer / Airflow.

## Contents

| Document | Description |
|----------|-------------|
| [advanced-dag-patterns.md](advanced-dag-patterns.md) | SubDAG patterns, cross-DAG dependencies, dynamic task generation, setup/teardown tasks, SLA monitoring, retry strategies, sensor patterns |
| [airflow-2x-migration.md](airflow-2x-migration.md) | TaskGroup migration, sensor retirement, PythonVirtualenvOperator changes, HA cluster migration |
| [private-environment-setup.md](private-environment-setup.md) | VPC-native configuration, Private Service Connect, web server ingress control, DMZ architecture, DNS configuration |
| [aiops-composer-anomaly.md](aiops-composer-anomaly.md) | AIOps self-healing: worker pool exhaustion, DAG task failures, stuck upgrades — dry-run + idempotent + gate discipline |

## Usage

These documents cover advanced topics beyond the core operations in `references/`. Refer to them when:

- Building complex multi-DAG orchestration patterns
- Migrating from Airflow 1.x to 2.x
- Configuring private/restricted Composer environments

## See Also

- [Core Concepts](../core-concepts.md) — Airflow basics and Composer fundamentals
- [Troubleshooting Guide](../troubleshooting.md) — Common issues and resolutions
- [Integration](../integration.md) — Cross-service integration patterns
