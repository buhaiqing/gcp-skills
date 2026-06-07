---
name: gcp-monitoring-ops
description: >-
  Use when the user needs to query, configure, troubleshoot, or manage Google
  Cloud Monitoring — metrics, dashboards, alert policies, notification channels,
  uptime checks, and time-series data. User mentions Cloud Monitoring, Stackdriver,
  alert policies, metric queries, dashboard management, uptime checks, or describes
  monitoring scenarios (e.g., "set up alerts", "check metrics", "create dashboard",
  "notification not working") even without naming the product directly. Not for
  Cloud Logging, billing cost analysis, or IAM roles that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials, network access to
  Google Cloud Monitoring endpoints (`monitoring.googleapis.com`).
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://monitoring.googleapis.com/$discovery/rest?version=v3"
  cli_applicability: "dual-path"
  cli_support_evidence: "gcloud monitoring --help confirms subcommands: dashboards, alert-policies, notification-channels, metrics, uptime. See https://cloud.google.com/sdk/gcloud/reference/monitoring"
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Monitoring Operations Skill

## Overview

Cloud Monitoring on Google Cloud provides observability for applications and infrastructure — metrics, dashboards, alerting, uptime checks, and time-series analysis. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` supports monitoring. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step. Coverage gaps (SDK-only operations) are listed in `references/gcloud-usage.md`.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Cloud Monitoring) with clear cross-product delegation (Logging, GCE, GKE, etc.) |

Refer to the [meta-skill](../gcp-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions of each standard.

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM permissions, credential masking, VPC SC, data encryption | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Alert redundancy, uptime check multi-region, failure-oriented design | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Metrics retention pricing, custom metrics costs, waste detection | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Batch operations, CI/CD integration, automation patterns | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Monitoring latency, alert freshness, query performance | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Cloud Monitoring", "Stackdriver", "metrics", "alert policies", "dashboards", "notification channels", or "uptime checks"
- Task involves querying time-series metrics (CPU, memory, disk, network, custom metrics)
- Task involves CRUD on alert policies, notification channels, dashboards, uptime check configs
- Task keywords: monitor, alert, metric, dashboard, notification, uptime, incident, silen[ce], SLO
- User asks to set up, configure, troubleshoot, or investigate GCP observability

### SHOULD NOT Use This Skill When

- Task is purely Cloud Logging (log queries, log buckets, log-based metrics) → delegate to: `gcp-logging-ops` (when present)
- Task is IAM / permission model only → delegate to: `gcp-iam-ops` (when present)
- Task is about Compute Engine instance state (start/stop/ssh) → delegate to: `gcp-gce-ops`
- Task is about GKE cluster metrics (use kubectl top / gke-ops) → delegate to: `gcp-gke-ops`
- Task is about billing cost analysis → delegate to: `gcp-billing-ops` (when present)

### Delegation Rules

| Resource | Delegated Skill | Flow |
|----------|----------------|------|
| VM CPU/Memory investigation | `gcp-gce-ops` | Monitoring detects anomaly → delegate describe/patch to GCE |
| K8s cluster metrics | `gcp-gke-ops` | GKE metrics → GKE skill describes cluster/node |
| Log-based alert policies | `gcp-logging-ops` | Log-based metrics query → Logging skill for log filter |
| Database query performance | `gcp-cloudsql-ops` | Monitoring detects slow query → Cloud SQL skill investigates |

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.alert_policy_id}}` | Alert policy name/ID | Ask once; reuse |
| `{{user.channel_id}}` | Notification channel ID | Ask once; reuse |
| `{{user.dashboard_id}}` | Dashboard ID | Ask once; reuse |
| `{{user.metric_type}}` | Metric type (e.g., compute.googleapis.com/instance/cpu/utilization) | Ask once; reuse |
| `{{user.uptime_check_id}}` | Uptime check config ID | Ask once; reuse |
| `{{user.filter}}` | Monitoring filter expression | Ask once; reuse |
| `{{output.resource_name}}` | From last API or `gcloud` JSON response | Parse per operation |
| `{{output.alert_policy_name}}` | Created/modified alert policy name | Parse per API response |
| `{{output.channel_name}}` | Created notification channel name | Parse per API response |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** NEVER log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value. Verification MUST check existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA key file exists"`.

