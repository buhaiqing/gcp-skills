<!---
load_condition: "[用户询问监控/告警时加载]"
token_cost_estimate: "~700 tokens"
dependencies: []
--->

# Monitoring — Security Command Center

## Observability Sources

| Source | Use |
|--------|-----|
| SCC Findings API | State, severity, category, resource, event_time, mute status |
| Cloud Logging | SCC audit logs for mute config, notification config, BQ export, module mutations |
| Cloud Monitoring | SCC-specific metrics for finding count, severity score |
| BigQuery exports | Historical finding trends in exported tables |
| Pub/Sub notifications | Real-time alert routing and automation triggers |

## Finding Status Queries

```bash
# Active critical findings count
gcloud scc findings list --organization="{{user.org_id}}" \
  --filter='state="ACTIVE" AND severity="CRITICAL"' \
  --limit=100 --format=json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('totalSize',len(d.get('results',[]))))"

# High-severity findings trend over time
gcloud scc findings list --organization="{{user.org_id}}" \
  --filter='state="ACTIVE" AND severity="HIGH"' \
  --limit=500 --format=json

# Muted findings coverage
gcloud scc findings list --organization="{{user.org_id}}" \
  --filter='mute="MUTED"' \
  --limit=100 --format=json
```

## Cloud Logging Queries

SCC audit log filter:

```
protoPayload.serviceName="securitycenter.googleapis.com"
(protoPayload.methodName:"CreateMuteConfig" OR protoPayload.methodName:"DeleteMuteConfig" OR protoPayload.methodName:"CreateNotificationConfig" OR protoPayload.methodName:"DeleteNotificationConfig" OR protoPayload.methodName:"CreateBigQueryExport" OR protoPayload.methodName:"DeleteBigQueryExport" OR protoPayload.methodName:"UpdateFinding" OR protoPayload.methodName:"SetMute" OR protoPayload.methodName:"EnableSecurityCenter")
```

Finding state change filter:

```
resource.type="securitycenter_resource"
resource.labels.organization="123456789012"
protoPayload.serviceName="securitycenter.googleapis.com"
protoPayload.methodName:"UpdateFinding"
```

## Cloud Monitoring Metrics

[VERIFY: current metric names and exact format — Google may have updated the metric schema for SCC v2.]

Common metrics:
- `securitycenter.googleapis.com/finding/count` — total active findings by state/severity/category
- `securitycenter.googleapis.com/finding/severity_score` — weighted severity sum

Query example:

```bash
# List available SCC metrics
gcloud monitoring metrics list \
  --filter='metric.type:securitycenter' --format=json
```

## Recommended Alerts

| Alert | Signal | Response |
|-------|--------|----------|
| Critical findings spike | Critical finding count > baseline threshold | Triage new critical findings; check mute configs |
| High-severity findings accumulation | High finding count growing week-over-week | Review source coverage; check detector enablement |
| Mute config created | Audit log `CreateMuteConfig` | Verify approved mute rule; check no critical findings suppressed |
| Notification config deleted | Audit log `DeleteNotificationConfig` | Re-create or investigate intentional deletion |
| SCC disablement attempt | Audit log `DisableSecurityCenter` | Alert SOC immediately; verify authorized action |
| BigQuery export stopped | Notification or audit log for BQ export deletion | Re-create export; verify dataset/service agent IAM |
| Custom module disabled | Audit log or metric drop in detector output | Re-enable module; verify module configuration |

## Dashboard Panels

- Active findings by severity (CRITICAL/HIGH/MEDIUM/LOW) over time.
- New findings per day by category.
- Muted vs active findings ratio.
- Top resources by finding count.
- Notification config Pub/Sub publish rate.
- BigQuery export write latency and row count.

## Log Safety

- Redact finding descriptions that may contain resource paths, IP addresses, or bucket names if reporting publicly.
- Never export finding logs containing credential material to shared storage.
- Filter audit logs for sensitive principals before sharing.