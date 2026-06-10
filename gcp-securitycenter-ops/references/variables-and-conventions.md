<!---
load_condition: "[总是加载 — 变量约定和 JSON paths]"
token_cost_estimate: "~900 tokens"
dependencies: []
--->

# Variables and API Conventions — Security Command Center

## Variable Convention

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to service account key JSON | NEVER ask; verify file exists without printing content |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | Default project ID | NEVER ask; HALT if unset and `gcloud config` has no project |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask; refresh via `gcloud auth print-access-token` when needed |
| `{{user.org_id}}` | Organization numeric ID (e.g. `123456789012`) | Ask once when parent = organization |
| `{{user.folder_id}}` | Folder numeric ID | Ask once when parent = folder |
| `{{user.parent}}` | Fully-qualified parent resource path | Derive from `{{user.org_id}}` / `{{user.folder_id}}` / `{{env.CLOUDSDK_CORE_PROJECT}}` |
| `{{user.source_id}}` | Source ID (e.g. `12345678901234567`) | Ask once for source-specific operations |
| `{{user.finding_id}}` | Finding name without parent prefix | Ask once for finding-specific operations |
| `{{user.filter}}` | SCC findings filter expression (e.g. `state="ACTIVE" AND severity="HIGH"`) | Ask once; default `state="ACTIVE"` |
| `{{user.limit}}` | Maximum list results | Ask once; default 50 |
| `{{user.page_size}}` | Page size for SDK pagination | Ask once; default 100 |
| `{{user.page_token}}` | Continuation token | Parse from `{{output.next_page_token}}` |
| `{{user.mute_config_id}}` | Mute config ID (max 20 chars) | Ask once for mute operations |
| `{{user.mute_filter}}` | Filter expression for a mute config | Ask once when creating/updating mute config |
| `{{user.notification_config_id}}` | Notification config ID (max 20 chars) | Ask once for notification operations |
| `{{user.pubsub_topic}}` | Fully-qualified Pub/Sub topic path | Ask once for notification create |
| `{{user.bigquery_export_id}}` | BigQuery export ID | Ask once for BQ export operations |
| `{{user.bq_dataset}}` | Fully-qualified BigQuery dataset path | Ask once for BQ export create |
| `{{user.bq_table_prefix}}` | Table name prefix for BQ export | Ask once for BQ export create; default `finding` |
| `{{user.custom_module_id}}` | Custom module name | Ask once for custom module operations |
| `{{user.module_id}}` | Module ID (built-in or custom) | Ask once for module enable/disable |
| `{{user.resource_value_config_id}}` | Resource value config ID | Ask once for resource value config operations |
| `{{user.resource_name}}` | Target resource name for resource value config | Ask once when creating/updating resource value config |
| `{{user.resource_value}}` | Severity value: `MINIMAL`/`LOW`/`MEDIUM`/`HIGH`/`CRITICAL` | Ask once for resource value config |
| `{{user.new_state}}` | Finding state to set: `ACTIVE`/`INACTIVE` | Ask once for finding state update |
| `{{user.export_parent}}` | Parent for CSV export (org only) | Ask once for CSV export |
| `{{user.csv_destination}}` | Local CSV file path | Ask once for CSV export |
| `{{user.confirm_delete}}` | Explicit delete confirmation | Require exact target resource name before destructive deletes |
| `{{output.finding_name}}` | Fully-qualified finding name | Parse `$.name` |
| `{{output.finding_state}}` | Finding state | Parse `$.state` |
| `{{output.finding_severity}}` | Finding severity | Parse `$.severity` |
| `{{output.mute_config_name}}` | Fully-qualified mute config name | Parse `$.name` |
| `{{output.notification_config_name}}` | Fully-qualified notification config name | Parse `$.name` |
| `{{output.bq_export_name}}` | Fully-qualified BQ export name | Parse `$.name` |
| `{{output.next_page_token}}` | Pagination token | Parse `$.nextPageToken` |
| `{{output.total_size}}` | Total findings matching filter | Parse `$.totalSize` |

> `{{env.*}}` values are never collected from the user. `{{user.*}}` values are asked once and reused. Never print access tokens, service account key content, or credential-bearing finding descriptions; redact values matching token/key patterns.

## Centralized JSON Paths

| Resource | JSON Path | Purpose |
|----------|-----------|---------|
| Finding fully-qualified name | `$.name` | Store `{{output.finding_name}}` |
| Finding parent | `$.parent` | Organization/folder/project path |
| Finding state | `$.state` | `ACTIVE` / `INACTIVE` |
| Finding severity | `$.severity` | `CRITICAL` / `HIGH` / `MEDIUM` / `LOW` / `SEVERITY_UNSPECIFIED` |
| Finding category | `$.category` | e.g. `OPEN_FIREWALL`, `PUBLIC_BUCKET_ACL` |
| Finding resource name | `$.resourceName` | Affected resource |
| Finding event time | `$.eventTime` | When the finding was first observed |
| Finding create time | `$.createTime` | When SCC ingested it |
| Finding external URI | `$.externalUri` | Console link |
| Finding mute config | `$.muteConfig` / `$.mute` | Mute association |
| Source display name | `$.displayName` | Human-readable source name |
| Source name | `$.name` | Fully-qualified source name |
| Mute config filter | `$.filter` | Filter expression |
| Notification config Pub/Sub topic | `$.pubsubTopic` | Destination topic |
| Notification config filter | `$.filter` | Filter expression |
| BQ export dataset | `$.dataset` | Fully-qualified dataset path |
| BQ export table prefix | `$.description` (when present) | Local config field; API uses `name` |
| Resource value config resource name | `$.resourceName` | Target resource |
| Resource value config severity | `$.resourceValue` | `MINIMAL` / `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| List pagination (v1 REST API) | `$.listFindingsResults[].finding` | REST JSON response field |
| List pagination (v2 SDK) | `ListFindingsResult.finding` (SDK object attribute, not a JSON path) | SDK iterator |
| Next page token | `$.nextPageToken` | Continue pagination |
