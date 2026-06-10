---
name: securitycenter-api-sdk-usage
description: Security Command Center API and Python/Go SDK usage patterns for findings, sources, mute configs, notification configs, BigQuery exports, custom modules, and resource value configs

<!---
load_condition: "[SDK/API fallback 或 custom modules / resource value configs 时加载]"
token_cost_estimate: "~1400 tokens"
dependencies: ["references/troubleshooting.md"]
--->
---

# API/SDK Usage — Security Command Center

Use the SDK/API when structured automation is preferred, `gcloud scc` is unavailable, or the operation is CLI-only (custom modules, effective modules, resource value configs). Python SDK reads ADC from the environment; do not print credential paths or credential objects.

## Install/Import

```bash
python3 -m pip install --user google-cloud-securitycenter_v2
```

```python
from google.cloud import securitycenter_v2
```

> The v1 client is the legacy API. The v2 client (and its big-query-export, mute-config, notification-config subclients) is the recommended API for current SCC resources. Use v2 unless the operation specifically requires v1.

## Client Setup

```python
from google.cloud import securitycenter_v2

parent = "organizations/{{user.org_id}}"
client = securitycenter_v2.SecurityCenterClient()
```

For BigQuery exports, mute configs, and notification configs, use the dedicated subclients:

```python
from google.cloud import securitycenter_v2

mute_client = securitycenter_v2.MuteConfigsClient()
notif_client = securitycenter_v2.NotificationConfigsClient()
bqe_client = securitycenter_v2.BigQueryExportsClient()
```

## List and Describe Findings

```python
from google.cloud import securitycenter_v2

client = securitycenter_v2.SecurityCenterClient()
parent = "organizations/{{user.org_id}}/sources/-"
request = securitycenter_v2.ListFindingsRequest(
    parent=parent,
    filter='{{user.filter}}',  # e.g. 'state="ACTIVE" AND severity="HIGH"'
    page_size=100,
)
for finding_result in client.list_findings(request=request):
    f = finding_result.finding
    print({
        "name": f.name,
        "state": securitycenter_v2.Finding.State(f.state).name,
        "severity": securitycenter_v2.Finding.Severity(f.severity).name,
        "category": f.category,
        "resource_name": f.resource_name,
        "event_time": str(f.event_time),
    })
```

Describe a single finding:

```python
finding = client.get_finding(
    name="organizations/{{user.org_id}}/sources/{{user.source_id}}/findings/{{user.finding_id}}"
)
print({
    "name": finding.name,
    "state": securitycenter_v2.Finding.State(finding.state).name,
    "external_uri": finding.external_uri,
})
```

## Update Finding State

```python
from google.cloud import securitycenter_v2
from google.protobuf import field_mask_pb2

client = securitycenter_v2.SecurityCenterClient()
name = "organizations/{{user.org_id}}/sources/{{user.source_id}}/findings/{{user.finding_id}}"

# Get current finding to preserve other fields
finding = client.get_finding(name=name)
finding.state = securitycenter_v2.Finding.State.INACTIVE

request = securitycenter_v2.UpdateFindingRequest(
    finding=finding,
    update_mask=field_mask_pb2.FieldMask(paths=["state"]),
)
updated = client.update_finding(request=request)
print({"name": updated.name, "state": securitycenter_v2.Finding.State(updated.state).name})
```

## Set Mute State on a Finding

```python
# Set mute
client.set_mute(
    name="organizations/{{user.org_id}}/sources/{{user.source_id}}/findings/{{user.finding_id}}",
    mute=securitycenter_v2.Finding.Mute.MUTED,
)

# Unmute
client.set_mute(
    name="organizations/{{user.org_id}}/sources/{{user.source_id}}/findings/{{user.finding_id}}",
    mute=securitycenter_v2.Finding.Mute.UNMUTED,
)
```

## Mute Configs (Subclient)

```python
from google.cloud import securitycenter_v2

mute_client = securitycenter_v2.MuteConfigsClient()
parent = "organizations/{{user.org_id}}"
mute = securitycenter_v2.MuteConfig(
    description="Mute dev sandbox low-severity findings",
    filter='resource_name:"projects/dev-sandbox-*" AND severity="LOW"',
    type_=securitycenter_v2.MuteConfig.MuteType.DYNAMIC,
)
created = mute_client.create_mute_config(
    parent=parent, mute_config=mute, mute_config_id="{{user.mute_config_id}}"
)
print({"name": created.name})
```

## Notification Configs (Subclient)

