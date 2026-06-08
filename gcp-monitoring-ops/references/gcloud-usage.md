# gcloud Usage — Cloud Monitoring

## Overview

`gcloud monitoring` is the primary CLI for Cloud Monitoring operations. All commands support `--format=json` for machine parsing.

## Conventions

| Convention | Rule |
|-----------|------|
| Output | Always use `--format=json` |
| Project | `--project="{{env.CLOUDSDK_CORE_PROJECT}}"` or env var |
| Pagination | `--limit=N` limits results; default 100 |
| jq | Use for extracting fields from JSON output |

## Command Map

### Metrics

| Operation | Command |
|-----------|---------|
| List metric descriptors | `gcloud monitoring metrics list --project=PROJECT --format=json` |
| List with filter | `gcloud monitoring metrics list --filter="metric.type='compute.googleapis.com/instance/cpu/utilization'" --project=PROJECT` |
| List time series (REST) | `curl -H "Authorization: Bearer $(gcloud auth print-access-token)" "https://monitoring.googleapis.com/v3/projects/PROJECT/timeSeries?filter=..."` |
| Describe metric descriptor | `gcloud monitoring metrics describe METRIC_TYPE --project=PROJECT` |

### Alert Policies

| Operation | Command |
|-----------|---------|
| List | `gcloud monitoring alert-policies list --project=PROJECT --format=json` |
| Describe | `gcloud monitoring alert-policies describe POLICY_ID --project=PROJECT --format=json` |
| Create | `gcloud monitoring alert-policies create NAME --display-name=DISPLAY --condition-display-name=COND --condition-filter=FILTER --condition-threshold-value=VALUE --condition-threshold-duration=DUR --format=json` |
| Update | `gcloud monitoring alert-policies update POLICY_ID --enabled=BOOL --project=PROJECT --format=json` |
| Delete | `gcloud monitoring alert-policies delete POLICY_ID --project=PROJECT --quiet` |
| List with filter | `gcloud monitoring alert-policies list --filter="enabled.value=true" --project=PROJECT` |

### Notification Channels

| Operation | Command |
|-----------|---------|
| List | `gcloud monitoring channels list --project=PROJECT --format=json` |
| Describe | `gcloud monitoring channels describe CHANNEL_ID --project=PROJECT --format=json` |
| Create (email) | `gcloud monitoring channels create --display-name=NAME --type=email --channel-labels=email_address=ADDR --project=PROJECT --format=json` |
| Create (slack) | `gcloud monitoring channels create --display-name=NAME --type=slack --channel-labels=channel_name=#CHANNEL,auth_token=TOKEN --project=PROJECT` |
| Create (webhook) | `gcloud monitoring channels create --display-name=NAME --type=webhook --channel-labels=url=URL --project=PROJECT` |
| Update | `gcloud monitoring channels update CHANNEL_ID --channel-labels=KEY=VAL --project=PROJECT` |
| Delete | `gcloud monitoring channels delete CHANNEL_ID --project=PROJECT --quiet` |
| Verify | `gcloud monitoring channels send-verification-code CHANNEL_ID --project=PROJECT` |

### Dashboards

| Operation | Command |
|-----------|---------|
| List | `gcloud monitoring dashboards list --project=PROJECT --format=json` |
| Describe | `gcloud monitoring dashboards describe DASHBOARD_ID --project=PROJECT --format=json` |
| Create (from file) | `gcloud monitoring dashboards create --project=PROJECT --config-from-file=FILE.json` |
| Update (from file) | `gcloud monitoring dashboards update DASHBOARD_ID --project=PROJECT --config-from-file=FILE.json` |
| Delete | `gcloud monitoring dashboards delete DASHBOARD_ID --project=PROJECT --quiet` |

### Uptime Checks

