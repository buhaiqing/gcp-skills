---
name: gcp-bigquery-ops
description: >-
  Use when the user needs to manage, configure, troubleshoot, or monitor Google
  Cloud BigQuery resources — datasets, tables, views, materialized views,
  partitions, clustering, queries, jobs, IAM, cost analysis, data export/import,
  routines. User mentions BigQuery, bq, dataset, table, query, job, slot,
  partition, clustering, or describes analytics scenarios (e.g., "run a query",
  "create a dataset", "optimize query cost", "set up partitioning", "export
  data", "manage jobs") even without naming the product directly. Not for Cloud
  SQL, Bigtable, Spanner, Firestore, or other database products that have their
  own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`bq` command), Python SDK
  (`google-cloud-bigquery`), Go SDK (`cloud.google.com/go/bigquery`), valid
  service account credentials with BigQuery Admin or equivalent IAM roles,
  network access to bigquery.googleapis.com.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-08"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://bigquery.googleapis.com/$discovery/rest?version=v2"
  cli_applicability: "bq"
  cli_support_evidence: >-
    bq --help confirms subcommands: mk (create dataset/table), show (describe),
    ls (list), rm (delete), query, load, extract, cp (copy table), update
    (modify). See https://cloud.google.com/bigquery/docs/bq-command-line-tool
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud BigQuery Operations Skill

## Overview

BigQuery is a fully-managed, serverless data warehouse — datasets as containers, tables as structured columnar storage, jobs as compute units. This skill uses the **`bq` CLI** (part of Cloud SDK). Python SDK and JIT Go SDK are documented in references.

> **UX Compliance**: Follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md).

### Core Standards

| # | Standard | How Fulfilled |
|---|----------|---------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT with precise triggers and delegation rules |
| 2 | **Structured I/O** | `{{env.*}}`, `{{user.*}}`, `{{output.*}}` with documented types |
| 3 | **Explicit Steps** | Pre-flight → Execute → Validate → Recover for each operation |
| 4 | **Failure Strategies** | Error taxonomy (≥10 codes), HALT vs retry logic |
| 5 | **Single Responsibility** | BigQuery only; delegation to IAM, GCS, Monitoring, KMS skills |

### Google Cloud Architecture Framework

| Pillar | Reference |
|--------|-----------|
| **Security** | IAM, column/row-level access, VPC-SC, CMEK, audit logging |
| **Stability** | Dataset access controls, table snapshots, backup copies |
| **Cost** | On-demand ($5/TB), flat-rate reservations, partition pruning, dry-run |
| **Efficiency** | Partitioning, clustering, materialized views, query caching |
| **Performance** | Slot utilization, query optimization, clustering, BI Engine |

Full details: [references/well-architected-assessment.md](references/well-architected-assessment.md)

## Trigger & Scope

### SHOULD Use When
- User mentions "BigQuery", "bq", "dataset", "table", "query", "job", "slot", "partition", "clustering"
- Task: dataset CRUD, table CRUD, query execution, job management, partition/cluster management, IAM, cost analysis, data export/import, materialized views, routines

### SHOULD NOT Use When
- Relational DBs → `gcp-cloudsql-ops`; NoSQL → respective skill; Spanner → `gcp-spanner-ops` (planned); Bigtable → `gcp-bigtable-ops` (planned)
- IAM/SA → `gcp-iam-ops`; GCS buckets → `gcp-gcs-ops`; KMS → `gcp-kms-ops` (planned)
- Console-only flows with no API

## Variable Convention

| Placeholder | Meaning | Source |
|-------------|---------|--------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask; HALT if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask; HALT if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Access token | NEVER ask; refresh if expired |
| `{{user.dataset_id}}` | Dataset ID (project:dataset) | Ask once, reuse |
| `{{user.table_id}}` | Table ID (project:dataset.table) | Ask once, reuse |
| `{{user.job_id}}` | Job ID | Ask once or auto-generated |
| `{{user.query}}` | SQL query string | Ask once |
| `{{user.schema}}` | Table schema JSON/JSONL | Ask once |
| `{{user.location}}` | BigQuery region | Ask once; default US |
| `{{user.partition_field}}` | Partition column name | Ask once |
| `{{user.cluster_columns}}` | Clustering columns (comma-separated, e.g., `col1,col2`) | Ask once; converted to space-separated for CLI |
| `{{user.destination_uri}}` | GCS URI for export | Ask once |
| `{{user.source_uri}}` | GCS URI for load | Ask once |
| `{{user.format}}` | Data format (CSV/JSON/AVRO/PARQUET) | Ask once; default CSV |
| `{{user.iam_member}}` | IAM member (user:email/group:name/serviceAccount:sa) | Ask once |
| `{{user.iam_role}}` | IAM role | Ask once |
| `{{output.*}}` | Previous step result | Parse from API response |

