---
name: cloudbuild-gcloud-usage
description: gcloud command map for Cloud Build builds, triggers, worker pools, and diagnostics

<!---
load_condition: "[执行 CLI 操作时加载]"
token_cost_estimate: "~1700 tokens"
dependencies: ["references/api-sdk-usage.md"]
--->
---

# gcloud Usage — Cloud Build

All commands use sanitized parameters. Add `--project="{{user.project}}"` when it differs from `{{env.CLOUDSDK_CORE_PROJECT}}`. Prefer `--format=json` for machine parsing.

## Pre-flight

```bash
gcloud version
gcloud config get-value project
gcloud services list --enabled --filter='config.name=cloudbuild.googleapis.com' --format='value(config.name)'
gcloud builds list --limit=1 --format=json
```

## Submit Build

```bash
gcloud builds submit "{{user.source_dir}}" \
  --config="{{user.config_path}}" \
  --substitutions="{{user.substitutions}}" \
  --project="{{user.project}}" \
  --format=json
```

Notes:
- Omit `--substitutions` if empty.
- Redact secret-like substitution values before logging.
- For no-source builds, use `gcloud builds submit --no-source --config=...` when requested.

## List and Describe Builds

```bash
gcloud builds list \
  --filter="{{user.filter}}" \
  --limit="{{user.limit}}" \
  --project="{{user.project}}" \
  --format=json

gcloud builds describe "{{user.build_id}}" \
  --project="{{user.project}}" \
  --format=json

gcloud builds log "{{user.build_id}}" \
  --project="{{user.project}}"
```

For regional builds, add `--region="{{user.region}}"` to list/describe/log/cancel/retry commands when supported by the installed SDK, or use the full regional build resource/API path documented in [api-sdk-usage.md](api-sdk-usage.md#rest-patterns). Legacy global/project-level builds may omit `--region`.

Useful filters: `status=FAILURE`, `createTime>2026-06-01T00:00:00Z`, `substitutions.TRIGGER_NAME="name"`.

## Cancel and Retry Builds

```bash
gcloud builds cancel "{{user.build_id}}" \
  --project="{{user.project}}" \
  --format=json

gcloud builds retry "{{user.build_id}}" \
  --project="{{user.project}}" \
  --format=json
```

Add `--region="{{user.region}}"` for regional builds when local `gcloud builds cancel --help` / `retry --help` supports it; otherwise use the regional REST resource name.

Cancel only running/queued builds. Retry can re-run deployments or artifact pushes; confirm production-sensitive retries.

## Triggers

### List/Describe

```bash
gcloud builds triggers list \
  --project="{{user.project}}" \
  --region="{{user.region}}" \
  --format=json

gcloud builds triggers describe "{{user.trigger_id}}" \
  --project="{{user.project}}" \
  --region="{{user.region}}" \
  --format=json
```

Use the same `--project`, `--region`, and trigger ID for pre-update/pre-delete describe and post-mutation validation. Regional repository/connection triggers require `--region="{{user.region}}"`; global/classic triggers may omit `--region` after verifying local `gcloud builds triggers describe --help` behavior.

### Create

```bash
gcloud builds triggers create github \
  --name="{{user.trigger_name}}" \
  --repo-name="{{user.repo_name}}" \
  --repo-owner="{{user.repo_owner}}" \
  --branch-pattern="{{user.branch_pattern}}" \
  --build-config="{{user.config_path}}" \
  --service-account="{{user.service_account}}" \
  --project="{{user.project}}" \
  --region="{{user.region}}" \
  --format=json
```

For global/classic GitHub triggers, omit `--region` if local help does not support it. For regional trigger types, keep `--region="{{user.region}}"`.

For repository/connection based triggers, use import/export style config files when possible:

```bash
gcloud builds triggers import \
  --source="{{user.trigger_config}}" \
  --project="{{user.project}}" \
  --region="{{user.region}}"
```

### Update

```bash
# Config-file reconciliation path; import creates or updates the named trigger spec.
gcloud builds triggers import \
  --source="{{user.trigger_config}}" \
  --project="{{user.project}}" \
  --region="{{user.region}}"

# Type-specific update path; confirm supported flags locally before mutation.
gcloud builds triggers update github "{{user.trigger_id}}" \
  --branch-pattern="{{user.branch_pattern}}" \
  --build-config="{{user.config_path}}" \
  --project="{{user.project}}" \
  --region="{{user.region}}" \
  --format=json
```

If a specific trigger type requires different flags, run local help first: `gcloud builds triggers update --help` and the subtype help.

### Run

```bash
gcloud builds triggers run "{{user.trigger_id}}" \
  --branch="{{user.branch_name}}" \
  --substitutions="{{user.substitutions}}" \
  --project="{{user.project}}" \
  --region="{{user.region}}" \
  --format=json
```

### Delete

```bash
# Require: {{user.confirm_delete}} exactly equals {{user.trigger_id}}
gcloud builds triggers delete "{{user.trigger_id}}" \
  --project="{{user.project}}" \
  --region="{{user.region}}" \
  --quiet
```

## Private Worker Pools

### List/Describe

```bash
gcloud builds worker-pools list \
  --region="{{user.region}}" \
  --project="{{user.project}}" \
  --format=json

gcloud builds worker-pools describe "{{user.worker_pool}}" \
  --region="{{user.region}}" \
  --project="{{user.project}}" \
  --format=json
```

### Create/Update/Delete

Cloud SDK worker-pool flags can vary by version. Run local help before mutation and use supported flags such as worker config, peered network, machine type, and disk size. If `--config-from-file` is not supported by the installed SDK, translate `{{user.worker_pool_config}}` into supported flags or use the Cloud Build API.

```bash
gcloud builds worker-pools create --help >/dev/null
gcloud builds worker-pools update --help >/dev/null

gcloud builds worker-pools create "{{user.worker_pool}}" \
  --region="{{user.region}}" \
  --worker-machine-type="{{user.machine_type}}" \
  --worker-disk-size="{{user.disk_size}}" \
  --peered-network="{{user.peered_network}}" \
  --project="{{user.project}}" \
  --format=json

gcloud builds worker-pools update "{{user.worker_pool}}" \
  --region="{{user.region}}" \
  --worker-machine-type="{{user.machine_type}}" \
  --worker-disk-size="{{user.disk_size}}" \
  --project="{{user.project}}" \
  --format=json

# Require: {{user.confirm_delete}} exactly equals {{user.worker_pool}}
gcloud builds worker-pools delete "{{user.worker_pool}}" \
  --region="{{user.region}}" \
  --project="{{user.project}}" \
  --quiet
```

## Diagnostic Logging Pattern

When wrapping commands in scripts, emit structured logs:

```bash
printf '[%(%H:%M:%S)T] [DIAG] action=describe_build build_id=%s\n' -1 "{{user.build_id}}"
# command here
printf '[%(%H:%M:%S)T] [RESULT] status=%s log_url=%s\n' -1 "${STATUS}" "${LOG_URL}"
```

Use `[ERROR] TYPE={category} FIX={action}` for failures and never print credentials.
