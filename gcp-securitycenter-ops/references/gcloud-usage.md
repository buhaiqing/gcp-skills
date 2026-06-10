---
name: securitycenter-gcloud-usage
description: gcloud command map for Security Command Center settings, sources, findings, mute configs, notification configs, and BigQuery exports

<!---
load_condition: "[执行 CLI 操作时加载]"
token_cost_estimate: "~1500 tokens"
dependencies: ["references/api-sdk-usage.md"]
--->
---

# gcloud Usage — Security Command Center

All commands use sanitized parameters. Prefer `--format=json` for machine parsing. For organization-level operations, the agent identity must have SCC roles at the org level; use `--organization={{user.org_id}}` (or `--folder` / `--project` for the appropriate scope).

## Pre-flight

```bash
gcloud version
gcloud config get-value project
gcloud services list --enabled --filter='config.name=securitycenter.googleapis.com' --format='value(config.name)'
gcloud scc settings get --organization="{{user.org_id}}" --format=json
gcloud scc findings list --organization="{{user.org_id}}" --limit=1 --format=json
```

## Settings (Enable / Get)

```bash
# Get organization-level SCC settings (enablement + asset discovery)
gcloud scc settings get --organization="{{user.org_id}}" --format=json

# Enable SCC at organization level
gcloud scc settings enable --organization="{{user.org_id}}" --format=json

# Enable SCC at project level
gcloud scc settings enable --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

Notes:
- `enable` is GCL `required` because it has billing and posture-scope impact.
- For Premium/Enterprise detectors, additional enablement commands may apply at the org level — verify against current tier documentation.

## Sources

```bash
# List all sources at org level
gcloud scc sources list --organization="{{user.org_id}}" --format=json

# Describe a specific source
gcloud scc sources describe "{{user.source_id}}" \
  --organization="{{user.org_id}}" --format=json

# Update source display name
gcloud scc sources update "{{user.source_id}}" \
  --organization="{{user.org_id}}" \
  --display-name="<new-name>" --format=json
```

Notes:
- Sources are typically auto-created when detectors run; user-driven source create is via the SDK/REST (custom sources).
- `update` is GCL `recommended`; show current vs new display name before apply.

## Findings

```bash
# List findings with a filter
gcloud scc findings list \
  --organization="{{user.org_id}}" \
  --source="{{user.source_id}}" \
  --filter='{{user.filter}}' \
  --limit="{{user.limit}}" \
  --format=json

# Describe a specific finding
gcloud scc findings describe "{{user.finding_id}}" \
  --organization="{{user.org_id}}" \
  --source="{{user.source_id}}" --format=json

# Update finding state (mark as ACTIVE/INACTIVE)
gcloud scc findings update-state \
  --organization="{{user.org_id}}" \
  --source="{{user.source_id}}" \
  --finding="{{user.finding_id}}" \
  --state="{{user.new_state}}" \
  --format=json

# Update finding mute state (set/unset mute)
gcloud scc findings update-mute \
  --organization="{{user.org_id}}" \
  --source="{{user.source_id}}" \
  --finding="{{user.finding_id}}" \
  --mute=MUTED \
  --format=json

# Export findings to CSV
gcloud scc findings export \
  --organization="{{user.org_id}}" \
  --source="{{user.source_id}}" \
  --filter='{{user.filter}}' \
  --destination="{{user.csv_destination}}" \
  --format=json
```

Common filter examples:
- `state="ACTIVE"`
- `state="ACTIVE" AND severity="HIGH"`
- `category="OPEN_FIREWALL" AND resource_name:"projects/*/instances/web"`
- `event_time>="2026-05-01T00:00:00Z"`

Notes:
- `update-state` and `update-mute` are GCL `required` because they affect alerting and posture dashboards.
- Show the current state/mute before mutation; require explicit confirmation for production-impacting state changes.

## Mute Configs

```bash
# List mute configs at org level
gcloud scc mute-configs list --organization="{{user.org_id}}" --format=json

# Describe a specific mute config
gcloud scc mute-configs describe "{{user.mute_config_id}}" \
  --organization="{{user.org_id}}" --format=json

