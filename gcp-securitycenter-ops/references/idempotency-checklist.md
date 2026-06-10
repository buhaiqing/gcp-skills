<!---
load_condition: "[执行重试/幂等操作时加载]"
token_cost_estimate: "~600 tokens"
dependencies: []
--->

# Idempotency Checklist — Security Command Center

## Global Checklist

- [ ] Identify whether operation is read-only, state-changing, or destructive.
- [ ] Capture parent path (org/folder/project) and resource ID before mutation.
- [ ] Use describe to avoid duplicate mute configs, notification configs, or BQ exports.
- [ ] Require exact confirmation before delete.
- [ ] Redact credentials/secrets from trace.
- [ ] Validate final state with `--format=json`.

## Findings

| Operation | Idempotency rule |
|-----------|------------------|
| List/Describe | Idempotent read-only |
| Update state (INACTIVE) | Re-applying `INACTIVE` is idempotent; describe first, then update if not already target |
| Set mute (MUTED) | Re-muting is idempotent; describe first, then set if not already muted |
| Unmute (UNMUTED) | Re-unmuting is idempotent; describe first, then clear if not already unmuted |

## Mute Configs

- [ ] Describe by ID before create; if `ALREADY_EXISTS`, update the existing config.
- [ ] For update, compare desired filter to current filter; skip if already matching.
- [ ] For delete, require `{{user.confirm_delete}} == {{user.mute_config_id}}`; treat `NOT_FOUND` as successful final state only after confirmation captured.
- [ ] Note: muting a finding is not the same as deleting a mute config — muted findings remain visible in SCC.

## Notification Configs

- [ ] Describe by ID before create; if `ALREADY_EXISTS`, update or skip.
- [ ] For update, compare desired filter and topic to current values; skip if already matching.
- [ ] For delete, require `{{user.confirm_delete}} == {{user.notification_config_id}}`; treat `NOT_FOUND` as successful final state only after confirmation captured.
- [ ] Deleting a notification config does not delete the Pub/Sub topic.

## BigQuery Exports

- [ ] Describe by ID before create; if `ALREADY_EXISTS`, update or skip.
- [ ] For update, compare desired filter and dataset to current values; skip if already matching.
- [ ] For delete, require `{{user.confirm_delete}} == {{user.bigquery_export_id}}`; treat `NOT_FOUND` as successful final state only after confirmation captured.
- [ ] Deleting a BQ export does **not** drop the existing BigQuery tables; it only stops the continuous export.

## Custom Modules

- [ ] Describe module before enable/disable; skip if already in desired state.
- [ ] `ENABLED`/`DISABLED`/`INHERITED` are the three states; check current before apply.
- [ ] Effective modules are read-only; cannot be directly mutated — must change the underlying custom module.

## Resource Value Configs

- [ ] Describe by ID before create; if `ALREADY_EXISTS`, update or skip.
- [ ] For update, compare desired resource name and severity to current values; skip if already matching.
- [ ] For delete, require exact ID confirmation.

## Retry Policy

| Error | Retry? | Conditions |
|-------|--------|------------|
| `UNAVAILABLE` | Yes | Exponential backoff; operation is read-only or confirmed idempotent |
| `INTERNAL` | Yes | Exponential backoff; preserve trace |
| `DEADLINE_EXCEEDED` | Maybe | Retry for read-only; for write, describe current state first |
| `RESOURCE_EXHAUSTED` | Later | Wait; reduce call frequency; request quota if persistent |
| `PERMISSION_DENIED` | No | Fix IAM first |
| `NOT_FOUND` on delete | N/A | Already gone — confirm with describe/list |
| `ALREADY_EXISTS` on create | N/A | Describe and update instead |
| `FAILED_PRECONDITION` | No | Fix precondition (enable SCC, create dataset, create topic) first |
| Invalid filter syntax | No | Fix filter first |