```python
from google.cloud import securitycenter_v2

notif_client = securitycenter_v2.NotificationConfigsClient()
parent = "organizations/{{user.org_id}}"
ncfg = securitycenter_v2.NotificationConfig(
    description="SOC topic for high-severity",
    pubsub_topic="{{user.pubsub_topic}}",
    filter='state="ACTIVE" AND (severity="HIGH" OR severity="CRITICAL")',
    streaming_config=securitycenter_v2.NotificationConfig.StreamingConfig(streaming_update=...),
)
created = notif_client.create_notification_config(
    parent=parent, notification_config=ncfg, notification_config_id="{{user.notification_config_id}}"
)
print({"name": created.name})
```

[VERIFY: the exact `streaming_config` payload for current SDK versions — it carries a oneof between `streaming_update` and `streaming_update_time` and the structure varies across releases.]

## BigQuery Exports (Subclient)

```python
from google.cloud import securitycenter_v2

bqe_client = securitycenter_v2.BigQueryExportsClient()
parent = "organizations/{{user.org_id}}"
export = securitycenter_v2.BigQueryExport(
    description="Continuous export to SOC dataset",
    dataset="{{user.bq_dataset}}",
    filter='state="ACTIVE"',
)
created = bqe_client.create_big_query_export(
    parent=parent, big_query_export=export, big_query_export_id="{{user.bigquery_export_id}}"
)
print({"name": created.name, "dataset": created.dataset})
```

## Custom Modules

```python
from google.cloud import securitycenter_v2
from google.protobuf import field_mask_pb2

client = securitycenter_v2.SecurityCenterClient()
parent = "organizations/{{user.org_id}}/locations/global"

# List
for module in client.list_security_health_analytics_custom_modules(parent=parent):
    print({"name": module.name, "enablement_state": module.enablement_state})

# Enable
module = client.get_security_health_analytics_custom_module(name=f"{parent}/customModules/{{user.custom_module_id}}")
module.enablement_state = securitycenter_v2.SecurityHealthAnalyticsCustomModule.EnablementState.ENABLED
update_mask = field_mask_pb2.FieldMask(paths=["enablement_state"])
client.update_security_health_analytics_custom_module(
    security_health_analytics_custom_module=module,
    update_mask=update_mask,
)
```

## Effective Modules

```python
# List effective modules at a folder or project
parent_eff = "folders/{{user.folder_id}}/locations/global"
for em in client.list_effective_security_health_analytics_custom_modules(parent=parent_eff):
    print({"name": em.name, "enablement_state": em.enablement_state})

# Get the effective state of a specific module
em = client.get_effective_security_health_analytics_custom_module(
    name=f"{parent_eff}/effectiveCustomModules/{{user.custom_module_id}}"
)
```

## Resource Value Configs

```python
from google.cloud import securitycenter_v2

client = securitycenter_v2.SecurityCenterClient()
parent = "organizations/{{user.org_id}}"

# List
for rvc in client.list_resource_value_configs(parent=parent):
    print({"name": rvc.name, "resource_value": rvc.resource_value})

# Create
rvc = securitycenter_v2.ResourceValueConfig(
    resource_name="{{user.resource_name}}",
    resource_value=securitycenter_v2.ResourceValue.ResourceValueEnum.HIGH,
    tag="prod-critical",
)
created = client.create_resource_value_config(
    parent=parent, resource_value_config=rvc, resource_value_config_id="{{user.resource_value_config_id}}"
)
print({"name": created.name})
```

[VERIFY: `ResourceValue.ResourceValueEnum` exact symbol across SDK releases; some versions use `HIGH` as integer and others as enum.]

## REST Patterns

```bash
ACCESS_TOKEN="$(gcloud auth print-access-token)"

# List findings (v1 API)
curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://securitycenter.googleapis.com/v1/organizations/{{user.org_id}}/sources/-/findings?filter=state%3D%22ACTIVE%22"

# Describe notification config
curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://securitycenter.googleapis.com/v2/organizations/{{user.org_id}}/notificationConfigs/{{user.notification_config_id}}"
```

Never echo `${ACCESS_TOKEN}`. Store REST traces with headers redacted.

## Pagination

- CLI: use `--limit` and `--page-size` where available.
- SDK: iterate pagers; do not assume all findings/configs fit in one page.
- REST: follow `nextPageToken`.

## Error Handling

Map API exceptions/statuses to [troubleshooting.md](troubleshooting.md#error-taxonomy). Retry only transient `UNAVAILABLE`, `DEADLINE_EXCEEDED`, and `INTERNAL` conditions with backoff; do not retry destructive operations without explicit user re-confirmation.
