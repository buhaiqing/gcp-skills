---
name: gcp-composer-ops
description: >-
  Use when the user needs to create, configure, manage, or troubleshoot Google
  Cloud Composer — Airflow environments, DAGs, variables, connections, PyPI
  packages, workloads, and environment configuration. User mentions Cloud
  Composer, Airflow, DAG, environment, workflow, or describes orchestration
  scenarios (e.g., "create Airflow environment", "manage DAGs", "add PyPI
  packages") even without naming the product directly. Not for Dataflow,
  Dataproc, or other orchestration tools that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Composer
  Admin IAM role, network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-15"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://composer.googleapis.com/$discovery/rest?version=v2"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud composer --help confirms subcommands: environments, operations, storage.
    See https://cloud.google.com/sdk/gcloud/reference/composer
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Composer Operations Skill

## Overview

Google Cloud Composer is a managed Apache Airflow service for workflow orchestration. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` supports Composer operations via `gcloud composer environments`. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Cloud Composer) with clear delegation to related skills (GKE, Storage, IAM) |

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM roles, network configuration, environment variables encryption | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Environment sizing, worker redundancy, backup/restore | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Environment sizing, storage costs, worker costs | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | DAG management, PyPI packages, environment variables | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Airflow metrics, scheduler performance, worker utilization | `references/well-architected-assessment.md` §2.5 |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Cloud Composer", "Airflow", "DAG", "workflow orchestration"
- Task involves creating, describing, updating, or deleting Composer environments
- Task involves managing DAGs, variables, connections, or operators
- Task involves configuring PyPI packages, environment variables, workloads
- Task involves Airflow versions, Composer images, or worker scaling
- User describes orchestration scenarios (e.g., "schedule workflows", "manage data pipelines")

### SHOULD NOT Use This Skill When

- Task is purely about GKE clusters → delegate to: `gcp-gke-ops`
- Task is purely about Cloud Storage → delegate to: `gcp-gcs-ops`
- Task is purely about IAM / permissions → delegate to: `gcp-iam-ops`
- Task is purely about billing / cost → delegate to: `gcp-billing-ops`
- Task is purely about Dataflow or Dataproc → use their specific skills
- User insists on **console-only** flows with no API → state limitation

### Delegation Rules

| Resource | Delegated Skill | Flow |
|----------|----------------|------|
| GKE cluster | `gcp-gke-ops` | Composer creates GKE cluster → manage via GKE skill |
| Cloud Storage bucket | `gcp-gcs-ops` | Composer uses bucket for DAGs → manage via GCS skill |
| VPC network | `gcp-vpc-ops` | Composer needs VPC → configure via VPC skill |

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.environment_name}}` | Composer environment name | Ask once; reuse |
| `{{user.region}}` | GCP region | Ask once; reuse |
| `{{output.environment_name}}` | From last API or `gcloud` JSON response | Parse per REST API path |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value.

## API and Response Conventions (Agent-Readable)

- **REST API is canonical** for path, query, body fields, enums, and response shapes.
- **Errors:** Map SDK/gRPC/HTTP errors to canonical gRPC status codes and messages.
- **Timestamps:** RFC 3339 with timezone when the API returns strings.

### Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Create | `$.name` | string | Environment name |
| Describe | `$.state` | string | Environment state (RUNNING, CREATING, etc.) |
| List | `$.environments[].name` | array | Environment names |
| Update | `$.name` | string | Environment being updated |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create | — | `RUNNING` | 60s | 1800s (30min) |
| Update | `RUNNING` | `RUNNING` | 60s | 1800s (30min) |
| Delete | `RUNNING` | absent | 60s | 600s (10min) |

## Quick Start

### What This Skill Does
This skill enables you to manage Cloud Composer environments, DAGs, variables, connections, and configuration on Google Cloud using the `gcloud` CLI (primary) or JIT Go SDK (fallback).

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`
- [ ] Composer Admin IAM role granted

### Verify Setup
```bash
# Check gcloud and project
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
```

### Your First Command
```bash
# List all Composer environments
gcloud composer environments list --project={{env.CLOUDSDK_CORE_PROJECT}} --format="json"
```

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Create Environment | Create a new Composer environment | High | Low |
| Describe Environment | View environment details | Low | None |
| Update Environment | Modify environment configuration | Medium | Medium |
| Delete Environment | Remove a Composer environment | Low | **High** — irreversible |
| List Environments | View all environments | Low | None |
| Manage Variables | CRUD Airflow variables | Low | Low |
| Manage Connections | CRUD Airflow connections | Low | Low |

## Token Efficiency Guidelines (P0 — 强制)

Every `gcp-*-ops` SKILL.md MUST include this section. Rules TE-1 to TE-7 sourced from `gcp-skill-generator/references/gcp-skill-template.md` §Token Efficiency Guidelines; full definitions at `gcp-skill-generator/SKILL.md` §Token Efficiency Requirements.

| Rule | Key Point | Application |
|------|-----------|-------------|
| **TE-1** API query > static table | Use `gcloud` to fetch versions/quotas, no hardcoding | Replace hardcoded machine-type/version tables with live queries |
| **TE-2** Omit unnecessary docstrings | Inline comments only, no function-level docstring | Python/Go SDK snippets use `#`/`//` inline comments |
| **TE-3** Compact error tables | 1 error code per row, ≤3 columns | Error taxonomy tables in `references/troubleshooting.md` stay compact |
| **TE-4** Centralized JSON paths | Declare at file top, don't repeat | Resource JSON paths declared once in `variables-and-conventions.md` |
| **TE-5** YAML anchors | `example-config.yaml` use `&anchor` | Reusable config blocks use anchors to eliminate duplication |
| **TE-6** Eliminate cross-file duplication | SKILL.md has full flow, references/ don't repeat | Execution flows live in SKILL.md; references/ link, don't re-narrate |
| **TE-7** Layer professional content | AIOps/FinOps in `references/advanced/`; destructive ops marked Security-Sensitive | Advanced content split out; confirmations gated explicitly |

**Non-compressible**: Agent-executable commands (params, JSON paths), error recovery logic, safety gates, credential rules, cross-skill orchestration chains.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-15 | Initial Cloud Composer skill with environment, DAG, variable management |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud and/or SDK/API) → Validate → Recover**.

