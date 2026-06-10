<!---
load_condition: "[失败或报错时加载]"
token_cost_estimate: "~1200 tokens"
dependencies: []
--->

# Troubleshooting — Security Command Center

## Diagnostic Flow

1. Identify the failing operation (enable, findings, mute configs, notification configs, BQ exports, modules, resource value configs, org settings).
2. Describe the resource using the same parent (org/folder/project) and resource ID used in the failing call.
3. Capture sanitized status, error code, error message, and parent resource path.
4. Classify using the error taxonomy below.
5. Recommend the smallest safe fix. Do not mutate IAM, Pub/Sub, or BigQuery resources without explicit approval.

## Error Taxonomy

| Code / Symptom | Likely Cause | Recovery |
|----------------|--------------|----------|
| `PERMISSION_DENIED` on SCC operations | Operator lacks SCC Admin / Editor / Viewer at the target parent | HALT — grant `roles/securitycenter.admin` (org level) or `roles/securitycenter.findingsEditor` at the target scope |
| `PERMISSION_DENIED` on Pub/Sub topic | SCC service agent lacks `roles/pubsub.publisher` on the target topic | HALT — grant `roles/pubsub.publisher` to `serviceAccount:service-<project-num>@gcp-sa-securitycenter.iam.gserviceaccount.com` |
| `PERMISSION_DENIED` on BigQuery dataset | SCC service agent lacks BigQuery Data Editor on the export dataset | HALT — grant `roles/bigquery.dataEditor` to SCC service agent |
| `NOT_FOUND: source` | Wrong source ID or wrong organization path | Verify org ID, source ID, and that the source still exists |
| `NOT_FOUND: finding` | Wrong finding ID, source ID, or finding was deduplicated/expired | Verify source ID, finding ID; check retention window |
| `NOT_FOUND: mute-config` | Wrong mute config ID or parent | Verify parent (org/folder/project) and config ID |
| `NOT_FOUND: notification-config` | Wrong notification config ID | Verify parent and config ID |
| `NOT_FOUND: big-query-export` | Wrong export ID | Verify parent and export ID |
| `FAILED_PRECONDITION: securitycenter not enabled` | SCC is not enabled at the target parent | HALT — enable SCC first with `gcloud scc settings enable` |
| `FAILED_PRECONDITION: dataset not found` | BigQuery dataset does not exist | HALT — create dataset via `gcp-bigquery-ops` first |
| `FAILED_PRECONDITION: topic not found` | Pub/Sub topic does not exist | HALT — create topic via `gcp-pubsub-ops` first |
| `FAILED_PRECONDITION: mute config already exists` | Duplicate create without idempotency check | Describe existing config and update if desired state differs |
| `ALREADY_EXISTS: mute-config/notification-config/BQ-export` | Duplicate ID on create | Describe and update instead of create |
| `INVALID_ARGUMENT: filter syntax` | SCC filter expression malformed | Correct filter syntax per [gcloud-usage.md](gcloud-usage.md#findings); common causes: unmatched quotes, invalid field names, bad operators |
| `INVALID_ARGUMENT: resource value config` | Invalid resource name path or severity value | Verify resource path format and severity enum value |
| `RESOURCE_EXHAUSTED` | [VERIFY: SCC API quota exceeded — check current quota docs] | Backoff and retry; if persistent, request quota increase |
| `DEADLINE_EXCEEDED` | SCC API call timed out | Retry with exponential backoff; check network |
| `UNAUTHENTICATED` | Credentials expired or not set | Re-authenticate with `gcloud auth application-default login` |
| `INTERNAL` | Transient platform issue | Retry with backoff; preserve trace |
| Finding state not changing after update-mute | Finding already in target state or was in terminal state | Describe finding; confirm current state; do not retry if state is already target |
| Notification config not receiving events | Topic IAM wrong, filter too restrictive, SCC not enabled for events | Check topic IAM, filter expression, and SCC enablement state |

## Finding Diagnosis Commands

```bash
# Get current finding state
gcloud scc findings describe "{{user.finding_id}}" \
  --organization="{{user.org_id}}" \
  --source="{{user.source_id}}" --format=json

# List recent active findings
gcloud scc findings list \
  --organization="{{user.org_id}}" \
  --filter='state="ACTIVE"' \
  --limit=20 --format=json

# List muted findings
gcloud scc findings list \
  --organization="{{user.org_id}}" \
  --filter='mute="MUTED"' \
  --limit=20 --format=json

# Diagnose mute config coverage
gcloud scc mute-configs list-mute-findings "{{user.mute_config_id}}" \
  --organization="{{user.org_id}}" --format=json
```

## Notification Config Diagnosis

```bash
gcloud scc notifications describe "{{user.notification_config_id}}" \
  --organization="{{user.org_id}}" --format=json

# Verify topic exists and SCC service agent has publisher role
gcloud pubsub topics describe projects/$(gcloud config get-value project)/topics/$(echo "{{user.pubsub_topic}}" | grep -oP 'topics/\K[^/]+')
gcloud pubsub topics get-iam-policy "$(echo "{{user.pubsub_topic}}" | grep -oP '^projects/[^/]+/topics/\K.+')"
```

[VERIFY: exact command for topic IAM check — local gcloud version may require specific format.]

## BigQuery Export Diagnosis

```bash
gcloud scc big-query-exports describe "{{user.bigquery_export_id}}" \
  --organization="{{user.org_id}}" --format=json

# Verify SCC service agent has BQ Data Editor
gcloud bigquery datasets describe "$(echo "{{user.bq_dataset}}" | grep -oP 'datasets/\K[^/]+')" \
  --project="$(echo "{{user.bq_dataset}}" | grep -oP 'projects/\K[^/]+')" --format=json
```

## Custom Module Diagnosis

```python
# Use SDK to get module enablement state
from google.cloud import securitycenter_v2
client = securitycenter_v2.SecurityCenterClient()
module = client.get_security_health_analytics_custom_module(
    name="organizations/{{user.org_id}}/locations/global/customModules/{{user.custom_module_id}}"
)
print({"name": module.name, "enablement_state": module.enablement_state})
```

## Recovery Rules

| Situation | Rule |
|-----------|------|
| Permission fix needed | Explain exact principal + role + resource; delegate broad IAM changes to `gcp-iam-ops` |
| Pub/Sub topic missing | Delegate topic creation to `gcp-pubsub-ops`; retry SCC config create after |
| BigQuery dataset missing | Delegate dataset creation to `gcp-bigquery-ops`; retry SCC BQ export create after |
| SCC not enabled | Enable SCC at org/project with explicit acknowledgement; warn about billing |
| Filter syntax error | Show correct filter syntax with examples; do not proceed with malformed filter |
| Finding state mutation silently ignored | Check current finding state first; if already at target, report and skip |