> **Security**: Never output credentials. Mask in logs. Verify with `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA key exists"`.
> **Cost Safety**: ALWAYS run `--dry_run` before executing large queries to estimate cost.

## API Conventions

- **REST API**: BigQuery v2 (`bigquery.googleapis.com`). JSON paths centralized in [references/api-sdk-usage.md](references/api-sdk-usage.md).
- **Errors**: HTTP/gRPC → canonical types. See [references/troubleshooting.md](references/troubleshooting.md).
- **Idempotency**: `--replace` flag for table load; `--destination_table` with `WRITE_TRUNCATE`/`WRITE_APPEND`/`WRITE_EMPTY`.

## Prerequisites

### CLI Availability Check

Run this before any operation. Idempotent — installs `bq` only if missing:

```bash
if command -v bq &>/dev/null; then
  echo "✅ bq $(bq --version 2>&1) already installed"
else
  echo "WARN: bq not found — installing Google Cloud SDK..."
  if command -v apt-get &>/dev/null; then
    echo "DIAG: Detected Debian/Ubuntu — installing via apt"
    sudo apt-get update && sudo apt-get install -y google-cloud-cli
  elif command -v yum &>/dev/null; then
    echo "DIAG: Detected RHEL/CentOS — installing via yum"
    sudo yum install -y google-cloud-cli
  elif command -v brew &>/dev/null; then
    echo "DIAG: Detected macOS — installing via Homebrew"
    brew install --cask google-cloud-sdk
  elif command -v python3 &>/dev/null; then
    echo "DIAG: Detected Python — installing via pip"
    python3 -m pip install --upgrade google-cloud-sdk
  else
    echo "ERROR: No supported package manager found"
    echo "FIX: Install Google Cloud SDK manually: https://cloud.google.com/sdk/docs/install"
    exit 1
  fi
  echo "RESULT: bq installed successfully"
fi
```

