<!---
load_condition: "[总是加载 — 架构和权限基础]"
token_cost_estimate: "~1100 tokens"
dependencies: []
--->

# Core Concepts — Google Security Command Center

## Resource Model

| Resource | Scope | Notes |
|----------|-------|-------|
| Organization settings | Organization | Top-level SCC enablement, asset discovery enablement |
| Source | Organization, folder, or project | Produces findings; built-in or custom |
| Finding | Project (root container) | Central security object with state, severity, category, resource, muteConfig |
| Mute config | Organization, folder, or project | Suppresses findings matching a filter; only active on ACTIVE findings |
| Notification config | Organization, folder, or project | Routes findings matching a filter to a Pub/Sub topic |
| BigQuery export | Organization, folder, or project | Continuously exports findings to a BigQuery dataset |
| Custom module | Organization, folder, or project | User-defined Security Health Analytics detector |
| Effective module | Organization, folder, or project | Inherited module with effective enable state |
| Resource value config | Organization, folder, or project | Per-resource severity multiplier (`MINIMAL`/`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`) |
| Location | Global only | SCC v2 uses `locations=global`; v1 API is global by default |

## Tier Comparison

| Tier | Coverage | Notes |
|------|----------|-------|
| **Standard (free)** | Security Health Analytics, basic Web Security Scanner, Cloud Storage anomaly detection | Enabled by default in new organizations |
| **Premium** | Adds Event Threat Detection, Container Threat Detection, Security Health Analytics premium detectors, Virtual Machine Threat Detection | Paid; activated per org |
| **Enterprise** (formerly SCC Premium Enterprise / Chronicle-curated) | Adds attack path simulation, threat intelligence, case management | Higher pricing; activated per org |

[VERIFY: current tier names and exact detector set; Google has rebranded tiers in 2024-2025 — confirm with latest docs before quoting]

## Control Plane vs Data Plane

- **Control plane:** enable SCC, list/describe sources, list/describe findings, manage mute/notification/BQ-export configs, manage custom modules, manage resource value configs, read org settings.
- **Data plane:** the detectors themselves (Security Health Analytics scanners, Event Threat Detection, Container Threat Detection) generate findings. This skill does not invoke detectors directly; it manages the resources that receive detector output.

## IAM and Service Accounts

| Actor | Common roles | Purpose |
|-------|--------------|---------|
| Operator/agent credential | `roles/securitycenter.admin`, `roles/securitycenter.adminViewer`, `roles/securitycenter.findingsEditor`, `roles/securitycenter.muteConfigsEditor`, `roles/securitycenter.notificationConfigsEditor`, `roles/securitycenter.bigQueryExportsEditor` | Manage SCC resources at the operation's parent |
| BigQuery export service account | `roles/securitycenter.bigQueryExportsEditor` grants; export service agent created by SCC | Required to write to the export dataset |
| Notification config service account | `roles/securitycenter.notificationConfigsEditor`; topic publisher role on the target Pub/Sub topic | Required to publish to the topic |

Do not print service account key content or access tokens. For org-level operations, prefer impersonation (`gcloud config set auth/impersonate_service_account`) or caller's existing org-level SCC Admin.

## Finding State Machine

| From state | To state | Trigger | Effect |
|------------|----------|---------|--------|
| `ACTIVE` | `INACTIVE` | Resolve / mark as fixed; finding's resource no longer matches the detector | Stops alerting |
| `ACTIVE` | `MUTED` | Apply a mute config or set `mute` field directly | Suppresses alerting while keeping visibility |
| `MUTED` | `UNMUTED` | Remove mute config or clear `mute` field | Re-enables alerting |
| `INACTIVE` | `ACTIVE` | Resource reappears / re-detected | Detector re-emits |
| `ACTIVE` / `MUTED` | (deleted) | Source deleted or retention expired | Removed from listings |

Severity levels: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `SEVERITY_UNSPECIFIED`.

## Source Types

| Source | Type | Tier |
|--------|------|------|
| Security Health Analytics | Built-in | Standard+ |
| Event Threat Detection | Built-in | Premium |
| Container Threat Detection | Built-in | Premium |
| Virtual Machine Threat Detection | Built-in | Premium |
| Web Security Scanner | Built-in | Standard+ |
| Cloud Anomaly Detection | Built-in | Standard+ |
| Cloud Data Loss Prevention | Integration | Standard+ |
| Custom user source | User-defined | Standard+ |

## Operational Limits and Quotas

Use API/CLI queries over static numbers:

```bash
# Discover effective quota in current region/org
gcloud scc settings get --organization="{{user.org_id}}" --format=json
gcloud services list --enabled --filter='config.name=securitycenter.googleapis.com' --format='value(config.name)'

# List findings with pagination to discover cardinality
gcloud scc findings list --organization="{{user.org_id}}" --limit=10 --format=json
```

[VERIFY: exact quota values for `Findings.list` rate, mute-config rules per parent, BigQuery export rules per parent — check current docs before quoting.]

## Idempotency Principles

- `gcloud scc mute-configs create` is **not** idempotent on duplicate names — describe first, then either update or create.
- `gcloud scc notifications create` is **not** idempotent on duplicate IDs — same rule.
- `gcloud scc big-query-exports create` is **not** idempotent on duplicate IDs — same rule.
- `gcloud scc findings update-mute` / state mutations are write-once per call; verify post-state.
- Delete operations are idempotent only when `NOT_FOUND` is an acceptable final state and explicit confirmation was captured.

## Credential and Secret Handling

- Mask `GOOGLE_APPLICATION_CREDENTIALS`, access tokens, and any `private_key` content.
- Redact `Authorization` headers in REST traces.
- Never `cat` service account key files; never print finding descriptions that may contain credential material.
- Use VPC Service Controls to keep SCC API access within an authorized perimeter.
