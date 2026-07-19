# AIOps Self-Healing — Cloud Logging Pipeline Anomaly

> Agent runbook for detecting and auto-remediating Cloud Logging pipeline anomalies: ingestion delay/drop, log sink / log router configuration drift. Every remediation action is **dry-run first**, **idempotent**, and **gated**; destructive actions are marked `HALT`.

## Table of Contents

1. [Overview](#overview)
2. [Detection Capabilities](#detection-capabilities)
3. [Prerequisites](#prerequisites)
4. [Anomaly 1 — Ingestion Delay / Drop](#anomaly-1--ingestion-delay--drop)
5. [Anomaly 2 — Log Sink / Log Router Drift](#anomaly-2--log-sink--log-router-drift)
6. [Self-Healing Action Contract](#self-healing-action-contract)
7. [Cross-Skill Trigger](#cross-skill-trigger)
8. [Error Classification](#error-classification)
9. [Blast Radius](#blast-radius)
10. [See Also](#see-also)

## Overview

Cloud Logging pipelines can silently degrade: logs arrive late, get dropped, or stop exporting because a sink or log router (inclusion/exclusion filter) drifted from its intended configuration. This runbook gives an agent a closed-loop path:

```
detect anomaly → classify (error-taxonomy) → dry-run remediation → gate check → apply (or HALT) → validate → trigger cross-skill if needed
```

### Safety posture

- **Credential masking (§0.1):** NEVER print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` value. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.
- **Dry-run first:** Every mutating action prints the exact `gcloud` command it *would* run, then requires an explicit apply step.
- **Idempotent:** Re-creating a sink with identical `name`+`destination`+`filter` is a no-op if unchanged.
- **HALT on destructive:** Deleting buckets/sinks, modifying `_Default`/`_Required`, cross-project mutations → never auto-run.

## Detection Capabilities

| Anomaly | Signal | Severity | Auto-remediable |
|---------|--------|----------|:----------------:|
| Ingestion delay | `receiveTimestamp - timestamp` gap exceeds threshold | Medium | No (diagnose only) |
| Ingestion drop | Expected volume vs delivered volume gap | High | No (diagnose only) |
| Sink drift | Live sink config ≠ desired config | High | **Yes** (re-create) |
| Log router drift | Exclusion/filter changed unexpectedly | Medium | **Yes** (restore) |
| Writer identity IAM lost | Sink exists but destination rejects writes | High | **Yes** (re-grant) |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Logging API | `gcloud services list --enabled --filter="name:logging.googleapis.com"` | Enabled | `gcloud services enable logging.googleapis.com` |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Project | `gcloud config get-value project` | Set | HALT — set project |
| Monitoring API (for alert trigger) | `gcloud services list --enabled --filter="name:monitoring.googleapis.com"` | Enabled | Delegate to `gcp-monitoring-ops` |

## Anomaly 1 — Ingestion Delay / Drop

> **Scope:** Detection and diagnosis ONLY. Ingestion delay/drop is almost always caused by upstream (quota, project suspension, resource exhaustion) — self-healing the sink will NOT fix it. Classify and delegate.

### Detect delay

```bash
# Measure ingestion lag: gap between event time and delivery time
gcloud logging read "severity>=DEFAULT" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=20 \
  --format="json" \
  | jq -r '.[] | "\(.timestamp) -> \(.receiveTimestamp)"'
```

### Detect drop (volume gap)

```bash
# Compare delivered entries in last 5 min vs expected baseline (external SLO)
gcloud logging read "timestamp >= \"$(date -u -d '-5 min' +%Y-%m-%dT%H:%M:%SZ)\"" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq 'length'
```

### Remediation decision

| Finding | Classification (error-taxonomy) | Action |
|---------|----------------------------------|--------|
| Gap caused by `QUOTA_EXCEEDED` | Quota dimension | `REMEDIATE` (reduce exclusion / request increase) — delegate to `gcp-billing-ops` if billing-gated |
| Gap caused by `UNAVAILABLE` | Network dimension | `RETRY` (backoff; no mutation) |
| Gap caused by project suspension | Dependency dimension | `HALT` — human decision |
| No gap, false alarm | Unknown | Close anomaly |

**No auto-mutation here.** If a downstream sink is also broken, proceed to Anomaly 2.

## Anomaly 2 — Log Sink / Log Router Drift

> **Scope:** Detect config drift and self-heal by re-creating the sink from a known-good desired state. This is the primary auto-remediable path.

### Step 1 — Capture live state (DIAG)

```bash
SINK="{{user.sink_name}}"
gcloud logging sinks describe "$SINK" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" \
  | jq '{name, destination, filter, writerIdentity, disabled}' > /tmp/live_sink.json
cat /tmp/live_sink.json
```

### Step 2 — Compare against desired state

Desired state is supplied by the operator via `{{user.desired_sink_config}}` (a JSON file or inline). Drift is present when any of `destination`, `filter`, or `disabled` differ.

```bash
# Example diff (operator-provided desired config at /tmp/desired_sink.json)
jq -S 'del(.writerIdentity)' /tmp/live_sink.json > /tmp/live_norm.json
jq -S '{name, destination, filter, disabled}' "{{user.desired_sink_config}}" > /tmp/desired_norm.json
diff <(cat /tmp/live_norm.json) <(cat /tmp/desired_norm.json) && echo "✅ No drift" || echo "⚠️ Drift detected"
```

### Step 3 — DRY-RUN remediation

> **NEVER skip dry-run.** Print the exact command; do not execute.

```bash
echo "[DRY-RUN] Would re-create sink to restore desired state:"
echo "  gcloud logging sinks create \"$SINK\" \"{{user.sink_destination}}\" \\"
echo "    --log-filter='{{user.filter_query}}' \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T2 (writes to destination owned by another skill)"
```

### Step 4 — Gate check (MANDATORY)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Idempotent | Same `name`+`destination`+`filter` as desired | HALT if name collides with unrelated sink |
| Destination exists | `gcloud logging sinks describe` destination reachable | HALT — delegate to destination skill |
| Blast radius | Tier ≤ T2 | HALT if T3/T4 (cross-project / `_Required`) |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

### Step 5 — APPLY (only after gate passes)

```bash
# Re-create is idempotent: same name re-applies desired config
gcloud logging sinks create "$SINK" "{{user.sink_destination}}" \
  --log-filter="{{user.filter_query}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Step 6 — Re-grant writer identity (idempotent IAM)

```bash
WRITER_IDENTITY=$(gcloud logging sinks describe "$SINK" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq -r '.writerIdentity')
# Grant is a no-op if already granted (idempotent). Delegate destination IAM to its skill.
echo "[EXEC] Ensure $WRITER_IDENTITY has write on destination (delegate to gcp-bigquery-ops / gcp-pubsub-ops / gcp-gcs-ops)"
```

### Step 7 — VALIDATE

```bash
gcloud logging sinks describe "$SINK" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq '{name, destination, filter, disabled}' | diff - /tmp/desired_norm.json && echo "✅ Sink restored"
```

### Log router (exclusion) drift — same pattern

Replace sink commands with `gcloud logging exclusions describe/create` using the identical dry-run → gate → apply → validate flow. Exclusions are Tier T2 (affect all log readers + Monitoring alert policies) — note this in output.

## Self-Healing Action Contract

| Property | Rule |
|----------|------|
| Dry-run | Every mutating command printed before execution; `--format=json` for parse |
| Idempotent | Re-create with identical params = safe no-op/update |
| Gated | Gate table must pass before APPLY |
| HALT list | Delete sink/bucket, modify `_Default`/`_Required`, cross-project, org log router |
| Credential | §0.1 masking — existence check only |

## Cross-Skill Trigger

When the anomaly's root cause or remediation crosses skill boundaries, **delegate** (do not inline the other skill's logic):

| Trigger | Delegate to | Reason |
|---------|-------------|-------|
| Sink destination missing/broken | `gcp-bigquery-ops` / `gcp-pubsub-ops` / `gcp-gcs-ops` | Destination owned by another skill |
| Anomaly originated from a Monitoring alert policy | `gcp-monitoring-ops` | Alert owns the signal |
| Ingestion drop due to billing/quota suspension | `gcp-billing-ops` | Billing mutation is `HALT` |
| Writer identity IAM grant needed | destination skill's IAM flow | IAM gate inherited |
| Security-relevant log gap (audit/SCC) | `gcp-securitycenter-ops` | `_Required` bucket is Tier T4 |

Trigger format: report the classified error code (from [error-taxonomy.md](../../../docs/error-taxonomy.md)) and the recommended skill, then stop and let the agent load that skill.

## Error Classification

Map every detected anomaly to [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) before choosing remediation:

| Logging symptom | Taxonomy dimension | Canonical code | Recovery |
|-----------------|--------------------|----------------|----------|
| Sink config drift | Configuration | `INVALID_ARGUMENT` (if malformed) / config drift | `REMEDIATE` (re-create) |
| Writer IAM lost | Permission | `PERMISSION_DENIED` | `REMEDIATE` (re-grant) |
| Ingestion drop (quota) | Quota | `QUOTA_EXCEEDED` | `REMEDIATE` / delegate |
| Ingestion drop (suspended) | Dependency | `BILLING_NOT_ENABLED` | `HALT` |
| Transient read failure | Network | `UNAVAILABLE` | `RETRY` |
| Unknown internal | Unknown | `INTERNAL` | `RETRY` → `ESCALATE` |

## Blast Radius

Apply the tiers from [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md):

- Sink re-create → **T2** (writes to destination owned by another skill) → dry-run + cross-skill note, confirm destination exists.
- Exclusion restore → **T2** (affects Monitoring alert policies) → note in output.
- Cross-project aggregated sink → **T3** → `HALT`.
- `_Default` / `_Required` / org log router → **T4** → `HALT`, never auto-mutate.

## See Also

- [error-taxonomy.md](../../../docs/error-taxonomy.md) — unified cross-skill error classification
- [cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — blast radius tiers and gates
- [gcp-logging-ops SKILL.md](../../SKILL.md) — base operations (sinks, exclusions, buckets)
- [gcp-monitoring-ops](../../../gcp-monitoring-ops/SKILL.md) — alert policies that may trigger this runbook
- [VPC AIOps reference](../../../gcp-vpc-ops/references/advanced/aiops-network-anomaly.md) — sibling AIOps pattern