| Operation | Command |
|-----------|---------|
| List | `gcloud monitoring uptime list --project=PROJECT --format=json` |
| Describe | `gcloud monitoring uptime describe CONFIG_ID --project=PROJECT --format=json` |
| Create (HTTP) | `gcloud monitoring uptime create NAME --display-name=DISPLAY --hostname=HOST --check-type=HTTP --period=SECS --timeout=SECS --project=PROJECT` |
| Create (HTTPS) | `gcloud monitoring uptime create NAME --hostname=HOST --check-type=HTTPS --project=PROJECT` |
| Create (TCP) | `gcloud monitoring uptime create NAME --hostname=HOST --port=PORT --check-type=TCP --project=PROJECT` |
| Delete | `gcloud monitoring uptime delete CONFIG_ID --project=PROJECT --quiet` |
| List check IPs | `gcloud monitoring uptime ips --format=json` |

### Alert Policy Silencing

| Operation | Command |
|-----------|---------|
| List incidents | `gcloud monitoring incidents list --project=PROJECT --format=json` |
| Silence alert | `gcloud monitoring alert-policies update POLICY_ID --enabled=false --project=PROJECT` |
| Unsilence | `gcloud monitoring alert-policies update POLICY_ID --enabled=true --project=PROJECT` |

## Common jq Patterns

| Task | jq Expression |
|------|---------------|
| Get alert policy names | `.[] \| .displayName` |
| Get enabled policies | `.[] \| select(.enabled.value == true) \| .displayName` |
| Extract channel types | `.[] \| {name: .name, type: .type}` |
| Dashboard widget count | `.gridLayout.widgets \| length` |
| Uptime check config details | `{name, displayName, period, timeout, checkType}` |
| Alert policy condition filters | `.conditions[] \| {displayName, filter: .conditionThreshold.filter}` |
| Time series values | `.timeSeries[] \| {metric: .metric.type, points: [.points[].value.double_value]}` |

## CLI vs API Coverage

| Resource | gcloud Coverage | Notes |
|----------|----------------|-------|
| Metrics | Full | list, describe; time series via REST |
| Alert Policies | Full | CRUD, enable/disable |
| Notification Channels | Full | CRUD, verification |
| Dashboards | Full | CRUD via JSON config files |
| Uptime Checks | Full | CRUD, IP list |
| SLOs | Partial | Limited CLI; API preferred |
| Groups | Partial | API preferred |
| Services | Partial | API preferred |

## Detailed Execution Flows

Every operation: **Pre-flight → Execute → Validate → Recover**. Full scripts below.

### Operation: Query Time-Series Metrics

#### Pre-flight Checks (additional)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Metric type | Known from `gcloud monitoring metrics list` | Valid metric type | List available metrics first |
| Time range | User-provided or default (last 1h) | `< end_time > start_time` | Default to last 1 hour |

#### Execution

```bash
# Query CPU utilization for all instances (last 1 hour)
gcloud monitoring metrics list \
  --filter="metric.type = 'compute.googleapis.com/instance/cpu/utilization'" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Read time series with specific parameters (via REST with access token)
curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://monitoring.googleapis.com/v3/projects/{{env.CLOUDSDK_CORE_PROJECT}}/timeSeries?filter=metric.type%3D%22compute.googleapis.com%2Finstance%2Fcpu%2Futilization%22&interval.startTime=2026-06-06T00:00:00Z&interval.endTime=2026-06-07T00:00:00Z" \
  | jq '.timeSeries[] | {resource: .resource.labels.instance_id, values: [.points[].value.double_value]}'
```

#### Python SDK

```python
# query_timeseries.py
import os
from datetime import datetime, timedelta
from google.cloud import monitoring_v3

project_id = os.environ["CLOUDSDK_CORE_PROJECT"]
client = monitoring_v3.MetricServiceClient()

now = datetime.utcnow()
interval = monitoring_v3.TimeInterval(
    end_time=now,
    start_time=now - timedelta(hours=1),
)
aggregation = monitoring_v3.Aggregation(
    alignment_period={"seconds": 300},
    per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
)

request = {
    "name": f"projects/{project_id}",
    "filter": "metric.type = 'compute.googleapis.com/instance/cpu/utilization'",
    "interval": interval,
    "aggregation": aggregation,
}
for page in client.list_time_series(request).pages:
    for ts in page.time_series:
        print(f"Metric: {ts.metric.type}")
        print(f"Resource: {ts.resource.labels}")
        for pt in ts.points:
            print(f"  Time: {pt.interval.end_time} Value: {pt.value.double_value}")
```

