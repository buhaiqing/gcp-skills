<!---
load_condition: "[首次使用或环境配置时加载]"
token_cost_estimate: "~700 tokens"
dependencies: []
--->

# Integration — Security Command Center

## Environment Variables

| Variable | Purpose | Rule |
|----------|---------|------|
| `GOOGLE_APPLICATION_CREDENTIALS` | ADC service account key path | Verify existence only; never print file content |
| `CLOUDSDK_CORE_PROJECT` | Default project ID | Prefer over asking user; fallback to `gcloud config` |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | Temporary access token | Never print; refresh with gcloud as needed |

## Local Tooling

```bash
gcloud version
python3 --version
```

Install SDK fallback only when needed:

```bash
python3 -m pip install --user google-cloud-securitycenter_v2
```

## Authentication Checks

```bash
gcloud auth print-access-token >/dev/null
gcloud auth application-default print-access-token >/dev/null 2>&1 || true
```

Do not echo returned tokens. For org-level operations, prefer Workload Identity or service account impersonation over raw key files.

## API Enablement Check

```bash
gcloud services list --enabled \
  --filter='config.name=securitycenter.googleapis.com' \
  --format='value(config.name)'
```

Enabling APIs changes project state; ask for approval before `gcloud services enable securitycenter.googleapis.com`.

## Required Roles by Operation

| Operation | Minimal starting role |
|-----------|----------------------|
| Get org settings | `roles/securitycenter.adminViewer` at org |
| Enable SCC | `roles/securitycenter.admin` at org |
| List/describe sources | `roles/securitycenter.adminViewer` at org |
| List/describe findings | `roles/securitycenter.findingsViewer` at org/folder/project |
| Update finding state | `roles/securitycenter.findingsEditor` at org/folder/project |
| Set mute on finding | `roles/securitycenter.findingsEditor` at org/folder/project |
| Manage mute configs | `roles/securitycenter.muteConfigsEditor` at org/folder/project |
| Manage notification configs | `roles/securitycenter.notificationConfigsEditor` at org/folder/project |
| Manage BigQuery exports | `roles/securitycenter.bigQueryExportsEditor` at org/folder/project |
| Manage custom modules | `roles/securitycenter.customModulesEditor` at org/folder/project |
| Manage resource value configs | `roles/securitycenter.resourceValueConfigsEditor` at org/folder/project |

## Cross-Service Integration

- **Pub/Sub:** Notification configs route findings to topics. Delegate topic lifecycle to `gcp-pubsub-ops`; check SCC service agent IAM on the topic before creating the config.
- **BigQuery:** Continuous exports write to datasets. Delegate dataset creation to `gcp-bigquery-ops`; grant SCC service agent `roles/bigquery.dataEditor` before creating the export.
- **Cloud Logging:** SCC audit logs for all SCC mutations. Delegate log sink/metric management to `gcp-logging-ops`.
- **Cloud Monitoring:** SCC metrics for finding counts and severity scores. Delegate alert policy management to `gcp-monitoring-ops`.
- **IAM:** SCC roles and service agent IAM grants. Delegate broad policy design to `gcp-iam-ops`.
- **VPC Service Controls:** SCC API can be restricted to authorized perimeters. Delegate perimeter management outside this skill.

## SCC Service Agent

SCC uses the following service agent to write to BigQuery and publish to Pub/Sub:

```
service-<project-number>@gcp-sa-securitycenter.iam.gserviceaccount.com
```

When setting up BigQuery exports or notification configs, grant this principal:
- `roles/bigquery.dataEditor` on the target dataset
- `roles/pubsub.publisher` on the target topic

## Safe Output Contract

Reports should include:

- Resource type and sanitized ID.
- Command family used (`gcloud scc ...`) without tokens.
- Finding state, severity, category, and resource name (redacted where sensitive).
- Validation evidence and exact next action.

Reports must not include raw credential files, access tokens, private keys, or service account key content.