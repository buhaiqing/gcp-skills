---
name: gcp-cloudsql-ops
description: >-
  Use when the user needs to manage, configure, troubleshoot, or monitor Google
  Cloud SQL (MySQL, PostgreSQL, SQL Server) — instance lifecycle, database/user
  management, backup/recovery (on-demand, PITR, import/export), HA (regional
  failover, read replicas, cross-region replicas), connection (Auth Proxy, SSL,
  authorized networks), maintenance, performance (Query Insights), and security
  (IAM DB authentication, CMEK). User mentions Cloud SQL, SQL instance, MySQL,
  PostgreSQL, Postgres, SQL Server, managed database, database, replica, backup,
  PITR, Cloud SQL Auth Proxy, or describes database scenarios ("create a
  database", "restore from backup", "instance won't start", "query insights",
  "DB connection failed") even without naming the product directly. Not for
  Cloud Spanner, Bigtable, BigQuery, Firestore, Memorystore, or other database
  products that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Cloud SQL Admin
  or Cloud SQL Viewer IAM role, network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://sqladmin.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud sql --help confirms subcommands: instances, backups, backups
    restore, databases, users, tiers, operations. See
    https://cloud.google.com/sdk/gcloud/reference/sql
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Cloud SQL Operations Skill

## Overview

Cloud SQL provides fully managed relational databases — MySQL, PostgreSQL, and SQL Server. This skill is an **operational runbook** with explicit scope, credential rules, pre-flight checks, **dual-path execution** (SDK + `gcloud` CLI), response validation, and failure recovery.

> **UX Compliance:** Follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md).

### CLI Applicability

- **`cli_applicability: dual-path`**: `gcloud` fully supports Cloud SQL. Ship both `references/gcloud-usage.md` and document SDK + `gcloud` steps for every operation. Coverage gaps listed in `references/gcloud-usage.md`.

## Quality Gates

| Standard | How Met |
|----------|---------|
| Clear Boundaries | SHOULD/SHOULD NOT triggers below |
| Structured I/O | `{{env.*}}`/`{{user.*}}`/`{{output.*}}` with source |
| Explicit Steps | Pre-flight → Execute → Validate → Recover per op |
| Failure Strategies | ≥10 error codes, HALT vs retry per type |
| Single Responsibility | Cloud SQL only; delegate others |

Google Cloud Architecture Framework: [well-architected-assessment.md](references/well-architected-assessment.md)

## Trigger & Scope (Agent-Readable)

### SHOULD Use When
- Cloud SQL, MySQL, PostgreSQL, SQL Server mentioned; CRUD on instances/databases/users/backups/replicas; import/export; connection setup; flags; maintenance; Query Insights
- Keywords: Cloud SQL, MySQL, PostgreSQL, Postgres, SQL Server, database, DB, failover, replica, backup, PITR, Query Insights, Auth Proxy, SSL, authorized network, flag, tier, maintenance

### SHOULD NOT Use When
- Bigtable/Firestore → `gcp-bigtable-ops` | BigQuery → `gcp-bigquery-ops` | Spanner → `gcp-spanner-ops`
- Memorystore/Redis → `gcp-memorystore-ops` | VPC → `gcp-vpc-ops` | IAM → `gcp-iam-ops` | GCS → `gcp-gcs-ops`
- Console-only flows with no API → state limitation

### Delegation Rules
VPC/Private IP → `gcp-vpc-ops` | GCS → `gcp-gcs-ops` | IAM → `gcp-iam-ops` | Monitoring → `gcp-monitoring-ops` | GCL → `gcp-gcl-runner-ops`

## Variable Convention

| Var | Source | Notes |
|-----|--------|-------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Env | NEVER ask; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | Env | NEVER ask; fail if unset |
| `{{user.project}}` | Ask once | Project override |
| `{{user.region}}` | Ask once | Default: us-central1 |
| `{{user.instance_name}}` | Ask once | Cloud SQL instance |
| `{{user.database_version}}` | Ask once | Default: MYSQL_8_0 |
| `{{user.tier}}` | Ask once | Default: db-n1-standard-2 |
| `{{user.root_password}}` | Ask once | SQL Server only; mask in logs |
| `{{user.database_name}}` | Ask once | Internal DB name |
| `{{user.user_name}}` | Ask once | DB user |
| `{{user.password}}` | Ask once | Use MYSQL_PWD/PGPASSWORD, not -p |
| `{{user.backup_id}}` | Ask once | Backup identifier |
| `{{user.gcs_bucket}}` | Ask once | GCS bucket |
| `{{user.replica_name}}` | Ask once | Read replica |
| `{{output.instance_state}}` | Parse | `$.state` |
| `{{output.instance_ip}}` | Parse | `$.ipAddresses[0].ipAddress` |

