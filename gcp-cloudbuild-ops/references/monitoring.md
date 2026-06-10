---
name: cloudbuild-monitoring
description: Monitoring, logging, dashboards, and alerting guidance for Cloud Build

<!---
load_condition: "[用户询问监控/告警时加载]"
token_cost_estimate: "~600 tokens"
dependencies: []
--->
---

# Monitoring — Cloud Build

## Observability Sources

| Source | Use |
|--------|-----|
| Build metadata | Status, timing, images, artifacts, service account, worker pool |
| Build logs | Step output and failure evidence; redact secrets |
| Cloud Logging | Query build logs and audit logs across projects |
| Cloud Monitoring | Alert on failure rates, queueing, duration where metrics are available |
| Audit Logs | Trigger/worker pool create/update/delete traceability |

## Build Status Queries

```bash
gcloud builds list --filter='status=FAILURE' --limit=20 --format=json
gcloud builds list --filter='createTime>="{{user.start_time}}"' --limit=100 --format=json
```

## Cloud Logging Queries

Use Cloud Logging for cross-build diagnosis. Example filter:

```text
resource.type="build"
resource.labels.build_id="{{user.build_id}}"
```

Audit mutation filter:

```text
protoPayload.serviceName="cloudbuild.googleapis.com"
(protoPayload.methodName:"CreateBuildTrigger" OR protoPayload.methodName:"UpdateBuildTrigger" OR protoPayload.methodName:"DeleteBuildTrigger" OR protoPayload.methodName:"WorkerPool")
```

## Recommended Alerts

| Alert | Signal | Response |
|-------|--------|----------|
| Build failure spike | Failure count/rate above baseline | Diagnose common failing trigger/step |
| Queue delay | `createTime` to `startTime` exceeds SLO | Check quotas/private pool capacity |
| Timeout increase | `TIMEOUT` builds appear | Inspect long steps/dependency slowness |
| Worker pool unavailable | Pool state not usable or builds expired | Check network/quota/region |
| Trigger mutation | Audit log create/update/delete | Verify approved change/GCL trace |

## Dashboard Panels

- Builds by status over time.
- P50/P95 build duration and queue duration.
- Top failing triggers/build configs.
- Worker pool utilization proxy: queued builds and active builds by pool.
- Artifact push failures and permission-denied counts.

## Log Safety

- Redact tokens, passwords, private keys, Git credentials, and secret substitution values.
- Prefer evidence snippets over full logs.
- Do not export logs containing secrets to public/shared storage.