After installation, verify credentials:
```bash
bq version
gcloud auth application-default login  # Interactive browser auth
gcloud config set project "{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Capabilities

| Operation | CLI Tool | Risk |
|-----------|----------|------|
| Create Dataset | `bq mk` | Low |
| Describe Dataset | `bq show` | None |
| List Datasets | `bq ls` | None |
| Update Dataset | `bq update` | Medium |
| Delete Dataset | `bq rm` | **High** |
| Create Table | `bq mk` | Low |
| Describe Table | `bq show` | None |
| List Tables | `bq ls` | None |
| Update Table | `bq update` | Medium |
| Delete Table | `bq rm` | **High** |
| Run Query | `bq query` | Medium (cost risk) |
| Dry-Run Query | `bq query --dry_run` | None |
| Describe Job | `bq show -j` | None |
| Cancel Job | `bq cancel` | Low |
| Create Partition | Table option | Low |
| Modify Clustering | `bq update` | Medium |
| Set IAM | `bq add-iam-policy-binding` | Medium |
| Export Data | `bq extract` | Low |
| Load Data | `bq load` | Medium |
| Create Materialized View | `bq mk --materialized_view` | Low |
| Create Routine | `bq mk --routine` | Low |
| Copy Table | `bq cp` | Low |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-08 | Initial release |

## Execution Flows

> All SDK (Python/Go) code snippets are in [references/api-sdk-usage.md](references/api-sdk-usage.md). For detailed CLI variants, see [references/gcloud-usage.md](references/gcloud-usage.md). For error recovery, see [references/troubleshooting.md](references/troubleshooting.md). For idempotent patterns, see [references/idempotency-checklist.md](references/idempotency-checklist.md).

### Create Dataset

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Dataset not exists | `bq show "{{user.dataset_id}}" --quiet 2>&1` | NOT_FOUND | HALT — already exists |
| Location valid | US/EU/region | Valid | HALT |
| Billing enabled | `gcloud beta billing projects describe` | Active | HALT — enable billing |

**CLI**: `bq --location="{{user.location:-US}}" mk --dataset --description="{{user.description:-}}" --label=env=dev "{{user.dataset_id}}"`
*Variants*: `--default_table_expiration`, `--default_partition_expiration`

**Validate**: `bq show --format=prettyjson "{{user.dataset_id}}" | jq '{datasetReference, location, defaultTableExpirationMs, labels}'`

### Describe Dataset

**CLI**: `bq show --format=prettyjson "{{user.dataset_id}}"`
*Extract*: `jq '{datasetReference, location, defaultTableExpirationMs, labels, access}'`
*Tables in dataset*: `bq ls "{{user.dataset_id}}"`

### List Datasets

**CLI**: `bq ls --format=prettyjson --project_id="{{env.CLOUDSDK_CORE_PROJECT}}"`
*Filter*: `jq '.[] | {datasetReference, location, friendlyName}'`
*All including hidden*: `bq ls -a`

### Update Dataset

**Pre-flight**: Dataset exists.

**CLI**:
- Labels: `bq update --set_label=K=V "{{user.dataset_id}}"`
- Description: `bq update --description="{{user.description}}" "{{user.dataset_id}}"`
- Default table expiration: `bq update --default_table_expiration="{{user.expiration_ms}}" "{{user.dataset_id}}"`
- Access control: `bq add-iam-policy-binding "{{user.dataset_id}}" --member="{{user.iam_member}}" --role="{{user.iam_role}}"`

**Validate**: `bq show --format=prettyjson "{{user.dataset_id}}" | jq '{labels, description, defaultTableExpirationMs}'`

### Delete Dataset — SAFETY GATE

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| User confirms | User types exact dataset ID | Match | HALT |
| Tables exist | `bq ls "{{user.dataset_id}}" --format=json` | Count displayed | Warn — all tables will be lost |

**WARN**: Irreversible — all tables and data permanently lost.

**CLI**:
- Empty: `bq rm --dataset "{{user.dataset_id}}"`
- Force (with tables): `bq rm -r -f --dataset "{{user.dataset_id}}"`

**Never use `--quiet` to bypass this safety gate.**

**Validate**: `bq show "{{user.dataset_id}}" --quiet 2>&1 || echo "✅ Dataset confirmed deleted"`

### Create Table

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Dataset exists | `bq show "{{user.dataset_id}}" --quiet` | Exit 0 | HALT — create dataset first |
| Table not exists | `bq show "{{user.table_id}}" --quiet 2>&1` | NOT_FOUND | HALT — already exists |

**CLI**:
- Empty table: `bq mk --table --schema="{{user.schema}}" "{{user.table_id}}"`
- From query: `bq query --destination_table="{{user.table_id}}" --replace "{{user.query}}"`
- From GCS: `bq load --source_format={{user.format:-CSV}} --autodetect "{{user.table_id}}" "{{user.source_uri}}"`
- Partitioned: `bq mk --table --schema="{{user.schema}}" --time_partitioning_field={{user.partition_field}} "{{user.table_id}}"`
- Clustered: `bq mk --table --schema="{{user.schema}}" --clustering_fields={{user.cluster_columns}} "{{user.table_id}}"`

**Validate**: `bq show --format=prettyjson "{{user.table_id}}" | jq '{tableReference, schema, timePartitioning, clustering, numRows, numBytes}'`

### Describe Table

**CLI**: `bq show --format=prettyjson "{{user.table_id}}"`
*Extract*: `jq '{tableReference, schema, timePartitioning, clustering, numRows, numBytes, type, creationTime}'`
*Schema only*: `bq show --schema --format=prettyjson "{{user.table_id}}"`

### List Tables

**CLI**: `bq ls --format=prettyjson "{{user.dataset_id}}"`
*Filter*: `jq '.[] | {tableReference, type, creationTime}'`
*Tables only*: `bq ls "{{user.dataset_id}}" | grep TABLE`
*Views only*: `bq ls "{{user.dataset_id}}" | grep VIEW`

### Update Table

**Pre-flight**: Table exists.

**CLI**:
- Schema: `bq update --schema="{{user.schema}}" "{{user.table_id}}"`
- Description: `bq update --description="{{user.description}}" "{{user.table_id}}"`
- Expiration: `bq update --expiration={{user.expiration_ms}} "{{user.table_id}}"`
- Labels: `bq update --set_label=K=V "{{user.table_id}}"`

**Validate**: `bq show --format=prettyjson "{{user.table_id}}" | jq '{schema, description, labels}'`

### Delete Table — SAFETY GATE

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| User confirms | User types exact table ID | Match | HALT |
| Data size | `bq show "{{user.table_id}}" --format=json | jq -r '.numRows'` | Row count | Display to user |

**WARN**: Irreversible — all rows permanently lost.

**CLI**: `bq rm -f --table "{{user.table_id}}"`

**Validate**: `bq show "{{user.table_id}}" --quiet 2>&1 || echo "✅ Table confirmed deleted"`

### Run Query — COST SAFETY

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Dry-run | `bq query --dry_run --use_legacy_sql=false "{{user.query}}" 2>&1` | Bytes processed | HALT if > threshold |
| Syntax valid | Dry-run exit 0 | Exit 0 | HALT — fix query |

**Dry-run first**: `bq query --dry_run --use_legacy_sql=false --format=prettyjson "{{user.query}}"`
*Extract cost*: `Estimated bytes processed → multiply by $5/TB (on-demand)`

**CLI**: `bq query --use_legacy_sql=false --format=prettyjson --max_rows=100 --destination_table="{{user.destination_table:-}}" "{{user.query}}"`
*Batch mode*: `bq query --use_legacy_sql=false --priority=batch --destination_table="{{user.destination_table}}" "{{user.query}}"`
*Interactive (default)*: `--priority=interactive`

**Validate**: `bq show -j "{{output.job_id}}" --format=prettyjson | jq '{statistics.query.totalBytesProcessed, statistics.query.totalSlotMs, status.state}'`

### Describe Job

**CLI**: `bq show -j "{{user.job_id}}" --format=prettyjson`
*Extract*: `jq '{configuration, statistics, status, jobReference}'`

### Cancel Job

**Pre-flight**: Job exists and is running/pending.

**CLI**: `bq cancel "{{user.job_id}}"`

**Validate**: `bq show -j "{{user.job_id}}" --format=prettyjson | jq '.status.state'` — should be `DONE` with error result.

### Create/Modify Partitioning

**Pre-flight**: Table exists, is not already partitioned.

**CLI**:
- Time partitioning: `bq update --time_partitioning_field={{user.partition_field}} --time_partitioning_type={{user.partition_type:-DAY}} "{{user.table_id}}"`
- Ingestion-time partitioning: `bq mk --table --time_partitioning_field=_PARTITIONTIME --time_partitioning_type=DAY "{{user.table_id}}"`
- Expiration: `bq update --time_partitioning_expiration={{user.expiration_ms}} "{{user.table_id}}"`

**Validate**: `bq show --format=prettyjson "{{user.table_id}}" | jq '.timePartitioning'`

### Create/Modify Clustering

**Pre-flight**: Table exists, ≤4 clustering columns.

**CLI**: `bq update --clustering_fields={{user.cluster_columns//,/ }} "{{user.table_id}}"`

**Validate**: `bq show --format=prettyjson "{{user.table_id}}" | jq '.clustering.fields'`

### Set Dataset IAM

**CLI**:
- Add: `bq add-iam-policy-binding "{{user.dataset_id}}" --member="{{user.iam_member}}" --role="{{user.iam_role}}"`
- Remove: `bq remove-iam-policy-binding "{{user.dataset_id}}" --member="{{user.iam_member}}" --role="{{user.iam_role}}"`
- View: `bq get-iam-policy "{{user.dataset_id}}"`

**Validate**: `bq get-iam-policy "{{user.dataset_id}}" --format=prettyjson | jq '.bindings[] | select(.role == "{{user.iam_role}}")'`

### Export Data to GCS

**Pre-flight**: GCS bucket exists, SA has `roles/storage.objectAdmin`.

**CLI**: `bq extract --destination_format={{user.format:-CSV}} --compression=GZIP "{{user.table_id}}" "{{user.destination_uri}}"`
*Variants*: `--field_delimiter`, `--print_header`, `--use_avro_logical_types`

**Validate**: `gsutil ls -l "{{user.destination_uri}}" | head -5`

### Load Data from GCS

**Pre-flight**: GCS source exists, schema compatible.

**CLI**: `bq load --source_format={{user.format:-CSV}} --autodetect --write_disposition=WRITE_TRUNCATE "{{user.table_id}}" "{{user.source_uri}}"`
*Variants*: `--skip_leading_rows=1`, `--field_delimiter=,`, `--schema="{{user.schema}}"`

**Validate**: `bq show --format=prettyjson "{{user.table_id}}" | jq '.numRows'`

### Create Materialized View

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Base table exists | `bq show "{{user.base_table_id}}" --quiet` | Exit 0 | HALT |
| MV not exists | `bq show "{{user.mv_id}}" --quiet 2>&1` | NOT_FOUND | HALT |

**CLI**: `bq mk --materialized_view "{{user.mv_id}}" "{{user.query}}"`

**Validate**: `bq show --format=prettyjson "{{user.mv_id}}" | jq '{type, materializedView}'`

### Create Routine (UDF)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Dataset exists | `bq show "{{user.dataset_id}}" --quiet` | Exit 0 | HALT |

**CLI**: `bq mk --routine --routine_type="{{user.routine_type:-SCALAR_FUNCTION}}" --language="{{user.language:-SQL}}" --definition_body="{{user.definition_body}}" --return_type="{{user.return_type}}" "{{user.dataset_id}}.{{user.routine_name}}"`

> **Note**: For SQL UDFs, wrap definition body in single quotes within the variable value to prevent shell expansion. For JS UDFs, escape special characters appropriately.

**Validate**: `bq show --format=prettyjson "{{user.dataset_id}}.{{user.routine_name}}" | jq '{routineType, definitionBody, returnType}'`

### Copy Table

**CLI**:
- Same project: `bq cp "{{user.source_table_id}}" "{{user.destination_table_id}}"`
- Cross-project: `bq cp --destination_kms_key="{{user.kms_key}}" "{{user.source_table_id}}" "{{user.destination_table_id}}"`

**Validate**: `bq show --format=prettyjson "{{user.destination_table_id}}" | jq '.numRows'`

## Quality Gate (GCL)

| Property | Value |
|----------|-------|
| Classification | **required** (Delete dataset/table + expensive query cost risk) |
| max_iter | 2 |
| Most-scrutinized | Delete Dataset, Delete Table, Run Query (cost), Export/Load |

- **Rubric**: [references/rubric.md](references/rubric.md)
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md)

## Token Efficiency (P0 — 强制)

| Rule | Implementation |
|------|---------------|
| **TE-1** API query > static | Use `bq ls` instead of hardcoding datasets/tables |
| **TE-2** No docstrings | `#` comments only in SDK snippets |
| **TE-3** Compact errors | ≤3 columns, 1 row per code |
| **TE-4** Centralized JSON | See [references/api-sdk-usage.md](references/api-sdk-usage.md) |
| **TE-5** YAML anchors | See [assets/example-config.yaml](assets/example-config.yaml) |
| **TE-6** No duplication | SKILL.md = what; references/ = how |
| **TE-7** Advanced content | AIOps/FinOps in `references/advanced/` |

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, quotas, Prerequisites
- [API & SDK Usage](references/api-sdk-usage.md) — REST API map, Python/Go SDK code
- [gcloud Usage](references/gcloud-usage.md) — `bq` CLI commands for all operations
- [Troubleshooting](references/troubleshooting.md) — Error codes (≥10), diagnostics, recovery
- [Integration](references/integration.md) — Go bootstrap, env vars, credential rules
- [Monitoring](references/monitoring.md) — Metrics, dashboards, alerts, cost monitoring
- [Idempotency Checklist](references/idempotency-checklist.md) — Retry-safe patterns
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Rubric](references/rubric.md) — GCL scoring
- [Prompt Templates](references/prompt-templates.md) — GCL templates

## See Also

- **Meta-Skill**: [gcp-skill-generator](../gcp-skill-generator/SKILL.md)
- **IAM**: [gcp-iam-ops](../gcp-iam-ops/SKILL.md) — Service accounts and permissions
- **GCS**: [gcp-gcs-ops](../gcp-gcs-ops/SKILL.md) — Data export/import source/destination
- **KMS**: (planned) — CMEK key management
- **Monitoring**: [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md) — Dashboards and alerts
- **GCL Runner**: [gcp-gcl-runner-ops](../gcp-gcl-runner-ops/SKILL.md) — Execution quality gate

## Operational Best Practices

- **Least privilege**: `roles/bigquery.dataViewer` (read), `roles/bigquery.dataEditor` (CRUD), `roles/bigquery.jobUser` (run queries), `roles/bigquery.admin` (full)
- **Cost safety**: Always `--dry_run` first; use partition pruning; set billing alerts
- **Security**: CMEK for sensitive data, VPC-SC, audit logging, column-level security
- **Performance**: Partition large tables, cluster on filter columns, use materialized views
- **Data governance**: Dataset-level access controls, table expiration policies, audit trails
- **Naming**: `{project}_{dataset}_{table}` — descriptive, consistent, lowercase with underscores