# Create a mute config
gcloud scc mute-configs create "{{user.mute_config_id}}" \
  --organization="{{user.org_id}}" \
  --description="Mute dev sandbox findings" \
  --filter='resource_name:"projects/dev-sandbox-*" AND severity="LOW"' \
  --type=DYNAMIC \
  --format=json

# Delete a mute config (require {{user.confirm_delete}} == {{user.mute_config_id}})
gcloud scc mute-configs delete "{{user.mute_config_id}}" \
  --organization="{{user.org_id}}" --quiet

# List currently-muted findings for a config
gcloud scc mute-configs list-mute-findings "{{user.mute_config_id}}" \
  --organization="{{user.org_id}}" --format=json
```

Notes:
- Mute config ID must be 1-20 characters matching `[a-zA-Z0-9-_]`.
- `--type=DYNAMIC` evaluates the filter at query time (most common); `--type=STATIC` mutes a specific set of findings (less common, requires explicit finding names).
- Delete is GCL `required` — confirmation must equal mute config ID.

## Notification Configs

```bash
# List notification configs
gcloud scc notifications list --organization="{{user.org_id}}" --format=json

# Describe a notification config
gcloud scc notifications describe "{{user.notification_config_id}}" \
  --organization="{{user.org_id}}" --format=json

# Create a notification config
gcloud scc notifications create "{{user.notification_config_id}}" \
  --organization="{{user.org_id}}" \
  --description="High-severity findings to SOC topic" \
  --pubsub-topic="{{user.pubsub_topic}}" \
  --filter='state="ACTIVE" AND (severity="HIGH" OR severity="CRITICAL")' \
  --format=json

# Update a notification config
gcloud scc notifications update "{{user.notification_config_id}}" \
  --organization="{{user.org_id}}" \
  --description="Updated description" \
  --filter='state="ACTIVE" AND severity="CRITICAL"' \
  --format=json

# Delete a notification config (require {{user.confirm_delete}} == {{user.notification_config_id}})
gcloud scc notifications delete "{{user.notification_config_id}}" \
  --organization="{{user.org_id}}" --quiet

Notes:
- The Pub/Sub topic must exist and the SCC service agent must have `roles/pubsub.publisher` on it.
- Delete is GCL `required` — confirmation must equal notification config ID.

## BigQuery Exports

```bash
# List BigQuery exports
gcloud scc big-query-exports list --organization="{{user.org_id}}" --format=json

# Describe a BigQuery export
gcloud scc big-query-exports describe "{{user.bigquery_export_id}}" \
  --organization="{{user.org_id}}" --format=json

# Create a BigQuery export
gcloud scc big-query-exports create "{{user.bigquery_export_id}}" \
  --organization="{{user.org_id}}" \
  --dataset="{{user.bq_dataset}}" \
  --description="Continuous export to SOC dataset" \
  --filter='state="ACTIVE"' \
  --format=json

# Update a BigQuery export
gcloud scc big-query-exports update "{{user.bigquery_export_id}}" \
  --organization="{{user.org_id}}" \
  --description="Updated filter" \
  --filter='state="ACTIVE" AND (severity="HIGH" OR severity="CRITICAL")' \
  --format=json

# Delete a BigQuery export (require {{user.confirm_delete}} == {{user.bigquery_export_id}})
gcloud scc big-query-exports delete "{{user.bigquery_export_id}}" \
  --organization="{{user.org_id}}" --quiet
```

Notes:
- The BigQuery dataset must exist and the SCC service agent must have BigQuery Data Editor on it.
- Delete is GCL `required` — confirmation must equal export ID. Note: delete **does not** drop the exported tables, only stops the export.

## Diagnostic Logging Pattern

When wrapping commands in scripts, emit structured logs:

```bash
printf '[%(%H:%M:%S)T] [DIAG] action=list_findings parent=%s filter=%s\n' -1 "{{user.parent}}" "{{user.filter}}"
# command here
printf '[%(%H:%M:%S)T] [RESULT] total=%s next_token=%s\n' -1 "${TOTAL}" "${NEXT_TOKEN}"
```

Use `[ERROR] TYPE={category} FIX={action}` for failures and never print credentials.