## API and Response Conventions (Agent-Readable)

- **REST API is canonical:** `https://monitoring.googleapis.com/v3/`
- **Time format:** RFC 3339 (e.g., `2026-06-07T10:00:00Z`)
- **Filter format:** Monitoring filter language — see [Filtering docs](https://cloud.google.com/monitoring/api/v3/filters)
- **Pagination:** `pageToken` in request, `nextPageToken` in response; page size defaults to 100
- **Metric types:** `{service}.googleapis.com/{namespace}/{metric}` (e.g., `compute.googleapis.com/instance/cpu/utilization`)

### Common JSON Paths

```json
// ── Time Series ──
// $.timeSeries[].metric.type          -> metric type string
// $.timeSeries[].resource.type        -> monitored resource type
// $.timeSeries[].points[].value       -> metric values
// $.timeSeries[].points[].interval    -> time range
//
// ── Alert Policy ──
// $.name               -> "projects/{project}/alertPolicies/{policy_id}"
// $.displayName        -> human-readable name
// $.combiner           -> OR / AND / AND_WITH_MATCHING_RESOURCE
// $.conditions[]       -> list of alert conditions
// $.notificationChannels[] -> linked notification channels
// $.enabled            -> { "value": true/false }
// $.creationRecord     -> { "mutateTime": "..." }
//
// ── Notification Channel ──
// $.name               -> "projects/{project}/notificationChannels/{channel_id}"
// $.type               -> "email", "sms", "pagerduty", "slack", "webhook", etc.
// $.labels             -> channel-specific config (email_address, url, etc.)
// $.verificationStatus -> UNVERIFIED / VERIFIED
//
// ── Dashboard ──
// $.name               -> "projects/{project}/dashboards/{dashboard_id}"
// $.displayName        -> human-readable name
// $.gridLayout.widgets[] -> widget definitions
// $.etag               -> for optimistic concurrency control
//
// ── Uptime Check ──
// $.name               -> "projects/{project}/uptimeCheckConfigs/{config_id}"
// $.displayName        -> human-readable name
// $.monitoredResource  -> resource being checked
// $.period             -> check frequency (e.g., "60s")
// $.timeout            -> check timeout (e.g., "10s")
// $.checkType          -> HTTP / HTTPS / TCP
```

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create Alert Policy | — | exists (no async) | — | 30s |
| Create Notification Channel | — | exists (no async) | — | 30s |
| Create Dashboard | — | exists (no async) | — | 30s |
| Create Uptime Check | — | exists (no async) | — | 30s |
| Delete (any) | exists | deleted | — | 30s |

## Quick Start

### What This Skill Does

This skill enables you to query metrics, manage alert policies, configure notification channels, create dashboards, and set up uptime checks on Google Cloud Monitoring.

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`

### Verify Setup
```bash
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
```

### Your First Command
```bash
# List all metric descriptors in the project
gcloud monitoring metrics list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq '[.[] | {name, type, unit}]'
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Understand Cloud Monitoring architecture
- [Common Operations](#execution-flows) — Manage alerts, dashboards, channels
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Query Time Series | Query metric time-series data | Medium | None |
| List Metric Descriptors | List all metric types available | Low | None |
| List/Create/Modify/Delete Alert Policies | Manage alert rules | Medium | **Medium** — alert gaps impact ops |
| List/Create/Describe/Delete Notification Channels | Configure alert routing | Low | **Low** — misrouting causes missed alerts |
| List/Create/Describe/Delete Dashboards | Visual metric dashboards | Medium | Low |
| Create/Describe/Delete Uptime Checks | External endpoint monitoring | Medium | Low |
| Silence/Unsilence Alerts | Temporarily mute alerts | Low | **Low** — can miss production alerts |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial Cloud Monitoring skill with time-series, alerts, channels, dashboards, uptime checks |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud and SDK/API) → Validate → Recover**. Do not skip phases.

### Pre-flight Checks (Common to all operations)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI | `gcloud version` | Exit code 0 | Install gcloud (see Prerequisites) |
| Credentials | `gcloud auth print-access-token --quiet` | Non-empty token | HALT; authenticate SA |
| Project | `gcloud config get-value project` or env var | Set and valid | HALT; set `CLOUDSDK_CORE_PROJECT` |
| Monitoring API | `gcloud services list --enabled --filter="config:monitoring.googleapis.com"` | enabled | HALT; run `gcloud services enable monitoring.googleapis.com` |

### Operation: Query Time-Series Metrics

#### Use Case
Query metric data for a specific resource or aggregation over a time window.

#### Pre-flight Checks (additional)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Metric type | Known from `gcloud monitoring metrics list` | Valid metric type | List available metrics first |
| Time range | User-provided or default (last 1h) | `< end_time > start_time` | Default to last 1 hour |

#### Execution — CLI (`gcloud`)
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

#### Execution — Python SDK (Primary Fallback)
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

#### Execution — JIT Go SDK (Secondary Fallback)
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

### Operation: List/Create/Describe/Modify/Delete Alert Policies

#### Pre-flight Checks (for Create/Modify/Delete)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Alert policy name | `gcloud monitoring alert-policies list` | Unique name | Warn if name exists; ask user |
| Notification channel | `gcloud monitoring channels list` | Channel exists (optional) | Create channel first or skip |
| Metric type | `gcloud monitoring metrics list` | Valid metric | List available metrics |
| **Delete confirmation** | User must confirm with policy ID | Exact match | HALT — user must type exact policy ID |

#### Execution — CLI (`gcloud`)

**List alert policies:**
```bash
gcloud monitoring alert-policies list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Describe an alert policy:**
```bash
gcloud monitoring alert-policies describe "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Create alert policy (CPU > 80% for 5 minutes):**
```bash
gcloud monitoring alert-policies create "high-cpu-alert" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --display-name="High CPU Alert" \
  --condition-display-name="CPU > 80%" \
  --condition-filter='resource.type = "gce_instance" AND metric.type = "compute.googleapis.com/instance/cpu/utilization"' \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s \
  --notification-channels="{{user.channel_id}}" \
  --format="json"
```

**Modify alert policy (enable/disable):**
```bash
gcloud monitoring alert-policies update "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --enabled=false \
  --format="json"
```

**Delete alert policy (Safety Gate required):**
```bash
# Safety Gate — user must confirm
# "WARNING: This will permanently delete alert policy {policy_id} ({display_name})."
# "Type the policy ID to confirm: _______________"

gcloud monitoring alert-policies delete "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet
```

#### Execution — Python SDK (Primary Fallback)

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

#### Execution — JIT Go SDK

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
	// $.name -> created policy name
	fmt.Printf("Created: %s\n", resp.Name)
}
```

#### Post-execution Validation

```bash
# Verify alert policy exists and is enabled
gcloud monitoring alert-policies describe "{{output.alert_policy_name}}" \
  --format="json" | jq '{name: .name, enabled: .enabled, conditions: [.conditions[].displayName]}'