#### Go SDK

```go
// query_timeseries.go
package main

import (
	"context"
	"fmt"
	"os"
	"time"

	monitoring "cloud.google.com/go/monitoring/apiv3"
	"cloud.google.com/go/monitoring/apiv3/v2/monitoringpb"
	"google.golang.org/api/option"
	"google.golang.org/protobuf/types/known/timestamppb"
)

func main() {
	ctx := context.Background()
	client, err := monitoring.NewMetricClient(ctx,
		option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
	if err != nil {
		panic(err)
	}
	defer client.Close()

	project := os.Getenv("CLOUDSDK_CORE_PROJECT")
	end := time.Now()
	start := end.Add(-1 * time.Hour)

	req := &monitoringpb.ListTimeSeriesRequest{
		Name:   fmt.Sprintf("projects/%s", project),
		Filter: `metric.type = "compute.googleapis.com/instance/cpu/utilization"`,
		Interval: &monitoringpb.TimeInterval{
			StartTime: timestamppb.New(start),
			EndTime:   timestamppb.New(end),
		},
	}
	it := client.ListTimeSeries(ctx, req)
	for {
		ts, err := it.Next()
		if err != nil {
			break
		}
		fmt.Printf("Metric: %s | Resource: %v\n", ts.Metric.Type, ts.Resource.Labels)
		for _, p := range ts.Points {
			fmt.Printf("  Time: %s | Value: %v\n", p.Interval.EndTime.AsTime(), p.Value.GetDoubleValue())
		}
	}
}
```

#### Post-execution Validation
1. Verify `timeSeries` array is non-empty
2. For each series, confirm `points[]` has values in the expected time range
3. Report metric name, resource labels, and value ranges to the user

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|---------------|-------------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | 0 | HALT; fix metric type or filter | `[ERROR] INVALID_ARGUMENT: Invalid metric filter. Verify metric.type exists.` |
| `PERMISSION_DENIED` / 403 | 0 | HALT; check Monitoring IAM | `[ERROR] PERMISSION_DENIED: Missing monitoring.timeSeries.list permission.` |
| `UNAVAILABLE` / 503 | 3 (5s, 10s, 20s) | Backoff retry | `⚠️ Monitoring API temporarily unavailable. Retrying...` |
| `INTERNAL` / 500 | 3 (2s, 4s, 8s) | Retry; then HALT | `[ERROR] INTERNAL: Server error. Retry or create support case.` |

### Operation: Alert Policies (List/Create/Describe/Modify/Delete)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Alert policy name | `gcloud monitoring alert-policies list` | Unique name | Warn if name exists; ask user |
| Notification channel | `gcloud monitoring channels list` | Channel exists (optional) | Create channel first or skip |
| Metric type | `gcloud monitoring metrics list` | Valid metric | List available metrics |
| **Delete confirmation** | User must confirm with policy ID | Exact match | HALT — user must type exact policy ID |

#### Execution

```bash
# List
gcloud monitoring alert-policies list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Describe
gcloud monitoring alert-policies describe "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Create alert policy (CPU > 80% for 5 minutes)
gcloud monitoring alert-policies create "high-cpu-alert" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --display-name="High CPU Alert" \
  --condition-display-name="CPU > 80%" \
  --condition-filter='resource.type = "gce_instance" AND metric.type = "compute.googleapis.com/instance/cpu/utilization"' \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s \
  --notification-channels="{{user.channel_id}}" \
  --format="json"

# Modify (enable/disable)
gcloud monitoring alert-policies update "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --enabled=false \
  --format="json"

# Delete (Safety Gate — user must confirm)
gcloud monitoring alert-policies delete "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet
```

#### Python SDK

