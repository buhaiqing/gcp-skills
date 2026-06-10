<!---
load_condition: "[总是加载 — 核心执行流程]"
token_cost_estimate: "~2500 tokens"
dependencies: ["references/gcloud-usage.md", "references/api-sdk-usage.md", "references/troubleshooting.md", "references/idempotency-checklist.md"]
--->

# Execution Flows — Security Command Center

Detailed Pre-flight → Execute → Validate → Recover flows for every SCC operation. SKILL.md links here per operation.

## Operation: Enable SCC

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI installed | `gcloud version` | Exit 0 | HALT — install Google Cloud SDK |
| Org-level IAM | Check caller has `roles/securitycenter.admin` at org | Role present | HALT — obtain SCC Admin at org level |
| API enabled | `gcloud services list --enabled --filter='config.name=securitycenter.googleapis.com'` | API enabled | HALT — enable SCC API with user approval |
| Current settings check | `gcloud scc settings get --organization="{{user.org_id}}"` | JSON returned | HALT — verify org ID and access |

### Execution

1. Show current enablement state, asset discovery state, and detector coverage tier.
2. Require explicit acknowledgement: enabling SCC at org scope has billing impact and activates detectors.
3. Execute `gcloud scc settings enable --organization="{{user.org_id}}" --format=json`.
4. Store output state.

### Post-execution Validation

- Describe settings again and confirm `enablementState` or equivalent active flag is set.

### Failure Recovery

- If `PERMISSION_DENIED`, the caller lacks org-level SCC Admin; delegate org IAM grant to `gcp-iam-ops`.
- If `FAILED_PRECONDITION`, SCC may already be enabled; check current state first.

---

## Operation: List, Describe, or Update Sources

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Viewer role | `gcloud scc sources list --organization="{{user.org_id}}" --limit=1 --format=json` | Exit 0 | HALT — need SCC admin viewer or editor |
| Source ID for describe | `{{user.source_id}}` is non-empty when describe/update requested | Non-empty | Ask once |

### Execution

- List: `gcloud scc sources list --organization="{{user.org_id}}" --format=json`
- Describe: `gcloud scc sources describe "{{user.source_id}}" --organization="{{user.org_id}}" --format=json`
- Update: `gcloud scc sources update "{{user.source_id}}" --organization="{{user.org_id}}" --display-name="<new>" --format=json`
- Parse `$.name`, `$.displayName`, `$.description`, `$.providerName`, `$.mostRecentEventTime`.

### Post-execution Validation

- Confirm expected source appears in list; for describe, confirm `$.name` matches.

### Failure Recovery

- On `NOT_FOUND`, verify source ID and org path.
- On permission errors, check `roles/securitycenter.adminViewer`.

---

## Operation: List or Describe Findings

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Viewer role | `gcloud scc findings list --organization="{{user.org_id}}" --limit=1 --format=json` | Exit 0 | HALT — need SCC findings viewer |
| Filter validity | Validate `{{user.filter}}` filter syntax | Valid expression | HALT — correct filter syntax |
| Source ID optional | `{{user.source_id}}` | Can be `-` for all sources | Default to `-` |

### Execution

1. Run `gcloud scc findings list` with `{{user.filter}}`, `{{user.limit}}`, `{{user.source_id}}`.
2. Parse findings array from response; extract `$.name`, `$.state`, `$.severity`, `$.category`, `$.resourceName`, `$.eventTime`, `$.muteConfig`.
3. For describe, use `gcloud scc findings describe` with source and finding IDs.

### Post-execution Validation

- Confirm findings match filter criteria.
- Show `totalSize` if available.

### Failure Recovery

