---
name: cloudbuild-integration
description: Integration, bootstrap, environment, and credential rules for Cloud Build skill execution

<!---
load_condition: "[首次使用或环境配置时加载]"
token_cost_estimate: "~650 tokens"
dependencies: []
--->
---

# Integration — Cloud Build

## Environment Variables

| Variable | Purpose | Rule |
|----------|---------|------|
| `GOOGLE_APPLICATION_CREDENTIALS` | ADC service account key path | Verify existence only; never print file content |
| `CLOUDSDK_CORE_PROJECT` | Default project | Prefer over asking user; fallback to `gcloud config` |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | Temporary token | Never print; refresh with gcloud as needed |

## Local Tooling

```bash
gcloud version
python3 --version
```

Install SDK fallback only when needed:

```bash
python3 -m pip install --user google-cloud-build
```

## Authentication Checks

```bash
gcloud auth print-access-token >/dev/null
gcloud auth application-default print-access-token >/dev/null 2>&1 || true
```

Do not echo returned tokens.

## API Enablement Check

```bash
gcloud services list --enabled \
  --filter='config.name=cloudbuild.googleapis.com' \
  --format='value(config.name)'
```

Enabling APIs changes project state; ask for approval before `gcloud services enable cloudbuild.googleapis.com`.

## Required Roles by Operation

| Operation | Minimal starting role |
|-----------|-----------------------|
| List/describe builds | `roles/cloudbuild.builds.viewer` |
| Submit/cancel/retry builds | `roles/cloudbuild.builds.editor` or equivalent custom permissions |
| Manage triggers | Cloud Build trigger admin/editor permissions |
| Manage worker pools | `roles/cloudbuild.workerPoolOwner` or equivalent |
| Build step artifact push | Downstream role on target repo/project for build service account |

## Cross-Service Integration

- **Cloud Logging:** Build logs and audit logs; delegate sinks/metrics to `gcp-logging-ops`.
- **Artifact Registry/GCR:** Build images/artifacts; diagnose permissions here, delegate repo lifecycle.
- **Secret Manager:** Build secrets; do not print values, delegate secret lifecycle.
- **Cloud Run/GKE/GCE:** Deployment targets from build steps; delegate target resource configuration.
- **VPC:** Private worker pool networking; delegate broad network changes to `gcp-vpc-ops`.

## Safe Output Contract

Reports should include:

- Resource type and sanitized ID.
- Command family used (`gcloud builds ...`) without tokens.
- Status, log URL, and key validation fields.
- Redacted failure evidence and exact next action.

Reports must not include raw credential files, access tokens, webhook secrets, private keys, or plaintext build secrets.
