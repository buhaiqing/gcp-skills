# AIOps Self-Healing Runbook — Cloud Logging

> Agent runbook for closed-loop self-healing of Cloud Logging failures: ingestion backlog / dropped logs, log bucket retention breach, sink / log-router drift. Every remediation action is **dry-run first**, **idempotent**, and **gated**; destructive actions are marked `HALT`.

## Table of Contents

1. [Overview](#overview)
2. [Detection Capabilities](#detection-capabilities)
3. [Prerequisites](#prerequisites)
4. [Trigger Conditions](#trigger-conditions)
5. [Self-Healing Actions](#self-healing-actions)
6. [Error Classification](#error-classification)
7. [Blast Radius](#blast-radius)
8. [GCL Connection](#gcl-connection)
9. [See Also](#see-also)

## Overview

Cloud Logging can degrade in ways that are invisible until an audit or dashboard goes dark: logs pile up in ingestion backlog, get silently dropped, or a log bucket silently breaches its retention policy. This runbook closes the loop:

```
trigger → detect → classify (error-taxonomy) → dry-run remediation → gate check → apply (or HALT) → validate → cross-skill if needed
```

### Safety posture

- **Credential masking (§0.1):** NEVER print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` value. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.
- **Dry-run first:** Every mutating action prints the exact `gcloud` command it *would* run, then requires an explicit apply step.
- **Idempotent:** Re-applying a sink/exclusion/bucket update with identical params is a no-op if unchanged.
- **HALT on destructive:** Deleting buckets/sinks, modifying `_Default`/`_Required`, retention unlock, cross-project mutations → never auto-run.

## Detection Capabilities

| Anomaly | Signal | Severity | Auto-remediable |
|---------|--------|----------|:----------------:|
| Ingestion backlog | Persistent delivery lag / queue depth rising | High | No (diagnose only) |
| Dropped logs | Expected volume vs delivered volume gap | High | No (diagnose only) |
| Bucket retention breach | `retentionDays` below policy floor | Medium | **Yes** (update) |
| Sink drift | Live sink config ≠ desired config | High | **Yes** (re-create) |
| Log router drift | Exclusion/filter changed unexpectedly | Medium | **Yes** (restore) |
| Writer identity IAM lost | Sink exists but destination rejects writes | High | **Yes** (re-grant) |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Logging API | `gcloud services list --enabled --filter="name:logging.googleapis.com"` | Enabled | `gcloud services enable logging.googleapis.com` |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Credentials file | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | Exists | HALT — set `GOOGLE_APPLICATION_CREDENTIALS=****` |
| Project | `gcloud config get-value project` | Set | HALT — set project |
| Monitoring API (alert trigger) | `gcloud services list --enabled --filter="name:monitoring.googleapis.com"` | Enabled | Delegate to `gcp-monitoring-ops` |

## Trigger Conditions

### T1 — Ingestion backlog

Backlog = logs generated faster than Cloud Logging can deliver. Detected as a growing gap between event time (`timestamp`) and delivery time (`receiveTimestamp`).

```bash
# Measure ingestion lag for recent entries
gcloud logging read "severity>=DEFAULT" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=20 \
  --format="json" \
  | jq -r '.[] | "\(.timestamp) -> \(.receiveTimestamp)"'
```

**Remediation:** diagnose only. Backlog is almost always upstream (quota, project suspension, resource exhaustion). Self-healing the sink will NOT fix it — classify and delegate (see [Error Classification](#error-classification)).

### T2 — Dropped logs

Detected as a volume gap between expected ingestion (external SLO / baseline) and delivered entries.

```bash
# Count delivered entries in the last 5 minutes (compare against expected baseline)
gcloud logging read "timestamp >= \"$(date -u -d '-5 min' +%Y-%m-%dT%H:%M:%SZ)\"" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq 'length'
```

**Remediation:** diagnose only. Follows the same delegate path as T1.

### T3 — Log bucket retention breach

Detected when a custom bucket's `retentionDays` drops below the compliance floor (operator-supplied `{{user.retention_floor_days}}`, default 30).

```bash
# List custom buckets and flag any below the retention floor
FLOOR="{{user.retention_floor_days:-30}}"
gcloud logging buckets list --location=global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -r --argjson f "$FLOOR" '.[] | select(.name | test("_Default|_Required") | not) | select(.retentionDays < $f) | "\(.name)\t\(.retentionDays)"'
```

## Self-Healing Actions

### Action A — Restore bucket retention (T3)

> Idempotent, gated. Only for **unlocked** custom buckets. Never touches `_Default`/`_Required` or a **locked** bucket (locked retention is immutable → `HALT`).

#### Dry-run

```bash
BUCKET="{{user.log_bucket_name}}"; REGION="{{user.region:-global}}"
echo "[DRY-RUN] Would raise retention to floor:"
echo "  gcloud logging buckets update \"$BUCKET\" --location=\"$REGION\" \\"
echo "    --retention-days=\"{{user.retention_floor_days:-30}}\" \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single bucket, same skill)"
```

#### Idempotency

Re-applying `--retention-days` with the same value is a no-op; applying a higher value only ever increases retention (never shortens), so repeats are safe.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Bucket unlocked | `describe` shows `locked == false` | HALT — locked buckets are immutable |
| Not reserved | `name` not `_Default`/`_Required` | HALT — protected bucket |
| Increase-only | new value ≥ current `retentionDays` | HALT — never shorten retention |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
gcloud logging buckets update "$BUCKET" --location="$REGION" \
  --retention-days="{{user.retention_floor_days:-30}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

#### Validate

```bash
gcloud logging buckets describe "$BUCKET" --location="$REGION" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.retentionDays >= ({{user.retention_floor_days:-30}})' && echo "✅ Retention restored"
```

### Action B — Re-create drifted sink (T-sink)

> Idempotent, gated. Primary auto-remediable path. See `aiops-log-pipeline-anomaly.md` §Anomaly 2 for the full capture → diff flow.

#### Dry-run

```bash
SINK="{{user.sink_name}}"
echo "[DRY-RUN] Would re-create sink to restore desired state:"
echo "  gcloud logging sinks create \"$SINK\" \"{{user.sink_destination}}\" \\"
echo "    --log-filter='{{user.filter_query}}' \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T2 (writes to destination owned by another skill)"
```

#### Idempotency

Re-creating with identical `name`+`destination`+`filter` re-applies the desired config; unchanged sinks are no-ops.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Idempotent | Params match desired state | HALT if name collides with unrelated sink |
| Destination exists | Destination reachable | HALT — delegate to destination skill |
| Blast radius | Tier ≤ T2 | HALT if T3/T4 (cross-project / `_Required`) |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply + validate

```bash
gcloud logging sinks create "$SINK" "{{user.sink_destination}}" \
  --log-filter="{{user.filter_query}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
# Re-grant writer identity (idempotent no-op if already granted)
WRITER_IDENTITY=$(gcloud logging sinks describe "$SINK" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq -r '.writerIdentity')
echo "[EXEC] Ensure $WRITER_IDENTITY has write on destination (delegate to gcp-bigquery-ops / gcp-pubsub-ops / gcp-gcs-ops)"
```

### Action C — Restore log-router exclusion drift

> Idempotent, gated. Same dry-run → gate → apply → validate pattern as Action B, using `gcloud logging exclusions describe/create`. Exclusions are **T2** (affect all log readers + Monitoring alert policies) — note this in output.

### HALT list (never auto-mutate)

| Action | Reason |
|--------|--------|
| Delete bucket / sink | Irreversible, data loss |
| Modify `_Default` / `_Required` | Protected, org-critical |
| Shorten / unlock retention | Compliance + immutability violation |
| Cross-project / org log router | Out of scope, blast radius T3/T4 |

## Error Classification

Map every detected anomaly to [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) before choosing remediation. Recovery vocabulary (`HALT` / `RETRY` / `REMEDIATE` / `ESCALATE`) and `idempotent_safe` flag are defined there.

| Logging symptom | Taxonomy dimension | Canonical code | Recovery | Idempotent safe |
|-----------------|--------------------|----------------|----------|:----------------:|
| Bucket retention below floor | Configuration | `INVALID_ARGUMENT` (if malformed) | `REMEDIATE` (raise retention) | true |
| Sink config drift | Configuration | `INVALID_ARGUMENT` (drift) | `REMEDIATE` (re-create) | true |
| Writer IAM lost | Permission | `PERMISSION_DENIED` | `REMEDIATE` (re-grant) | true |
| Ingestion backlog/drop (quota) | Quota | `QUOTA_EXCEEDED` | `REMEDIATE` / delegate | true |
| Ingestion backlog/drop (suspended) | Dependency | `BILLING_NOT_ENABLED` | `HALT` | false |
| Transient read failure | Network | `UNAVAILABLE` | `RETRY` | true |
| Unknown internal | Unknown | `INTERNAL` | `RETRY` → `ESCALATE` | true |

## Blast Radius

Apply the tiers from [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) (HARD rule: only a pointer — never inline cross-domain descriptions):

- Bucket retention restore → **T1** (same skill, single bucket) → dry-run + gate.
- Sink re-create → **T2** (writes to destination owned by another skill) → dry-run + cross-skill note, confirm destination exists.
- Exclusion restore → **T2** (affects Monitoring alert policies) → note in output.
- Cross-project aggregated sink → **T3** → `HALT`.
- `_Default` / `_Required` / org log router → **T4** → `HALT`, never auto-mutate.

> 详见 docs/cross-skill-blast-radius.md

## GCL Connection

This runbook is the detection→remediation leg of the cross-skill GCL loop. Wire it to the runner so every self-healing action is audited and fed back:

- **State capture:** `gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` imports `StateSnapshot` (from `self_correction_mechanism.py`) and invokes it per command to capture pre/post execution state. Use `StateSnapshot` to record the bucket/sink state before and after each Action A/B/C so the diff is provable.
- **Degradation gate:** the same script imports `DegradationDetector` and feeds it consecutive failure patterns; when `failure_count` crosses `threshold` it degrades to human-in-the-loop. Surface repeated `HALT`/failed gates to that detector rather than retrying blindly.
- **Feedback loop:** `gcp-gcl-runner-ops/trace_feedback.py` (`scan_traces`, `aggregate`, `build_report`) consumes persisted GCL traces to compute per-skill quality (`SkillQuality`) — feed it the trace from each self-healing run so Logging-specific failure patterns refine future auto-remediation thresholds.

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。

## See Also

- [error-taxonomy.md](../../../docs/error-taxonomy.md) — unified cross-skill error classification + recovery vocabulary
- [cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — blast radius tiers and gates
- [aiops-log-pipeline-anomaly.md](aiops-log-pipeline-anomaly.md) — sibling runbook (ingestion/sink drift details)
- [gcp-logging-ops SKILL.md](../../SKILL.md) — base operations (buckets, sinks, exclusions)
- [gcp-gcl-runner-ops](../../../gcp-gcl-runner-ops/SKILL.md) — Generator-Critic-Loop runner
