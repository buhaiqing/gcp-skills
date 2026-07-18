<!---
load_condition: "[总是加载 — 核心执行流程]"
token_cost_estimate: "~2500 tokens"
dependencies: ["references/gcloud-usage.md", "references/api-sdk-usage.md", "references/troubleshooting.md", "references/idempotency-checklist.md"]
--->

# Execution Flows — Security Command Center

Detailed Pre-flight → Execute → Validate → Recover flows for every SCC operation. SKILL.md links here per operation.

## Operation: Enable SCC

### Pre-flight Checks

| Check | Action | Reference |
|-------|--------|-----------|
| CLI installed | HALT if `gcloud version` fails; install SDK | Prerequisites |
| Org-level IAM | HALT if missing `roles/securitycenter.admin` at org | gcp-iam-ops |
| API enabled | HALT if SCC API not enabled; enable with user approval | `gcloud services enable` |
| Current settings | HALT if `gcloud scc settings get` fails; verify org ID | troubleshooting.md |

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

| Check | Action | Reference |
|-------|--------|-----------|
| Viewer role | HALT if `gcloud scc sources list` fails; need SCC viewer | gcloud-usage.md |
| Source ID for describe | Ask once if empty for describe/update | — |

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

| Check | Action | Reference |
|-------|--------|-----------|
| Viewer role | HALT if missing `roles/securitycenter.findingsViewer` | gcloud-usage.md |
| Filter validity | HALT if `{{user.filter}}` syntax invalid | troubleshooting.md |
| Source ID | Default `-` for all sources | — |

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

| Check | Action | Reference |
|-------|--------|-----------|
| Editor role | HALT if missing `roles/securitycenter.findingsEditor` | gcp-iam-ops |
| Finding exists | HALT if describe fails; verify source/finding IDs | gcloud-usage.md |
| State change preview | Ask for confirmation if state differs | — |
| Production impact | HALT if critical/active threat; clarify intent | — |

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

| Check | Action | Reference |
|-------|--------|-----------|
| Editor role | HALT if missing `roles/securitycenter.muteConfigsEditor` | gcp-iam-ops |
| Filter validity | HALT if `{{user.mute_filter}}` syntax invalid | troubleshooting.md |
| Mute config ID format | HALT if `{{user.mute_config_id}}` not `[a-zA-Z0-9-_]{1,20}` | — |
| Existing config check | Create: describe first → continue if NOT_FOUND; Update: confirm match | gcloud-usage.md |

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

| Check | Action | Reference |
|-------|--------|-----------|
| Editor role | HALT if missing `roles/securitycenter.notificationConfigsEditor` | gcp-iam-ops |
| Pub/Sub topic exists | HALT if topic missing; delegate to `gcp-pubsub-ops` | gcp-pubsub-ops |
| Topic publisher IAM | HALT if SCC service agent lacks `roles/pubsub.publisher`; delegate to `gcp-iam-ops` | gcp-iam-ops |
| Notification config ID | HALT if `{{user.notification_config_id}}` not `[a-zA-Z0-9-_]{1,20}` | — |

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

| Check | Action | Reference |
|-------|--------|-----------|
| Editor role | HALT if missing `roles/securitycenter.bigQueryExportsEditor` | gcp-iam-ops |
| Dataset exists | HALT if missing; delegate to `gcp-bigquery-ops` | gcp-bigquery-ops |
| SCC service agent BQ IAM | HALT if missing `roles/bigquery.dataEditor` on dataset | gcp-iam-ops |
| BQ export ID format | HALT if `{{user.bigquery_export_id}}` not `[a-zA-Z0-9-_]{1,20}` | — |

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

| Check | Action | Reference |
|-------|--------|-----------|
| Custom modules editor role | HALT if missing `roles/securitycenter.customModulesEditor` | gcp-iam-ops |
| Module ID valid | Ask once if empty for enable/disable | — |

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

| Check | Action | Reference |
|-------|--------|-----------|
| Viewer role | HALT if missing SCC admin viewer | gcp-iam-ops |
| Folder/project scope | Ask once if empty | — |

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

| Check | Action | Reference |
|-------|--------|-----------|
| Editor role | HALT if missing `roles/securitycenter.resourceValueConfigsEditor` | gcp-iam-ops |
| Resource name valid | HALT if `{{user.resource_name}}` not valid GCP path | api-sdk-usage.md |
| Resource value valid | HALT if `{{user.resource_value}}` not in MINIMAL/LOW/MEDIUM/HIGH/CRITICAL | — |

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

| Check | Action | Reference |
|-------|--------|-----------|
| Admin role | HALT if missing `roles/securitycenter.admin` | gcp-iam-ops |
| Current settings visible | HALT if `gcloud scc settings get` fails; verify org access | gcloud-usage.md |

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

| Check | Action | Reference |
|-------|--------|-----------|
| Viewer role | HALT if missing `roles/securitycenter.findingsViewer` | gcp-iam-ops |
| Filter valid | HALT if `{{user.filter}}` syntax invalid | troubleshooting.md |
| Source ID | Default `-` for all sources | — |

### Execution

- `gcloud scc findings export --organization="{{user.org_id}}" --source="{{user.source_id}}" --filter="{{user.filter}}" --destination="{{user.csv_destination}}"`

### Post-execution Validation

- Confirm CSV file exists and contains headers.
- Row count match expected findings count.

### Failure Recovery

- If CSV destination is a local file, confirm write permissions.
- If `INVALID_ARGUMENT`, correct filter.