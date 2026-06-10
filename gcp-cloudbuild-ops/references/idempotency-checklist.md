---
name: cloudbuild-idempotency-checklist
description: Idempotency and retry checklist for Cloud Build operations

<!---
load_condition: "[执行重试/幂等操作时加载]"
token_cost_estimate: "~600 tokens"
dependencies: []
--->
---

# Idempotency Checklist — Cloud Build

## Global Checklist

- [ ] Identify whether operation is read-only, mutating metadata, or executing build steps.
- [ ] Capture project, region, resource ID, and current state before mutation.
- [ ] Use describe/list to avoid duplicate triggers or worker pools.
- [ ] Require exact confirmation before delete.
- [ ] Redact credentials/secrets from trace.
- [ ] Validate final state with `--format=json`.

## Builds

| Operation | Idempotency rule |
|-----------|------------------|
| Submit | Not inherently idempotent; build steps may deploy/push/delete |
| Describe/List | Idempotent read-only |
| Cancel | Idempotent if final `CANCELLED` or already terminal is accepted and reported |
| Retry | Not inherently idempotent; require approval for production-impacting steps |

Before retry/submit, inspect build config for deployment steps, destructive commands, image tags like `latest`, and external side effects.

## Triggers

- [ ] List triggers and match by name, source repo, branch/tag pattern, and config path.
- [ ] If same desired trigger exists, do not create duplicate.
- [ ] For update, compare desired config to current config and report changed fields.
- [ ] For run, treat as build execution and apply build idempotency rules.
- [ ] For delete, require `{{user.confirm_delete}} == {{user.trigger_id}}` and validate not found after deletion.

## Private Worker Pools

- [ ] Use region-specific list/describe before create.
- [ ] Compare desired `workerConfig` and `networkConfig` before update.
- [ ] Avoid update/delete while pool is already updating/deleting unless final state is known.
- [ ] Check triggers/build configs referencing the pool before delete when feasible.
- [ ] Treat `NOT_FOUND` after delete as successful final state only after confirmation was captured.

## Retry Policy

| Error | Retry? | Conditions |
|-------|--------|------------|
| `UNAVAILABLE` | Yes | Exponential backoff; operation idempotent or approved |
| `INTERNAL_ERROR` build status | Maybe | Retry only if build steps idempotent |
| `RESOURCE_EXHAUSTED` | Later | Wait/reduce concurrency/request quota |
| `PERMISSION_DENIED` | No | Fix IAM first |
| Invalid config/source | No | Fix config/source first |
| Trigger/worker pool delete | No blind retry | Confirm target and final state |
