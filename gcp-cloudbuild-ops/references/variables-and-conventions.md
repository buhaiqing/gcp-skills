<!---
load_condition: "[总是加载 — 变量约定和 JSON paths]"
token_cost_estimate: "~800 tokens"
dependencies: []
--->

# Variables and API Conventions — Cloud Build

## Variable Convention

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to service account key JSON | NEVER ask; verify file exists without printing content |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | Default project ID | NEVER ask; HALT if unset and `gcloud config` has no project |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask; refresh via `gcloud auth print-access-token` when needed |
| `{{user.project}}` | Project override | Ask once; default to env/config project |
| `{{user.region}}` | Worker pool/trigger region | Ask once; default `global` for triggers, explicit region for private pools |
| `{{user.source_dir}}` | Local source directory for submit | Ask once; default `.` |
| `{{user.config_path}}` | Build config path | Ask once; default `cloudbuild.yaml` |
| `{{user.build_id}}` | Build UUID/name | Ask once for describe/cancel/retry/log diagnosis |
| `{{user.filter}}` | Build/trigger list filter expression | Ask once when user requests filtered list; default empty |
| `{{user.limit}}` | Maximum list results | Ask once; default 20 |
| `{{user.trigger_id}}` | Trigger ID/name | Ask once for trigger operations |
| `{{user.trigger_name}}` | Human-readable trigger name | Ask once for create/update when not in config |
| `{{user.trigger_config}}` | Trigger config JSON/YAML path | Ask once for create/update/import |
| `{{user.branch_pattern}}` | Branch regex for trigger | Ask once when creating/updating branch trigger |
| `{{user.branch_name}}` | Branch name for manual trigger run | Ask once for run trigger |
| `{{user.repo_name}}` | Repository/source identifier | Ask once for trigger source config |
| `{{user.repo_owner}}` | GitHub repository owner/org | Ask once for GitHub trigger create when not in config |
| `{{user.service_account}}` | Cloud Build trigger/build service account | Ask once when creating/updating trigger or inspecting impact |
| `{{user.start_time}}` | Lower-bound timestamp for diagnosis/list filters | Ask once when user requests time-scoped diagnosis |
| `{{user.operation}}` | Requested Cloud Build operation | Infer from user request; confirm before mutation |
| `{{user.resource}}` | Target resource kind/name | Infer from user request; confirm before mutation |
| `{{user.worker_pool}}` | Private worker pool ID | Ask once for pool operations |
| `{{user.worker_pool_config}}` | Desired worker pool config JSON/YAML path | Ask once for create/update; extract supported CLI/API fields |
| `{{user.machine_type}}` | Worker machine type | Ask once for worker pool create/update when not in config |
| `{{user.disk_size}}` | Worker disk size in GB | Ask once for worker pool create/update when not in config |
| `{{user.peered_network}}` | VPC network for private pool | Ask once when private networking is required |
| `{{user.substitutions}}` | Build substitutions map | Ask once; pass as comma-separated or JSON |
| `{{user.confirm_delete}}` | Explicit delete confirmation | Require exact target resource name before trigger/worker-pool delete |
| `{{output.build_id}}` | Submitted/retried build ID | Parse `$.id` |
| `{{output.build_status}}` | Build status | Parse `$.status` |
| `{{output.log_url}}` | Console log URL | Parse `$.logUrl` |
| `{{output.trigger_id}}` | Created/listed trigger ID | Parse `$.id` |
| `{{output.worker_pool_name}}` | Worker pool full name | Parse `$.name` |

> `{{env.*}}` values are never collected from the user. `{{user.*}}` values are asked once and reused. Never print access tokens, service account key content, secret substitutions, or build logs containing credentials; redact values matching token/key patterns.

## Centralized JSON Paths

| Resource | JSON Path | Purpose |
|----------|-----------|---------|
| Build ID | `$.id` | Store `{{output.build_id}}` |
| Build name | `$.name` | Fully-qualified build resource |
| Build status | `$.status` | Validate queued/working/success/failure/cancelled |
| Build timing | `$.createTime,$.startTime,$.finishTime` | Queue/runtime diagnosis |
| Build logs | `$.logUrl,$.logsBucket` | Log access guidance |
| Build images/artifacts | `$.images,$.artifacts` | Artifact validation |
| Trigger ID/name | `$.id,$.name` | Trigger validation |
| Trigger source | `$.github,$.repositoryEventConfig,$.triggerTemplate` | Source mapping |
| Worker pool name | `$.name` | Worker pool validation |
| Worker pool state | `$.state` | Create/update/delete polling |
| Worker pool config | `$.workerConfig,$.networkConfig` | Capacity/network diagnosis |