- On `INVALID_ARGUMENT` (bad filter), correct filter syntax; consult [troubleshooting.md](troubleshooting.md#error-taxonomy).
- On permission errors, check `roles/securitycenter.findingsViewer`.

---

## Operation: Update Finding State

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Editor role | Verify `roles/securitycenter.findingsEditor` | Role present | HALT — obtain role |
| Finding exists | Describe finding to confirm current state | Finding JSON | HALT — verify source/finding IDs |
| State change preview | Show current state → proposed state | State differs | Ask for confirmation |
| Production impact | Confirm the finding is not a critical/active threat requiring immediate response | User acknowledged | HALT — clarify intent |

### Execution

1. Describe the finding first to capture current state.
2. Show state transition (e.g., `ACTIVE → INACTIVE` or `ACTIVE → MUTED`).
3. Execute `gcloud scc findings update-mute` or `gcloud scc findings update-state` via [gcloud-usage.md](gcloud-usage.md#findings) or [api-sdk-usage.md](api-sdk-usage.md#update-finding-state).
4. Store `{{output.finding_name}}`, `{{output.finding_state}}`.

### Post-execution Validation

- Describe the finding again and confirm `$.state` / `$.muteConfig` matches intended target.

### Failure Recovery

- If state is already the target, report and do not re-execute.
- If `NOT_FOUND`, the finding may have been deduplicated or moved; check list.
- If `PERMISSION_DENIED`, check `roles/securitycenter.findingsEditor`.

---

## Operation: Manage Mute Configs

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Editor role | `gcloud scc mute-configs list --organization="{{user.org_id}}" --limit=1 --format=json` | Exit 0 | HALT — need SCC mute configs editor |
| Filter validity | Validate `{{user.mute_filter}}` filter expression | Valid expression | HALT — correct filter syntax |
| Mute config ID format | `{{user.mute_config_id}}` matches `[a-zA-Z0-9-_]{1,20}` | Valid | HALT — correct ID |
| Existing config check | Create only: describe by ID first | NOT_FOUND for create | Continue to create; for update, confirm match |

### Execution

- List: `gcloud scc mute-configs list --organization="{{user.org_id}}" --format=json`
- Describe: `gcloud scc mute-configs describe "{{user.mute_config_id}}" --organization="{{user.org_id}}" --format=json`
- Create: `gcloud scc mute-configs create "{{user.mute_config_id}}" --organization="{{user.org_id}}" --filter="{{user.mute_filter}}" --type=DYNAMIC --format=json`
- Delete: require `{{user.confirm_delete}} == {{user.mute_config_id}}`, then `gcloud scc mute-configs delete ... --quiet`

### Post-execution Validation

- Describe confirms expected filter and type.
- Delete: describe/list returns `NOT_FOUND`.

### Failure Recovery

- On `ALREADY_EXISTS`, update the existing config instead of creating a duplicate.
- On `INVALID_ARGUMENT`, check filter syntax.
- On delete confirmation mismatch, HALT.

---

## Operation: Manage Notification Configs

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Editor role | `gcloud scc notifications list --organization="{{user.org_id}}" --limit=1 --format=json` | Exit 0 | HALT — need SCC notification configs editor |
| Pub/Sub topic exists | Validate topic path format | Valid topic | Ask user to create topic via `gcp-pubsub-ops` first |
| Topic publisher IAM | SCC service agent has `roles/pubsub.publisher` on the topic | Role present | HALT — grant via `gcp-iam-ops` before creating config |
| Notification config ID format | `{{user.notification_config_id}}` matches `[a-zA-Z0-9-_]{1,20}` | Valid | HALT — correct ID |

### Execution

- List: `gcloud scc notifications list --organization="{{user.org_id}}" --format=json`
- Describe: `gcloud scc notifications describe "{{user.notification_config_id}}" --organization="{{user.org_id}}" --format=json`
- Create: `gcloud scc notifications create "{{user.notification_config_id}}" --organization="{{user.org_id}}" --pubsub-topic="{{user.pubsub_topic}}" --filter="{{user.filter}}" --format=json`
- Update: `gcloud scc notifications update "{{user.notification_config_id}}" --organization="{{user.org_id}}" --filter="{{user.filter}}" --format=json`
- Delete: require `{{user.confirm_delete}} == {{user.notification_config_id}}`, then `gcloud scc notifications delete ... --quiet`

### Post-execution Validation

- Describe confirms topic path and filter.
- Delete: describe/list returns `NOT_FOUND`.

### Failure Recovery

- If `FAILED_PRECONDITION` (topic missing), delegate topic creation, then retry.
- On `PERMISSION_DENIED` (publisher IAM), delegate IAM grant, then retry.

---

## Operation: Manage BigQuery Exports

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Editor role | `gcloud scc big-query-exports list --organization="{{user.org_id}}" --limit=1 --format=json` | Exit 0 | HALT — need SCC BQ exports editor |
| Dataset exists | Validate dataset path format | Valid dataset | Ask user to create dataset via `gcp-bigquery-ops` first |
| SCC service agent has BQ Data Editor | Check dataset IAM | Role present | HALT — grant SCC service agent BigQuery Data Editor |
| BQ export ID format | `{{user.bigquery_export_id}}` matches `[a-zA-Z0-9-_]{1,20}` | Valid | HALT — correct ID |

### Execution

- List: `gcloud scc big-query-exports list --organization="{{user.org_id}}" --format=json`
- Describe: `gcloud scc big-query-exports describe "{{user.bigquery_export_id}}" --organization="{{user.org_id}}" --format=json`
- Create: `gcloud scc big-query-exports create "{{user.bigquery_export_id}}" --organization="{{user.org_id}}" --dataset="{{user.bq_dataset}}" --filter="{{user.filter}}" --format=json`
- Update: `gcloud scc big-query-exports update "{{user.bigquery_export_id}}" --organization="{{user.org_id}}" --filter="{{user.filter}}" --format=json`
- Delete: require `{{user.confirm_delete}} == {{user.bigquery_export_id}}`, then `gcloud scc big-query-exports delete ... --quiet`

### Post-execution Validation

- Describe confirms dataset path and filter.
- Delete: note that BQ tables are **not** dropped; only the export schedule stops.

### Failure Recovery

- If `FAILED_PRECONDITION` (dataset missing), delegate dataset creation.
- If `PERMISSION_DENIED` (service agent lacks BQ Data Editor), delegate IAM grant.

---

## Operation: Manage Custom Modules

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Custom modules editor role | `gcloud scc operations list` or SDK `list_security_health_analytics_custom_modules` | Exit 0 | HALT — need SCC custom modules editor |
| Module ID valid | `{{user.custom_module_id}}` is non-empty for enable/disable | Non-empty | Ask once |

### Execution

- List: use [api-sdk-usage.md](api-sdk-usage.md#custom-modules) — `client.list_security_health_analytics_custom_modules`.
- Get: `client.get_security_health_analytics_custom_module`.
- Enable/Disable: `client.update_security_health_analytics_custom_module` with `update_mask={"paths": ["enablement_state"]}`.

### Post-execution Validation

- Describe the module again and confirm `enablement_state` matches intended state.

### Failure Recovery

- If module is already in desired state, report and skip mutation.
- If `NOT_FOUND`, verify module ID and parent path.

---

## Operation: Manage Effective Modules

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Viewer role | List effective modules via SDK | Exit 0 | HALT — need SCC admin viewer |
| Folder/project scope | `{{user.folder_id}}` or `{{env.CLOUDSDK_CORE_PROJECT}}` | Non-empty | Ask once |

### Execution

- List: use [api-sdk-usage.md](api-sdk-usage.md#effective-modules) — `client.list_effective_security_health_analytics_custom_modules`.
- Get: `client.get_effective_security_health_analytics_custom_module`.

### Post-execution Validation

- Confirm expected modules appear in list; check `enablement_state`.

### Failure Recovery

- Effective modules are read-only; cannot directly enable/disable — must update the underlying custom module or folder/project module settings.

---

## Operation: Manage Resource Value Configs

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Editor role | SDK `list_resource_value_configs` | Exit 0 | HALT — need SCC resource value configs editor |
| Resource name valid | `{{user.resource_name}}` is a valid GCP resource path | Valid path | HALT — correct resource name |
| Resource value valid | `{{user.resource_value}}` in `MINIMAL`/`LOW`/`MEDIUM`/`HIGH`/`CRITICAL` | Valid enum | HALT — correct value |

### Execution

- List: `client.list_resource_value_configs(parent="organizations/{{user.org_id}}")`
- Create: `client.create_resource_value_config(parent="...", resource_value_config=..., resource_value_config_id="...")`
- Update: `client.update_resource_value_config` with `update_mask={"paths": ["resource_value", "description"]}`
- Delete: require `{{user.confirm_delete}} == {{user.resource_value_config_id}}`, then `client.delete_resource_value_config`.

### Post-execution Validation

- Describe confirms resource name and severity value.
- Delete: describe returns `NOT_FOUND`.

### Failure Recovery

- On `ALREADY_EXISTS`, update the existing config.
- On `INVALID_ARGUMENT`, check resource name path format.

---

## Operation: Organization Settings

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Admin role | `gcloud scc settings get --organization="{{user.org_id}}"` | Exit 0 | HALT — need SCC admin |
| Current settings visible | `gcloud scc settings get` returns settings JSON | JSON returned | HALT — verify org access |

### Execution

- Get: `gcloud scc settings get --organization="{{user.org_id}}" --format=json`
- Update (enable): `gcloud scc settings enable --organization="{{user.org_id}}" --format=json`

### Post-execution Validation

- Get settings again and confirm state changed.

### Failure Recovery

- `FAILED_PRECONDITION`: already enabled.
- `PERMISSION_DENIED`: org-level SCC Admin needed.

---

## Operation: Export Findings to CSV

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Viewer role | `gcloud scc findings list --organization="{{user.org_id}}" --limit=1 --format=json` | Exit 0 | HALT — need SCC findings viewer |
| Filter valid | `{{user.filter}}` is valid SCC filter syntax | Valid expression | HALT — correct filter |
| Source ID | Optional; use `-` for all sources | Default `-` | Default `-` |

### Execution

- `gcloud scc findings export --organization="{{user.org_id}}" --source="{{user.source_id}}" --filter="{{user.filter}}" --destination="{{user.csv_destination}}"`

### Post-execution Validation

- Confirm CSV file exists and contains headers.
- Row count match expected findings count.

### Failure Recovery

- If CSV destination is a local file, confirm write permissions.
- If `INVALID_ARGUMENT`, correct filter.