> **Credential Masking:** NEVER log SA keys, credential values, or passwords. Use `MYSQL_PWD`/`PGPASSWORD` env vars, not CLI `-p`.

## API & Response Conventions

- **REST API**: Cloud SQL Admin API v1 (`sqladmin.googleapis.com`). JSON paths verified against official reference.
- **Errors**: HTTP/gRPC status codes → canonical error types.
- **Timestamps**: RFC 3339.
- **Password security**: `--password` in gcloud is safe (HTTPS to API). For local DB connections, use `MYSQL_PWD`/`PGPASSWORD`.

### Key JSON Paths

| Operation | JSON Path |
|-----------|-----------|
| Create/Update/Delete | `$.name` (operation name) |
| Describe Instance | `$.{state,name,region,databaseVersion,settings.tier,settings.dataDiskSizeGb,ipAddresses}` |
| List Instances | `$.items[].{name,state,region,databaseVersion,settings.tier}` |
| Create Backup | `$.id` |
| List Backups | `$.items[].{id,description,status,enqueuedTime,selfLink}` |

### Expected State Transitions

| Operation | Initial State | Target State | Max Wait |
|-----------|---------------|--------------|----------|
| Create Instance | — | `RUNNABLE` | 600s |
| Delete Instance | `RUNNABLE` | absent | 300s |
| Restore Backup | `RUNNABLE` | `RUNNABLE` | 600s |
| Create Replica | — | `RUNNABLE` | 600s |
| Export/Import | `RUNNABLE` | `RUNNABLE` | 1800s |

## Quick Start

```bash
gcloud sql instances list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

See [core-concepts.md](references/core-concepts.md) for prerequisites.

## Capabilities at a Glance

| Operation | Risk | Operation | Risk |
|-----------|------|-----------|------|
| Instance Create | Low | Create Backup | None |
| Instance Describe | None | Restore Backup | **High** |
| Instance Update | Medium | Create Replica | Low |
| Instance Delete | **High** | Promote Replica | **High** |
| Export Database | Low | Import Database | **High** |
| Create Database | Low | Delete Database | **High** |
| Create User | Low | Enable Query Insights | Low |
| Restart Instance | Medium | | |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI) → Validate → Recover**. SDK examples: [api-sdk-usage.md](references/api-sdk-usage.md) :: [integration.md](references/integration.md).

### Operation: Create Instance

**Pre-flight**: gcloud CLI ✓ | Credentials ✓ | SQL Admin API enabled ✓ | Quota available ✓ | Name unique ✓ | VPC exists (if private IP).
**Smart defaults**: `MYSQL_8_0`, `db-n1-standard-2`, `us-central1`, `100GB SSD`, `03:00` backup.

```bash
gcloud sql instances create "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --region="{{user.region}}" \
  --database-version="{{user.database_version:-MYSQL_8_0}}" \
  --tier="{{user.tier:-db-n1-standard-2}}" --storage-size=100 --storage-type=SSD --format=json
```

**Validation**: Poll op DONE, describe `state: RUNNABLE`.

| Error | Action | Error | Action |
|-------|--------|-------|--------|
| 400/INVALID_ARGUMENT | Fix param | 403/PERMISSION_DENIED | HALT — grant cloudsql.admin |
| 409/ALREADY_EXISTS | Rename | 429/QUOTA_EXCEEDED | HALT — increase quota |
| 503/UNAVAILABLE | Retry 3x | BILLING_NOT_ENABLED | HALT |

### Operation: Describe Instance

**Pre-flight**: Instance exists.

```bash
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

Report: name, state, DB version, region, tier, IPs, storage, created time.

### Operation: Update Instance

**Pre-flight**: Instance RUNNABLE. Tier valid (if changing).

```bash
gcloud sql instances patch "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --tier="{{user.new_tier}}" --format=json
# Also: --database-flags, --maintenance-window-day/hour, --storage-size, --deletion-protection
```

**Validation**: Describe verifies changes applied.