```

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|---------------|-------------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | 0 | HALT; fix condition filter | `[ERROR] INVALID_ARGUMENT: Alert policy condition filter is malformed.` |
| `ALREADY_EXISTS` / 409 | 0 | HALT; name collision | `[ERROR] ALREADY_EXISTS: An alert policy with this name exists. Use modify or pick a new name.` |
| `NOT_FOUND` / 404 | 0 | HALT; describe first | `[ERROR] NOT_FOUND: Alert policy ID not found. List policies to find correct ID.` |
| `PERMISSION_DENIED` / 403 | 0 | HALT | `[ERROR] PERMISSION_DENIED: Missing monitoring.alertPolicies.* permission.` |
| `QUOTA_EXCEEDED` / 429 | 0 | HALT | `[ERROR] QUOTA_EXCEEDED: Alert policy quota reached. Delete unused policies.` |

### Operation: List/Create/Describe/Delete Notification Channels

#### Pre-flight Checks (for Delete)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Channel in use by alert | `gcloud monitoring alert-policies list --format="json" | jq '.[].notificationChannels[]'` grep channel ID | Optional | Warn user before deletion |
| **Delete confirmation** | User must confirm with channel ID | Exact match | HALT |

#### Execution — CLI (`gcloud`)

**List notification channels:**
```bash
gcloud monitoring channels list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Describe notification channel:**
```bash
gcloud monitoring channels describe "{{user.channel_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Create email notification channel:**
```bash
gcloud monitoring channels create \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --display-name="Ops Team Email" \
  --type=email \
  --channel-labels=email_address=ops@example.com \
  --format="json"
