<!---
load_condition: "[总是加载 — 核心执行流程]"
token_cost_estimate: "~1800 tokens"
dependencies: ["references/gcloud-usage.md", "references/api-sdk-usage.md", "references/troubleshooting.md", "references/idempotency-checklist.md"]
--->

# Execution Flows — Cloud Build

Detailed Pre-flight → Execute → Validate → Recover flows for every Cloud Build operation. SKILL.md links here per operation.

## Operation: Submit Build

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI installed | `gcloud version` | Exit 0 | HALT — install Google Cloud SDK |
| Project selected | `gcloud config get-value project` or `{{env.CLOUDSDK_CORE_PROJECT}}` | Non-empty | HALT — set project |
| API enabled | `gcloud services list --enabled --filter='config.name=cloudbuild.googleapis.com'` | `cloudbuild.googleapis.com` | HALT — enable API with user approval |
| Source/config exists | `test -d {{user.source_dir}} && test -f {{user.config_path}}` | Files exist | HALT — ask for valid paths |
| Secrets safe | inspect command arguments only | No secret literals in substitutions | HALT — move secrets to Secret Manager/env references |
| Build side effects preview | Inspect `{{user.config_path}}` for deploy/destructive commands, artifact pushes, mutable tags such as `latest`, external script downloads, and production substitutions | Side effects classified and shown with secrets redacted | Require explicit user acknowledgement for production/destructive effects |
| Supply-chain preview | Review source, builder images, artifacts, secrets, and provenance expectations; see [idempotency-checklist.md](idempotency-checklist.md) | Risks noted before execution | HALT — clarify unsafe external downloads/mutable tags |

### Execution