### Operation: Delete Instance

**Safety Gate**: User types exact instance name. Warn: all data permanently lost. Suggest final backup.

**Pre-flight**: Instance exists. User confirmed.

```bash
gcloud sql instances delete "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

**Validation**: Describe returns NOT_FOUND.

| Error | Action | Error | Action |
|-------|--------|-------|--------|
| 404/NOT_FOUND | Success | 403/PERMISSION_DENIED | HALT |
| FAILED_PRECONDITION | HALT — wait RUNNABLE | 503/UNAVAILABLE | Retry |

---

### Operation: Create Backup

**Pre-flight**: Instance RUNNABLE.

```bash
gcloud sql backups create --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --description="{{user.backup_description}}" --format=json
```

**Validation**: `gcloud sql backups list` shows `status: SUCCESSFUL`.

### Operation: List Backups

**Pre-flight**: Instance RUNNABLE.

```bash
gcloud sql backups list --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

Fields: ID, type, status, description, enqueuedTime.

### Operation: Restore Backup

**Safety Gate**: Warn overwrites ALL current data. User types exact instance name.

**Pre-flight**: Instance RUNNABLE. Backup exists. User confirmed.

```bash
gcloud sql backups restore {{user.backup_id}} \
  --restore-instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

**Validation**: Describe confirms RUNNABLE.

| Error | Action | Error | Action |
|-------|--------|-------|--------|
| 404/NOT_FOUND | Invalid backup ID | 403/PERMISSION_DENIED | HALT |
| FAILED_PRECONDITION | Not RUNNABLE | RESTORE_FAILED | HALT — corrupt backup |

### Operation: Create Read Replica

**Pre-flight**: Source RUNNABLE. Backups enabled. Binary logging (MySQL). Replica name unique.

```bash
gcloud sql instances create "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --region="{{user.region}}" \
  --master-instance-name="{{user.instance_name}}" \
  --tier="{{user.tier:-db-n1-standard-2}}" --format=json
```

**Validation**: Describe confirms RUNNABLE + `replicaConfiguration.active`.

### Operation: Promote Replica

**Safety Gate**: Warn breaks replication. User confirms source instance name.

**Pre-flight**: Replica RUNNABLE. `.masterInstanceName` not null. User confirmed.

```bash
gcloud sql instances promote-replica "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

**Validation**: `.masterInstanceName` is null (standalone).

| Error | Action | Error | Action |
|-------|--------|-------|--------|
| 404/NOT_FOUND | HALT | 403/PERMISSION_DENIED | HALT |
| FAILED_PRECONDITION | Replication broken | 503/UNAVAILABLE | Retry |

### Operation: Export Database

**Pre-flight**: Instance RUNNABLE. GCS bucket exists. Write permission granted.

```bash
gcloud sql export sql "{{user.instance_name}}" \
  "gs://{{user.gcs_bucket}}/{{user.gcs_path}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database="{{user.database_name}}" --format=json
# Also: export csv with --query
```

**Validation**: Poll DONE. Verify file in GCS.

| Error | Action | Error | Action |
|-------|--------|-------|--------|
| 403/PERMISSION_DENIED | Check GCS perms | 404/NOT_FOUND | Check instance/bucket |
| EXPORT_FAILED | Size/quota issue | FAILED_PRECONDITION | Not RUNNABLE |

### Operation: Import Database

**Safety Gate**: Warn may overwrite existing data.

**Pre-flight**: Instance RUNNABLE. Import file exists. Read permission granted.

```bash
gcloud sql import sql "{{user.instance_name}}" \
  "gs://{{user.gcs_bucket}}/{{user.gcs_path}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database="{{user.database_name}}" --format=json
# Also: import csv with --table
```

**Validation**: Poll DONE.

| Error | Action | Error | Action |
|-------|--------|-------|--------|
| 403/PERMISSION_DENIED | Check GCS perms | 404/NOT_FOUND | File/instance missing |
| IMPORT_FAILED | Check file format | FAILED_PRECONDITION | Not RUNNABLE |

### Operation: Create Database

**Pre-flight**: Instance RUNNABLE. DB name unique.