```

**Delete notification channel (Safety Gate):**
```bash
gcloud monitoring channels delete "{{user.channel_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet
```

#### Post-execution Validation

```bash
# Verify alert policy references updated channel
gcloud monitoring channels list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.[] | {name, type, labels}'
```

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|---------------|-------------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | 0 | HALT; check channel type/labels | `[ERROR] INVALID_ARGUMENT: Notification channel configuration invalid. Verify type and required labels.` |
| `ALREADY_EXISTS` / 409 | 0 | HALT; channel name exists | `[ERROR] ALREADY_EXISTS: A notification channel with this name already exists.` |
| `NOT_FOUND` / 404 | 0 | HALT; channel ID not found | `[ERROR] NOT_FOUND: Notification channel not found. List channels to find correct ID.` |
| `PERMISSION_DENIED` / 403 | 0 | HALT; check IAM | `[ERROR] PERMISSION_DENIED: Missing monitoring.notificationChannels.* permission.` |
| `FAILED_PRECONDITION` / 400 | 0 | HALT; channel requires verification | `[ERROR] Channel requires verification. Check email/webhook verification status.` |

### Operation: List/Create/Describe/Delete Dashboards

#### Execution — CLI (`gcloud`)

**List dashboards:**
```bash
gcloud monitoring dashboards list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Describe dashboard:**
```bash
gcloud monitoring dashboards describe "{{user.dashboard_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Create dashboard (JSON config file):**
```bash
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
```

**Delete dashboard:**
```bash
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
| `INVALID_ARGUMENT` / 400 | 0 | HALT; check dashboard JSON structure | `[ERROR] INVALID_ARGUMENT: Dashboard JSON is malformed. Verify widget structure.` |
| `NOT_FOUND` / 404 | 0 | HALT; dashboard ID not found | `[ERROR] NOT_FOUND: Dashboard not found. List dashboards to find correct ID.` |
| `PERMISSION_DENIED` / 403 | 0 | HALT; check IAM | `[ERROR] PERMISSION_DENIED: Missing monitoring.dashboards.* permission.` |
| `ABORTED` / 409 | 1 (3s) | Retry once; etag conflict | `[ERROR] ABORTED: Dashboard etag conflict. Re-fetch and retry.` |

### Operation: Uptime Checks (Create/Describe/Delete)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Target hostname | User-provided domain/IP | Resolvable | HALT; verify hostname |
| Region availability | `gcloud monitoring uptime list` (no args) | Check regions | Use default regions |

#### Execution — CLI (`gcloud`)

**List uptime checks:**
```bash
gcloud monitoring uptime list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Create HTTP uptime check:**
```bash
gcloud monitoring uptime create "web-health-check" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --display-name="Website Health Check" \
  --hostname="example.com" \
  --check-type=HTTP \
  --period=300 \
  --timeout=10 \
  --format="json"
