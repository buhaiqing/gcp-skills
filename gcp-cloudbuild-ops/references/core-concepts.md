---
name: cloudbuild-core-concepts
description: Architecture, resource model, permissions, limits, and safety constraints for Cloud Build operations

<!---
load_condition: "[总是加载 — 架构和权限基础]"
token_cost_estimate: "~1200 tokens"
dependencies: []
--->
---

# Core Concepts — Google Cloud Build

## Resource Model

| Resource | Scope | Notes |
|----------|-------|-------|
| Build | Project; optionally regional execution | Immutable build execution record with status, steps, source, logs, images, artifacts |
| Trigger | Project/global or regional depending source/repo type | CI/CD automation that starts builds from source events or manual `run` |
| Private worker pool | Project + region | Dedicated build workers with worker and network configuration |
| Build config | Source file (`cloudbuild.yaml`/JSON) or inline API object | Defines steps, images, artifacts, substitutions, timeout, service account |
| Logs/artifacts | Cloud Logging/Cloud Storage/Artifact Registry | Separate services used by build execution |

## Control Plane vs Data Plane

- **Control plane:** create/list/describe/update/delete triggers and worker pools; submit/cancel/retry builds.
- **Data plane:** build steps execute user commands, push/pull images, deploy resources, access networks, and write logs/artifacts. This skill diagnoses data-plane failures but delegates non-Cloud Build resource lifecycle when needed.

## IAM and Service Accounts

| Actor | Common roles | Purpose |
|-------|--------------|---------|
| Operator/agent credential | `roles/cloudbuild.builds.viewer`, `roles/cloudbuild.builds.editor`, `roles/cloudbuild.workerPoolOwner` | Manage Cloud Build resources |
| Build service account | `roles/cloudbuild.builds.builder` plus downstream least-privilege roles | Runtime identity for build steps |
| Trigger service account | Explicit service account recommended | Avoid broad default service account privileges |

Do not print service account key content or access tokens. Validate IAM by checking operation-specific failures and current service account identity, then delegate broad IAM policy changes to `gcp-iam-ops`.

## Build Status and State Handling

| Status | Meaning | Action |
|--------|---------|--------|
| `QUEUED` | Waiting for worker/capacity | Check queue TTL, quota, private pool state |
| `WORKING` | Running steps | Monitor logs and timeout |
| `SUCCESS` | Terminal success | Validate artifacts/images |
| `FAILURE` | Step failed | Diagnose failing step/log line |
| `INTERNAL_ERROR` | Platform/internal failure | Retry if idempotent; preserve trace |
| `TIMEOUT` | Build exceeded timeout | Tune timeout/steps or investigate hangs |
| `CANCELLED` | Cancelled by user/system | Report interrupter if visible |
| `EXPIRED` | Queue TTL exceeded | Check capacity, worker pool, quotas |

## Trigger Safety

Triggers can deploy to production on source events. Before create/update/delete/run:

1. Show trigger name/ID, source repo, branch/tag pattern, build config, substitutions, and service account.
2. Confirm production impact if build config deploys or pushes artifacts.
3. Require exact target ID/name for delete.
4. Prefer update existing trigger over duplicate creation.

## Private Worker Pool Safety

- Pools are regional; do not use `global` for worker pool creation.
- Network configuration can expose private resources to build steps; require explicit review.
- Deleting a pool can break triggers/builds referencing it; list recent references before delete when feasible.
- Machine size and disk affect cost and quota.

## Operational Limits and Quotas

Use API/CLI queries over static numbers:

```bash
gcloud services list --enabled --filter='config.name=cloudbuild.googleapis.com'
gcloud builds list --limit=1 --format=json
gcloud builds worker-pools list --region="{{user.region}}" --format=json
gcloud compute regions describe "{{user.region}}" --format=json  # quota context if Compute-backed constraints appear
```

## Idempotency Principles

- Builds are execution records; submitting/retrying is not idempotent unless build steps are idempotent.
- Trigger create is idempotent only after checking existing trigger by name/source/config.
- Worker pool create/update is idempotent after comparing desired config to current state.
- Delete operations are idempotent only when `NOT_FOUND` is an acceptable final state and explicit confirmation was captured.

## Credential and Secret Handling

- Mask `GOOGLE_APPLICATION_CREDENTIALS`, tokens, webhook secrets, substitutions containing secret-like names, and log lines containing credentials.
- Use Secret Manager references in Cloud Build configs instead of plaintext substitutions.
- Never run `cat $GOOGLE_APPLICATION_CREDENTIALS` or print config structs containing credential material.
