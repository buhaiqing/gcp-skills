# AIOps Log Anomaly Detection — Cloud Logging

> Agent runbook for detecting log-stream anomalies: volume spikes, error-rate anomalies, and new-error-pattern detection. Every action is **dry-run first**, **idempotent**, and **gated**; mutating actions are tabled and destructive ones marked `HALT`.

## Table of Contents

1. [Overview](#overview)
2. [Detection Capabilities](#detection-capabilities)
3. [Prerequisites](#prerequisites)
4. [Anomaly 1 — Volume Spike](#anomaly-1--volume-spike)
5. [Anomaly 2 — Error-Rate Anomaly](#anomaly-2--error-rate-anomaly)
6. [Anomaly 3 — New-Error-Pattern Detection](#anomaly-3--new-error-pattern-detection)
7. [Error Classification](#error-classification)
8. [Blast Radius](#blast-radius)
9. [GCL Connection](#gcl-connection)
10. [See Also](#see-also)

## Overview

Log streams carry early warning signals: a sudden volume spike may mean a runaway service or an attack; an error-rate anomaly means a regression; a never-seen error pattern means a new failure mode. This runbook gives an agent the detection path and a gated remediation path:

```
detect anomaly → classify (error-taxonomy) → dry-run action → gate check → apply (or HALT) → validate
```

### Safety posture

- **Credential masking (§0.1):** NEVER print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` value. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.
- **Detection is read-only:** All detection queries are `gcloud logging read` — no mutation.
- **Dry-run first:** Any downstream mutating action (exclusion, sink, alert) prints the exact command first.
- **HALT on destructive:** Deleting buckets/sinks, modifying `_Default`/`_Required`, cross-project mutations → never auto-run.

## Detection Capabilities

| Anomaly | Signal | Severity | Auto-remediable |
|---------|--------|----------|:----------------:|
| Volume spike | Entry count >> baseline (e.g. >3x) | Medium | No (diagnose / alert) |
| Error-rate anomaly | `severity>=ERROR` ratio >> baseline | High | No (diagnose / alert) |
| New-error-pattern | `jsonPayload.error.code` / message never seen in window | High | No (surface to human) |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Logging API | `gcloud services list --enabled --filter="name:logging.googleapis.com"` | Enabled | `gcloud services enable logging.googleapis.com` |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Credentials file | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | Exists | HALT — set `GOOGLE_APPLICATION_CREDENTIALS=****` |
| Project | `gcloud config get-value project` | Set | HALT — set project |

## Anomaly 1 — Volume Spike

### Detect

```bash
# Count entries in the last 10 minutes, broken down per 2-minute bucket
gcloud logging read "timestamp >= \"$(date -u -d '-10 min' +%Y-%m-%dT%H:%M:%SZ)\"" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" \
  | jq -r '.[].timestamp' \
  | cut -c1-16 | sort | uniq -c
```

Compare against the operator-supplied baseline (`{{user.volume_baseline}}` entries / 2-min). A sustained >3x burst is a spike.

### Remediation decision

| Finding | Classification (error-taxonomy) | Action |
|---------|----------------------------------|--------|
| Spike caused by `QUOTA_EXCEEDED` downstream | Quota dimension | `REMEDIATE` / delegate to `gcp-billing-ops` |
| Spike caused by app-level loop / attack | Unknown | `ESCALATE` (create exclusion after human gate) |
| Transient burst | Unknown | Close anomaly |

**No auto-mutation.** If a volume cap is desired, the only safe mutating action is a new **exclusion** (Action gate below).

#### Optional — add volume-cap exclusion (DRY-RUN + gate)

```bash
EXCLUSION="{{user.exclusion_name}}"
echo "[DRY-RUN] Would create exclusion to cap noisy log source:"
echo "  gcloud logging exclusions create \"$EXCLUSION\" \\"
echo "    --log-filter='{{user.filter_query}}' --description='volume cap (gated)' \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T2 (affects all log readers + Monitoring alert policies)"
```

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Idempotent | Name not in use (`describe` → NOT_FOUND) | HALT if name collides |
| Blast radius | Tier ≤ T2 | HALT if cross-project |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

Apply only after explicit human gate pass: `gcloud logging exclusions create "$EXCLUSION" --log-filter='{{user.filter_query}}' --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`.

## Anomaly 2 — Error-Rate Anomaly

### Detect

```bash
# Error ratio over the last 10 minutes
NOW=$(date -u -d '-10 min' +%Y-%m-%dT%H:%M:%SZ)
TOTAL=$(gcloud logging read "timestamp >= \"$NOW\"" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq 'length')
ERRS=$(gcloud logging read "timestamp >= \"$NOW\" AND severity>=ERROR" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq 'length')
echo "error_ratio=$((ERRS * 100 / (TOTAL > 0 ? TOTAL : 1)))% (baseline ${{user.error_rate_baseline:-1}}%)"
```

A sustained ratio materially above `{{user.error_rate_baseline}}` is an anomaly.

### Remediation decision

| Finding | Classification (error-taxonomy) | Action |
|---------|----------------------------------|--------|
| Errors from `PERMISSION_DENIED` | Permission | `REMEDIATE` (re-grant) — delegate |
| Errors from `UNAVAILABLE` | Network | `RETRY` (backoff; no mutation) |
| Errors from app regression | Unknown | `ESCALATE` to on-call |

**No auto-mutation** — error spikes are diagnostic signals, not fixable by Logging config.

## Anomaly 3 — New-Error-Pattern Detection

### Detect

```bash
# Find error codes seen in the last 1h that were NOT seen in the prior 24h baseline
RECENT=$(gcloud logging read "timestamp >= \"$(date -u -d '-1h' +%Y-%m-%dT%H:%M:%SZ)\" AND severity>=ERROR" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -r '.[].jsonPayload.error.code // .[].protoPayload.status.message // empty' | sort -u)
BASELINE=$(gcloud logging read "timestamp >= \"$(date -u -d '-24h' +%Y-%m-%dT%H:%M:%SZ)\" AND timestamp < \"$(date -u -d '-1h' +%Y-%m-%dT%H:%M:%SZ)\" AND severity>=ERROR" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -r '.[].jsonPayload.error.code // .[].protoPayload.status.message // empty' | sort -u)
echo "$RECENT" | while read -r code; do echo "$BASELINE" | grep -qx "$code" || echo "🆕 NEW pattern: $code"; done
```

### Remediation decision

| Finding | Classification (error-taxonomy) | Action |
|---------|----------------------------------|--------|
| New code maps to `PERMISSION_DENIED` | Permission | `REMEDIATE` (re-grant) — delegate |
| New code maps to `INTERNAL` | Unknown | `RETRY` → `ESCALATE` |
| New code unmapped | Unknown | `ESCALATE` (capture raw code/message) |

**No auto-mutation** — a new error pattern is a hard `HALT` for auto-fix; surface to human with the raw code/message.

## Error Classification

Map every detected anomaly to [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) before choosing remediation. Recovery vocabulary (`HALT` / `RETRY` / `REMEDIATE` / `ESCALATE`) and `idempotent_safe` flag are defined there.

| Logging symptom | Taxonomy dimension | Canonical code | Recovery | Idempotent safe |
|-----------------|--------------------|----------------|----------|:----------------:|
| Volume spike (quota) | Quota | `QUOTA_EXCEEDED` | `REMEDIATE` / delegate | true |
| Volume spike (attack/loop) | Unknown | `UNCLASSIFIED` | `ESCALATE` | true |
| Error-rate spike (permission) | Permission | `PERMISSION_DENIED` | `REMEDIATE` (re-grant) | true |
| Error-rate spike (network) | Network | `UNAVAILABLE` | `RETRY` | true |
| Error-rate spike (app) | Unknown | `INTERNAL` | `ESCALATE` | true |
| New error pattern (unmapped) | Unknown | `UNCLASSIFIED` | `ESCALATE` | true |

## Blast Radius

Apply the tiers from [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) (HARD rule: only a pointer — never inline cross-domain descriptions):

- Pure detection (all `gcloud logging read`) → read-only, no blast radius.
- Volume-cap exclusion → **T2** (affects all log readers + Monitoring alert policies) → gate + note.
- Cross-project sink/exclusion → **T3** → `HALT`.
- `_Default` / `_Required` / org log router → **T4** → `HALT`, never auto-mutate.

> 详见 docs/cross-skill-blast-radius.md

## GCL Connection

Detection and any gated action feed the cross-skill GCL loop:

- **State capture:** `gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` imports `StateSnapshot` (from `self_correction_mechanism.py`) and captures pre/post state per command. Use it to record the exclusion/sink state before and after any gated Action so the diff is provable.
- **Degradation gate:** the same script imports `DegradationDetector` and degrades to human-in-the-loop when consecutive `HALT`/failed gates cross `threshold`. Repeated new-error-pattern escalations should be routed there rather than retried.
- **Feedback loop:** `gcp-gcl-runner-ops/trace_feedback.py` (`scan_traces`, `aggregate`, `build_report`) consumes persisted GCL traces to compute per-skill `SkillQuality` — feed it each detection run so Logging-specific anomaly thresholds refine over time.

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。

## See Also

- [error-taxonomy.md](../../../docs/error-taxonomy.md) — unified cross-skill error classification + recovery vocabulary
- [cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — blast radius tiers and gates
- [self-healing-runbook.md](self-healing-runbook.md) — sibling runbook (ingestion/sink/bucket self-healing)
- [gcp-logging-ops SKILL.md](../../SKILL.md) — base operations (buckets, sinks, exclusions)
- [gcp-gcl-runner-ops](../../../gcp-gcl-runner-ops/SKILL.md) — Generator-Critic-Loop runner