```

**Describe uptime check:**
```bash
gcloud monitoring uptime describe "{{user.uptime_check_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Delete uptime check:**
```bash
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
| `INVALID_ARGUMENT` / 400 | 0 | HALT; check hostname/URL | `[ERROR] INVALID_ARGUMENT: Uptime check config is invalid. Verify hostname and check type.` |
| `NOT_FOUND` / 404 | 0 | HALT; uptime check ID not found | `[ERROR] NOT_FOUND: Uptime check not found. List uptime checks to find correct ID.` |
| `PERMISSION_DENIED` / 403 | 0 | HALT; check IAM | `[ERROR] PERMISSION_DENIED: Missing monitoring.uptimeCheckConfigs.* permission.` |
| `QUOTA_EXCEEDED` / 429 | 0 | HALT | `[ERROR] QUOTA_EXCEEDED: Uptime check quota reached (max 100 per project). Delete old checks.` |
| `FAILED_PRECONDITION` / 400 | 0 | HALT; resource not valid | `[ERROR] Hostname is not resolvable or resource does not exist.` |

## Prerequisites

1. **Install gcloud CLI** (primary execution path):
   ```bash
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

2. **Bootstrap Go runtime** (for JIT SDK fallback):
   ```bash
   if ! command -v go &> /dev/null; then
       OS=$(uname -s | tr '[:upper:]' '[:lower:]')
       ARCH=$(uname -m)
       [ "$ARCH" = "x86_64" ] && ARCH="amd64"
       [ "$ARCH" = "aarch64" ] && ARCH="arm64"
       mkdir -p /tmp/go-runtime
       curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
       export PATH="/tmp/go-runtime/go/bin:$PATH"
   fi
   go version
   ```

3. **Configure Credentials:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
   export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
   gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
   gcloud config set project "$CLOUDSDK_CORE_PROJECT"
   ```

4. **Enable Monitoring API:**
   ```bash
   gcloud services enable monitoring.googleapis.com
   ```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [gcloud Usage](references/gcloud-usage.md)
- [Troubleshooting Guide](references/troubleshooting.md)
- [Monitoring & Alerts](references/monitoring.md)
- [Integration](references/integration.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Idempotency Checklist](references/idempotency-checklist.md)
- [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md)
- [AIOps Best Practices](../gcp-skill-generator/references/aiops-best-practices.md)
- [Execution Environment Setup](../gcp-skill-generator/references/execution-environment.md)
- [Enhanced Self-Healing Framework](../gcp-skill-generator/references/enhanced-self-healing-framework.md)
- [CLI Behavioral Reference](../gcp-skill-generator/references/cli-behavior.md)

## Operational Best Practices

- **Least privilege:** Use `roles/monitoring.viewer` for read-only, `roles/monitoring.editor` for alerts/dashboards, `roles/monitoring.admin` for full management
- **Alert hygiene:** Use notification channel summaries; avoid alert fatigue with proper condition thresholds and durations
- **Dashboard structure:** Use `gridLayout` for organized widgets; label dashboards by team/service/environment
- **Metrics retention:** Standard retention is 6 weeks for most metrics; custom metrics follow billing plan
- **Uptime check regions:** Use multiple regions (at least 3) for reliable health checking

## Quality Gate (GCL)

This skill uses the **Generator-Critic-Loop (GCL)** adversarial quality gate for operations with medium or high risk.

| Dimension | Classification | Default `max_iter` | Most-scrutinized ops |
|-----------|---------------|:------------------:|----------------------|
| Cloud Monitoring | `recommended` | 3 | Delete Alert Policy, Modify Alert, Delete Notification Channel |

**Rubric:** See [references/rubric.md](references/rubric.md)
**Prompt templates:** See [references/prompt-templates.md](references/prompt-templates.md)

### Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial GCL integration (recommended) |

## Token Efficiency Guidelines (P0 — 强制)

### TE-1: API Query > Static Tables
Use `gcloud monitoring metrics list` to fetch metric descriptors instead of hardcoding tables.

### TE-2: No docstrings in code
Inline `#` comments only. No function-level docstrings.

### TE-3: Compact error tables
See [troubleshooting.md](references/troubleshooting.md) for compact error table format.

### TE-4: Centralized JSON paths
JSON paths are declared at the top of this file under [Common JSON Paths](#common-json-paths).

### TE-5: YAML anchors in example-config.yaml
See [assets/example-config.yaml](assets/example-config.yaml) for YAML anchor patterns.

### TE-6: Eliminate cross-file duplicate flows
SKILL.md has full execution flows; references do not repeat them.