```python
# create_alert_policy.py
import os
from google.cloud import monitoring_v3

project_id = os.environ["CLOUDSDK_CORE_PROJECT"]
client = monitoring_v3.AlertPolicyServiceClient()

policy = monitoring_v3.AlertPolicy(
    display_name="High CPU Alert",
    combiner=monitoring_v3.AlertPolicy.Combiner.OR,
    conditions=[
        monitoring_v3.AlertPolicy.Condition(
            display_name="CPU > 80%",
            condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                filter='resource.type = "gce_instance" AND metric.type = "compute.googleapis.com/instance/cpu/utilization"',
                duration={"seconds": 300},
                threshold_value=0.8,
                comparison=monitoring_v3.ComparisonType.COMPARISON_GT,
            ),
        )
    ],
    notification_channels=[os.getenv("NOTIFICATION_CHANNEL", "")],
)

request = monitoring_v3.CreateAlertPolicyRequest(
    name=f"projects/{project_id}",
    alert_policy=policy,
)
resp = client.create_alert_policy(request)
print(f"Created: {resp.name}")
```

#### Go SDK

```go
// create_alert_policy.go
package main

import (
	"context"
	"fmt"
	"os"

	monitoring "cloud.google.com/go/monitoring/apiv3"
	"cloud.google.com/go/monitoring/apiv3/v2/monitoringpb"
	"google.golang.org/api/option"
	"google.golang.org/protobuf/types/known/durationpb"
)

func main() {
	ctx := context.Background()
	client, err := monitoring.NewAlertPolicyClient(ctx,
		option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
	if err != nil {
		panic(err)
	}
	defer client.Close()

	project := os.Getenv("CLOUDSDK_CORE_PROJECT")
	policy := &monitoringpb.AlertPolicy{
		DisplayName: "High CPU Alert",
		Combiner:    monitoringpb.AlertPolicy_OR,
		Conditions: []*monitoringpb.AlertPolicy_Condition{{
			DisplayName: "CPU > 80%",
			ConditionThreshold: &monitoringpb.AlertPolicy_Condition_MetricThreshold{
				Filter:         `resource.type = "gce_instance" AND metric.type = "compute.googleapis.com/instance/cpu/utilization"`,
				Duration:       &durationpb.Duration{Seconds: 300},
				ThresholdValue: 0.8,
				Comparison:     monitoringpb.ComparisonOp_COMPARISON_GT,
			},
		}},
		NotificationChannels: []string{os.Getenv("NOTIFICATION_CHANNEL")},
	}
	req := &monitoringpb.CreateAlertPolicyRequest{
		Name:        fmt.Sprintf("projects/%s", project),
		AlertPolicy: policy,
	}
	resp, err := client.CreateAlertPolicy(ctx, req)
	if err != nil {
		panic(err)
	}
	fmt.Printf("Created: %s\n", resp.Name)
}
```

#### Post-execution Validation

```bash
gcloud monitoring alert-policies describe "{{output.alert_policy_name}}" \
  --format="json" | jq '{name: .name, enabled: .enabled, conditions: [.conditions[].displayName]}'
```

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|---------------|-------------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | 0 | HALT; fix condition filter | `[ERROR] INVALID_ARGUMENT: Alert policy condition filter is malformed.` |
| `ALREADY_EXISTS` / 409 | 0 | HALT; name collision | `[ERROR] ALREADY_EXISTS: An alert policy with this name exists.` |
| `NOT_FOUND` / 404 | 0 | HALT; describe first | `[ERROR] NOT_FOUND: Alert policy ID not found.` |
| `PERMISSION_DENIED` / 403 | 0 | HALT | `[ERROR] PERMISSION_DENIED: Missing monitoring.alertPolicies.* permission.` |
| `QUOTA_EXCEEDED` / 429 | 0 | HALT | `[ERROR] QUOTA_EXCEEDED: Alert policy quota reached.` |

### Operation: Notification Channels (List/Create/Describe/Delete)

#### Pre-flight Checks (for Delete)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Channel in use by alert | `gcloud monitoring alert-policies list --format="json" | jq '.[].notificationChannels[]'` grep channel ID | Optional | Warn user before deletion |
| **Delete confirmation** | User must confirm with channel ID | Exact match | HALT |

#### Execution