```bash
gcloud sql databases create "{{user.database_name}}" \
  --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

**Validation**: `databases list` includes new DB.

| Error | Action | Error | Action |
|-------|--------|-------|--------|
| 409/ALREADY_EXISTS | Rename | 403/PERMISSION_DENIED | HALT |
| 404/NOT_FOUND | Instance missing | FAILED_PRECONDITION | Not RUNNABLE |

### Operation: Delete Database

**Safety Gate**: User types exact database name. Warn: data permanently lost.

**Pre-flight**: Instance RUNNABLE. Database exists. User confirmed.

```bash
gcloud sql databases delete "{{user.database_name}}" \
  --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

**Python SDK**: `SqlDatabasesServiceClient.Delete()` — [api-sdk-usage.md](references/api-sdk-usage.md#delete-database).

**Validation**: `databases list` confirms absent.

| Error | Action | Error | Action |
|-------|--------|-------|--------|
| 404/NOT_FOUND | Already deleted | 403/PERMISSION_DENIED | HALT |
| FAILED_PRECONDITION | Not RUNNABLE | 503/UNAVAILABLE | Retry |

### Operation: Create User

**Safety Gate**: Use `MYSQL_PWD`/`PGPASSWORD` for local connections, not `-p`. `--password` in gcloud is safe (HTTPS).

**Pre-flight**: Instance RUNNABLE. User name unique.

```bash
gcloud sql users create "{{user.user_name}}" \
  --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --password="{{user.password}}" --format=json
```

**Validation**: `users list` includes new user.

| Error | Action | Error | Action |
|-------|--------|-------|--------|
| 409/ALREADY_EXISTS | HALT | 403/PERMISSION_DENIED | HALT |
| 404/NOT_FOUND | Instance missing | FAILED_PRECONDITION | Not RUNNABLE |

### Operation: Enable Query Insights

**Pre-flight**: Instance RUNNABLE. MySQL or PostgreSQL (SQL Server unsupported).

```bash
gcloud sql instances patch "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --insights-config-query-insights-enabled \
  --insights-config-record-application-tags \
  --insights-config-record-client-address \
  --insights-config-query-string-length="{{user.query_length:-1024}}" --format=json
```

**Validation**: `.settings.insightsConfig.queryInsightsEnabled` is `true`.

### Operation: Restart Instance

**Pre-flight**: Instance RUNNABLE. User warned about ~60s connection drop.

```bash
gcloud sql instances restart "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

**Validation**: Poll state until RUNNABLE.

---

## References

| Document | Description |
|----------|-------------|
| [core-concepts.md](references/core-concepts.md) | Architecture, quotas, regions, prerequisites |
| [api-sdk-usage.md](references/api-sdk-usage.md) | REST API, Python SDK, operation map, snippets |
| [gcloud-usage.md](references/gcloud-usage.md) | `gcloud sql` command map, jq extracts |
| [troubleshooting.md](references/troubleshooting.md) | 20+ error codes, diagnostics |
| [monitoring.md](references/monitoring.md) | Metrics, dashboards, alerts |
| [integration.md](references/integration.md) | Go SDK, Auth Proxy, IAM DB auth |
| [idempotency-checklist.md](references/idempotency-checklist.md) | Retry-safe patterns |
| [well-architected-assessment.md](references/well-architected-assessment.md) | 5-pillar assessment |
| [rubric.md](references/rubric.md) | GCL scoring rubric |
| [prompt-templates.md](references/prompt-templates.md) | GCL templates |

## GCL Quality Gate

**Classification**: required | **max_iter**: 2 | **Most-scrutinized**: Delete Instance/Database, Restore Backup, Promote Replica, Import

## Token Efficiency

| Rule | Practice | Rule | Practice |
|------|----------|------|----------|
| TE-1 | `gcloud sql tiers list` over hardcoded tables | TE-2 | No docstrings; inline comments only |
| TE-3 | Error tables: 1 row, ≤3 cols | TE-4 | JSON paths centralized above |
| TE-6 | SKILL.md references/ don't repeat | | |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Instance lifecycle, backup/recovery, replicas, import/export, DB/user mgmt, security, Query Insights; dual-path gcloud+SDK; GCL quality gate |

## See Also

[gcp-skill-generator](../gcp-skill-generator/SKILL.md) | [gcp-gcs-ops](../gcp-gcs-ops/SKILL.md) | [gcp-vpc-ops](../gcp-vpc-ops/SKILL.md) | [gcp-iam-ops](../gcp-iam-ops/SKILL.md) | [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md) | [gcp-gcl-runner-ops](../gcp-gcl-runner-ops/SKILL.md)