1. Preview project, source directory, config path, and substitutions with secret values redacted.
2. Execute `gcloud builds submit` using [gcloud-usage.md#submit-build](gcloud-usage.md#submit-build).
3. Store `{{output.build_id}}=$.id`, `{{output.build_status}}=$.status`, and `{{output.log_url}}=$.logUrl`.
4. If SDK path is required, use [api-sdk-usage.md#submit-build](api-sdk-usage.md#submit-build).

### Post-execution Validation

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Build created | Describe `{{output.build_id}}` | Status exists | Recover using build describe/logs |
| Terminal state | Poll status if requested | `SUCCESS` or requested non-blocking state | Diagnose failure/timeout |
| Artifacts/images | Inspect build result | Expected image/artifact present | Use artifact/IAM troubleshooting |

### Failure Recovery

- If status is `FAILURE`, `TIMEOUT`, `CANCELLED`, or `EXPIRED`, run [troubleshooting.md#diagnostic-flow](troubleshooting.md#diagnostic-flow).
- If source upload fails, verify `.gcloudignore`, path size, permissions, and Cloud Storage staging access.
- If downstream deploy/push fails, identify missing service account role and delegate broad IAM changes.

## Operation: List or Describe Builds

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Viewer role | `gcloud builds list --limit=1 --format=json` | Exit 0 | HALT — need Cloud Build viewer/editor |
| Build ID for describe | Validate `{{user.build_id}}` when provided | Non-empty | Ask once |

### Execution

1. For list, run `gcloud builds list --filter="{{user.filter}}" --limit={{user.limit}} --format=json`.
2. For describe, run `gcloud builds describe "{{user.build_id}}" --format=json`.
3. Parse status/timing/log paths from centralized JSON paths.

### Post-execution Validation

- Confirm requested build(s) are returned.
- For diagnosis, compare `createTime`, `startTime`, and `finishTime` for queue/runtime clues.

### Failure Recovery

- On `NOT_FOUND`, verify project, region/global context, build ID, and retention window.
- On permission errors, check `roles/cloudbuild.builds.viewer`.

## Operation: Cancel or Retry Build

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Build exists | `gcloud builds describe {{user.build_id}} --format=json` | Build JSON | HALT — correct build ID/project |
| State permits action | `$.status` | Cancel: `QUEUED`/`WORKING`; Retry: terminal failed/cancelled/expired | HALT — action not applicable |
| Mutation risk accepted | User intent explicit | User requested cancel/retry | HALT — ask confirmation for production-sensitive retry |

### Execution

- Cancel using `gcloud builds cancel "{{user.build_id}}" --format=json`.
- Retry using `gcloud builds retry "{{user.build_id}}" --format=json`.
- For retry, store new `{{output.build_id}}` if API returns a new build.

### Post-execution Validation

- Cancel: describe original build and expect `CANCELLED` or no longer running.
- Retry: describe new build and expect queued/working/successful progression.

### Failure Recovery

- If cancel races with completion, report final terminal status.
- If retry fails at submission, use failure diagnosis and service account/IAM checks.

## Operation: Create, Update, List, Describe, Run, or Delete Trigger

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Trigger API access | `gcloud builds triggers list --limit=1 --region="{{user.region}}" --format=json` when regional, otherwise omit `--region` after local help verification | Exit 0 | HALT — need trigger permissions or correct region |
| Operation selected | `{{user.operation}}` in create/update/import/list/describe/run/delete | One explicit operation | HALT — ask user to choose target operation |
| Config path | Create/update/import only: `test -f {{user.trigger_config}}` | File exists | HALT — provide config |
| Existing trigger check | Update/run/delete only: describe by ID using same project+region+trigger ID | Target JSON returned | HALT — correct trigger ID/region/project |
| Trigger preview | Show trigger name/ID, repo/source, branch/tag pattern, config, substitutions with redaction, service account, and detected deploy/artifact side effects | User can verify target and impact | HALT — cannot safely preview target |
| Production impact acknowledgement | Create/update/run only: inspect trigger config/build config for deploy steps, artifact pushes, production substitutions, and mutable tags | Explicit acknowledgement if production-impacting | HALT — user did not acknowledge impact |
| Supply-chain preview | Create/update only: review source connection, builder images, secrets, artifacts, and provenance expectations; see [idempotency-checklist.md](idempotency-checklist.md) | Risks noted before mutation | HALT — clarify unsafe external downloads/mutable tags |
| Run selector | Run only: `{{user.branch_name}}` or tag/commit selector provided and matches trigger source | Selector present | HALT — ask for exact selector |
| Delete confirmation | Delete only: `{{user.confirm_delete}} == {{user.trigger_id}}` after describe preview | Exact match | HALT — destructive op not confirmed |

### Execution

1. List/describe triggers to discover current state.
2. Create/update/run/delete using [gcloud-usage.md#triggers](gcloud-usage.md#triggers).
3. For create/update, validate source mapping, substitutions, service account, and included build config.
4. For run, capture `{{output.build_id}}` from the returned build.

### Post-execution Validation

- Create/update: describe trigger and compare name, source, branch/tag regex, config path, substitutions, service account.
- Run: describe returned build ID and inspect status/log URL.
- Delete: describe/list should return not found/no matching trigger.

### Failure Recovery

- On source connection errors, verify repository connection and OAuth/App installation outside this skill if necessary.
- On duplicate trigger names, update existing trigger instead of creating another.
- On delete failure, check if region-specific flags are required and confirm exact ID.

## Operation: Manage Private Worker Pools

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Region set | `{{user.region}}` | Non-global region | HALT — private pools require region |
| Worker pool permissions | `gcloud builds worker-pools list --region={{user.region}} --format=json` | Exit 0 | HALT — need worker pool viewer/owner |
| Desired config for create/update | `test -f {{user.worker_pool_config}}` when using config file | File exists or supported flags supplied | HALT — provide config or supported worker fields |
| Network config reviewed | Config/flag inspection | Valid peered network/private egress intent | HALT — clarify network design |
| Delete confirmation | `{{user.confirm_delete}} == {{user.worker_pool}}` | Exact match | HALT — destructive op not confirmed |

### Execution

- List/describe/create/update/delete using `gcloud builds worker-pools` commands in [gcloud-usage.md#private-worker-pools](gcloud-usage.md#private-worker-pools).
- Parse `$.name`, `$.state`, `$.workerConfig`, and `$.networkConfig`.

### Post-execution Validation

- Create/update: poll describe until state is usable/not updating; verify machine type, disk size, network.
- Delete: list/describe no longer returns the pool, or state indicates deletion in progress.

### Failure Recovery

- On network errors, check VPC peering, Private Service Connect/private Google access, DNS, and firewall routes.
- On capacity/quota errors, reduce worker config or request quota.
- If builds queue on the pool, inspect worker pool state and recent build `queueTtl`/timing.

## Operation: Diagnose Build Failure

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Build ID | `{{user.build_id}}` | Non-empty | Ask once |
| Read access | `gcloud builds describe {{user.build_id}} --format=json` | Exit 0 | HALT — need viewer role/correct project |
| Log access | `gcloud builds log {{user.build_id}}` or Cloud Logging query | Logs readable | Continue with metadata-only diagnosis if unavailable |

### Execution

1. Describe build; capture status, failure info, timings, service account, logs bucket, images, artifacts, substitutions with redaction.
2. Fetch logs safely; redact tokens, keys, passwords, and secret env values.
3. Classify error using [troubleshooting.md#error-taxonomy](troubleshooting.md#error-taxonomy).
4. Recommend minimal fix; do not mutate IAM, triggers, or artifacts unless the user approves a separate operation.

### Post-execution Validation

- Diagnosis includes likely failing step, error category, evidence line(s), and next action.
- If a retry is recommended, explain whether it is safe/idempotent.

### Failure Recovery

- If logs are missing, check `logsBucket`, Logging permissions, and retention.
- If build was never started, focus on queue, trigger, source, quota, and worker pool state.