```bash
# List
gcloud monitoring channels list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"

# Describe
gcloud monitoring channels describe "{{user.channel_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Create email channel
gcloud monitoring channels create \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --display-name="Ops Team Email" \
  --type=email \
  --channel-labels=email_address=ops@example.com \
  --format="json"

# Delete (Safety Gate)
gcloud monitoring channels delete "{{user.channel_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet
```

#### Post-execution Validation

```bash
gcloud monitoring channels list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.[] | {name, type, labels}'
```

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|---------------|-------------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | 0 | HALT; check channel type/labels | `[ERROR] Notification channel configuration invalid.` |
| `ALREADY_EXISTS` / 409 | 0 | HALT | `[ERROR] A notification channel with this name already exists.` |
| `NOT_FOUND` / 404 | 0 | HALT | `[ERROR] Notification channel not found.` |
| `PERMISSION_DENIED` / 403 | 0 | HALT | `[ERROR] Missing monitoring.notificationChannels.* permission.` |
| `FAILED_PRECONDITION` / 400 | 0 | HALT | `[ERROR] Channel requires verification.` |

### Operation: Dashboards (List/Create/Describe/Delete)

#### Execution

```bash
# List
gcloud monitoring dashboards list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"

# Describe
gcloud monitoring dashboards describe "{{user.dashboard_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Create (from JSON config file)
cat > /tmp/dashboard.json << 'EOF'
{
  "displayName": "VM CPU Overview",
  "gridLayout": {
    "widgets": [
      {
        "title": "CPU Utilization",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "metric.type=\"compute.googleapis.com/instance/cpu/utilization\""
              }
            }
          }]
        }
      }
    ]
  }
}
EOF

gcloud monitoring dashboards create \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --config-from-file=/tmp/dashboard.json \
  --format="json"

# Delete
gcloud monitoring dashboards delete "{{user.dashboard_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet
```

#### Post-execution Validation

```bash
gcloud monitoring dashboards describe "{{output.resource_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, displayName, widgets: [.gridLayout.widgets[].title]}'
```

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|---------------|-------------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | 0 | HALT; check dashboard JSON structure | `[ERROR] Dashboard JSON is malformed.` |
| `NOT_FOUND` / 404 | 0 | HALT | `[ERROR] Dashboard not found.` |
| `PERMISSION_DENIED` / 403 | 0 | HALT | `[ERROR] Missing monitoring.dashboards.* permission.` |
| `ABORTED` / 409 | 1 (3s) | Retry once; etag conflict | `[ERROR] Dashboard etag conflict. Re-fetch and retry.` |

### Operation: Uptime Checks (Create/Describe/Delete)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Target hostname | User-provided domain/IP | Resolvable | HALT; verify hostname |
| Region availability | `gcloud monitoring uptime list` (no args) | Check regions | Use default regions |

#### Execution

```bash
# List
gcloud monitoring uptime list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"

# Create HTTP uptime check
gcloud monitoring uptime create "web-health-check" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --display-name="Website Health Check" \
  --hostname="example.com" \
  --check-type=HTTP \
  --period=300 \
  --timeout=10 \
  --format="json"

# Describe
gcloud monitoring uptime describe "{{user.uptime_check_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Delete
gcloud monitoring uptime delete "{{user.uptime_check_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet
```

#### Post-execution Validation

```bash
gcloud monitoring uptime describe "{{output.resource_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, displayName, period, timeout, checkType}'
```

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|---------------|-------------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | 0 | HALT; check hostname/URL | `[ERROR] Uptime check config is invalid.` |
| `NOT_FOUND` / 404 | 0 | HALT | `[ERROR] Uptime check not found.` |
| `PERMISSION_DENIED` / 403 | 0 | HALT | `[ERROR] Missing monitoring.uptimeCheckConfigs.* permission.` |
| `QUOTA_EXCEEDED` / 429 | 0 | HALT | `[ERROR] Uptime check quota reached (max 100 per project).` |
| `FAILED_PRECONDITION` / 400 | 0 | HALT | `[ERROR] Hostname is not resolvable.` |
