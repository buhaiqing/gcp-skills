---
name: monitoring-ops-rubric
description: GCL scoring rubric for Cloud Monitoring operations
classification: recommended
gcl_max_iter: 3
---

# Rubric — Cloud Monitoring (GCL)

## Core Dimensions (5)

| Dimension | Weight | Max | Meaning |
|-----------|--------|-----|---------|
| **Correctness** | 30% | 10 | Resource ID, state, config matches request; filter syntax valid; metric type exists |
| **Safety** | 30% | 10 | Destructive operations (delete alert/channel/dashboard/uptime) confirmed; no alert gaps created |
| **Idempotency** | 15% | 10 | Repeated calls produce same result; etag handling for dashboards |
| **Traceability** | 10% | 10 | Commands, params, resource names, and responses recorded for audit |
| **Spec Compliance** | 15% | 10 | Follows core-concepts.md constraints (metric types, filter syntax, quotas) |

## GCP Extensions (3 additional dimensions, bonus)

| Dimension | Max | Scoring Criteria |
|-----------|-----|------------------|
| Filter Validation | 5 | Alert condition filter matches available metric descriptors and monitored resources |
| Notification Coverage | 5 | Alert policy has at least one verified notification channel linked |
| Alert Hygiene | 5 | Threshold and duration are reasonable (not too sensitive or too lax); no duplicate policies |

## Per-Op Safety Sub-Rules

| Operation | Safety Rule |
|-----------|-------------|
| Delete Alert Policy | User types policy ID → confirm; warn about monitoring gap until recreated |
| Delete Notification Channel | List alert policies referencing this channel first; warn about orphaned alerts |
| Delete Dashboard | Confirm display name; warn about lost visualization (data unaffected) |
| Delete Uptime Check | Confirm config ID; warn about losing external health monitoring |
| Disable Alert Policy | Warn user; policy can be re-enabled; note duration of suppression |
| Create Alert Policy (high sensitivity) | Warn if threshold < 10% or duration < 60s (likely to cause alert fatigue) |

## Detection Regex

```
delete|destroy|remove|disable|silence|mute
```

## Worked Examples

### PASS — Create Alert Policy

**Request:** Create CPU utilization alert for GCE instances at 80% for 5 minutes

**G Actions:**
1. Pre-flight: Check notification channel exists, metric type valid, policy name unique
2. Execute: `gcloud monitoring alert-policies create "high-cpu" --display-name="High CPU" --condition-filter='resource.type = "gce_instance" AND metric.type = "compute.googleapis.com/instance/cpu/utilization"' --condition-threshold-value=0.8 --condition-threshold-duration=300s --format=json`
3. Verify: Policy exists, enabled=true, condition threshold=0.8, duration=300s, channels linked
4. Report: Policy name, condition details, notification channels

**C Score:** Correctness=10, Safety=10, Idempotency=10, Traceability=9, Spec Compliance=10
**Extension:** Filter Validation=5, Notification Coverage=5, Alert Hygiene=5

### SAFETY_FAIL — Delete Last Notification Channel

**Request:** Delete the only notification channel in the project

**G Actions:**
1. Pre-flight: Channel exists but is referenced by 3 active alert policies
2. Safety check: Warn user — deleting this channel will break notifications for 3 alert policies
3. User confirms without providing replacement channel → G proceeds
4. C notes: Safety=0 — should have required at least one replacement channel or explicit acknowledgment of alert gap

**C Score:** Safety=0 → **ABORT**
**Fix Suggestion:** Before deletion, either (a) reassign alert policies to another channel, or (b) require explicit user acknowledgment that 3 alert policies will have no notification routing

### FAIL — Alert Policy with Invalid Filter

**Request:** Create alert for metric "compute.googleapis.com/instance/cpu/usage_rate"

**G Actions:**
1. Execute: Create alert with filter referencing `cpu/usage_rate`
2. Result: INVALID_ARGUMENT — metric type does not exist (correct type is `cpu/utilization`)
3. C notes: Correctness=3 — did not validate metric type against available descriptors before creating

**C Score:** Correctness=3, Safety=10, Idempotency=10, Traceability=8, Spec Compliance=5
**Fix Suggestion:** Run `gcloud monitoring metrics list --filter="metric.type:cpu"` to discover correct metric type before creating alert policy