### Operation: Create Environment

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI / deps | `gcloud version` | Exit code 0 | Document gcloud install |
| Credentials | gcloud auth / SA key file | Non-empty / valid | HALT; user authenticates |
| Project | `gcloud config get-value project` or env var | Set and valid | HALT; user sets project |
| Network | VPC network exists | Network available | HALT; create VPC first |
| Quota | Check project quotas | Sufficient quota | HALT; user requests increase |

#### Execution — CLI (`gcloud`)

```bash
gcloud composer environments create {{user.environment_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region={{user.region}} \
  --environment-size=small \
  --airflow-version=2.9.3 \
  --python-version=3.11 \
  --format="json"
```

#### Execution — Python SDK (Primary Fallback)

```python
# create_environment.py
import os
from google.cloud import composer_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
region = "{{user.region}}"

client = composer_v1.EnvironmentsClient()

environment = composer_v1.Environment(
    name=f"projects/{project}/locations/{region}/environments/{{user.environment_name}}",
    config=composer_v1.EnvironmentConfig(
        environment_size=composer_v1.Environment.Size.SMALL,
        software_config=composer_v1.SoftwareConfig(
            image_version="composer-2.9.3-airflow-2.9.3",
            python_version="3.11",
        ),
    ),
)

request = composer_v1.CreateEnvironmentRequest(
    parent=f"projects/{project}/locations/{region}",
    environment=environment,
)

operation = client.create_environment(request=request)
# Wait for operation to complete
```

#### Post-execution Validation

```bash
# Poll until RUNNING (create takes 15-30 minutes)
for i in $(seq 1 60); do
  STATE=$(gcloud composer environments describe {{user.environment_name}} \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --region={{user.region}} \
    --format="json" | jq -r '.state')
  [ "$STATE" = "RUNNING" ] && break
  sleep 30
done
echo "Environment state: $STATE"
```

#### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|--------------|-------------|---------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | 0–1 | — | Fix args from API reference | `[ERROR] INVALID_ARGUMENT: Invalid environment configuration` |
| `ALREADY_EXISTS` / 409 | 0 | — | Ask reuse vs new name | `[ERROR] ALREADY_EXISTS: Environment name already exists` |
| `QUOTA_EXCEEDED` / 429 | 0 | — | HALT | `[ERROR] QUOTA_EXCEEDED: Composer quota reached` |
| `PERMISSION_DENIED` / 403 | 0 | — | HALT | `[ERROR] PERMISSION_DENIED: Insufficient IAM permissions` |
| `FAILED_PRECONDITION` / 400 | 0 | — | HALT | `[ERROR] FAILED_PRECONDITION: VPC or network not configured` |

### Operation: Update Environment

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Environment exists | Describe | State is RUNNING | HALT — cannot update non-running env |
| No pending update | Describe | No pending operations | Wait for current update to complete |

#### Execution — CLI (`gcloud`)

```bash
# Update environment size
gcloud composer environments update {{user.environment_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region={{user.region}} \
  --environment-size=medium \
  --format="json"

# Add PyPI packages
gcloud composer environments update {{user.environment_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region={{user.region}} \
  --update-pypi-packages-from-file=packages.txt \
  --format="json"
```

#### Post-execution Validation

Poll until environment returns to `RUNNING` state.

### Operation: Delete Environment

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of `{{user.environment_name}}`.
- **MUST** warn user about data loss (DAGs, variables, connections).
- **MUST NOT** proceed without clear user assent.

#### Execution — CLI (`gcloud`)

```bash
gcloud composer environments delete {{user.environment_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region={{user.region}} \
  --quiet
```

#### Post-execution Validation

Poll describe until `NOT_FOUND` or environment is removed.

### Operation: Manage Variables

#### Execution — CLI (`gcloud`)

```bash
# Create variable
gcloud composer environments storage dags import \
  --environment={{user.environment_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region={{user.region}} \
  --source=gs://bucket/dags/variables.json

# Or via Airflow CLI (through SSH)
gcloud composer environments run {{user.environment_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region={{user.region}} \
  variables set key value
```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [gcloud Usage](references/gcloud-usage.md)
- [Troubleshooting Guide](references/troubleshooting.md)
- [Monitoring & Alerts](references/monitoring.md)
- [Integration](references/integration.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)

## Operational Best Practices

- **Least privilege:** IAM roles scoped to required permissions only.
- **Environment sizing:** Start small, scale based on workload.
- **Version management:** Use stable Airflow versions; test upgrades in non-prod.
- **DAG management:** Store DAGs in version control; use CI/CD for deployment.
- **Monitoring:** Enable Cloud Monitoring for environment health and performance.
