# AIOps Self-Healing Runbook — Filestore

> Agent runbook for closed-loop self-healing of Filestore failures: capacity exhaustion, volume offline, snapshot drift, mount misconfig. Every remediation action is **dry-run first**, **idempotent**, and **gated**; destructive actions (delete instance/volume, restore snapshot) are marked `HALT`.

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

Filestore can degrade in ways that stall workloads depending on NFS mounts: a volume fills past its capacity and writes start failing, an instance goes offline and clients hang, or snapshots drift so recovery points go stale. This runbook closes the loop:

```
trigger → detect → classify (error-taxonomy) → dry-run remediation → gate check → apply (or HALT) → validate → cross-skill if needed
```

### Safety posture

- **Credential masking (§0.1):** NEVER print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` value. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.
- **Dry-run first:** Every mutating action prints the exact `gcloud filestore` command it *would* run, then requires an explicit apply step.
- **Idempotent:** Re-applying a config with identical params is a no-op if unchanged.
- **HALT on destructive:** Delete instance/volume, restore snapshot over live data, detach → never auto-run.

## Detection Capabilities

| Anomaly | Signal | Severity | Auto-remediable |
|---------|--------|----------|:----------------:|
| Capacity exhaustion | `used_bytes` > 85% of `capacity_gb` | Critical | **Yes** (expand capacity) |
| Volume offline | State ≠ `READY` | High | No (HALT — manual) |
| Snapshot drift | Latest snapshot age > `{{user.snapshot_max_age}}` | Medium | **Yes** (create snapshot) |
| Mount misconfig | Client cannot mount (stale handle) | Medium | **Yes** (flag for review) |
| Throughput tier low | IOPS below workload need | Low | **Yes** (note tier upgrade) |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Filestore API | `gcloud services list --enabled --filter="name:file.googleapis.com"` | Enabled | `gcloud services enable file.googleapis.com` |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Credentials file | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | Exists | HALT — set `GOOGLE_APPLICATION_CREDENTIALS=****` |
| Project | `gcloud config get-value project` | Set | HALT — set project |
| Monitoring API (alert trigger) | `gcloud services list --enabled --filter="name:monitoring.googleapis.com"` | Enabled | Delegate to `gcp-monitoring-ops` |

## Trigger Conditions

### T1 — Capacity exhaustion

Detected as `used_bytes` > 85% of `capacity_gb`.

```bash
gcloud filestore instances describe "{{user.instance}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '(.fileShares[0].capacityGb * 0.85 | floor) < (.fileShares[0].usedGb // 0)' \
  && echo "CAPACITY_EXHAUSTED"
```

### T2 — Snapshot drift

Detected as the latest snapshot older than `{{user.snapshot_max_age}}`.

```bash
gcloud filestore snapshots list --instance="{{user.instance}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -r 'sort_by(.createTime)[-1].createTime // "1970-01-01T00:00:00Z"' \
  | { read -r ts; [ "$(date -d "$ts" +%s)" -lt "$(($(date +%s) - {{user.snapshot_max_age_seconds}}))" ] && echo "SNAPSHOT_DRIFT"; }
```

### T3 — Volume offline

Detected as instance state ≠ `READY`.

```bash
gcloud filestore instances describe "{{user.instance}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.state != "READY"' && echo "OFFLINE"
```

## Self-Healing Actions

### Action A — Expand capacity (T1)

> Idempotent, gated. Increases `fileShares[0].capacityGb` (only upward; Filestore cannot shrink).

#### Dry-run

```bash
INSTANCE="{{user.instance}}"
echo "[DRY-RUN] Would expand capacity to {{user.new_capacity_gb}}GB:"
echo "  gcloud filestore instances update \"$INSTANCE\" --location=\"{{user.location}}\" \\"
echo "    --file-share=name={{user.fileshare}},capacity={{user.new_capacity_gb}}GB \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single instance, same skill)"
```

#### Idempotency

Re-applying the same (or smaller) size is a no-op; the pre-check only scales if current < target.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Increase-only | new ≥ current `capacityGb` | HALT — cannot shrink |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
CURRENT=$(gcloud filestore instances describe "{{user.instance}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -r '.fileShares[0].capacityGb')
if [ "$CURRENT" -lt "{{user.new_capacity_gb}}" ]; then
  gcloud filestore instances update "{{user.instance}}" --location="{{user.location}}" \
    --file-share="name={{user.fileshare}},capacity={{user.new_capacity_gb}}GB" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
fi
```

#### Validate

```bash
gcloud filestore instances describe "{{user.instance}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.fileShares[0].capacityGb >= ({{user.new_capacity_gb}})' \
  && echo "✅ Capacity expanded"
```

### Action B — Create snapshot (T2)

> Idempotent, gated. Creates a fresh snapshot for recovery-point currency. Never restores over live data (that is HALT).

#### Dry-run

```bash
echo "[DRY-RUN] Would create snapshot {{user.snapshot_name}}:"
echo "  gcloud filestore snapshots create \"{{user.snapshot_name}}\" \\"
echo "    --instance=\"{{user.instance}}\" --location=\"{{user.location}}\" \\"
echo "    --file-share={{user.fileshare}} --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single instance, same skill)"
```

#### Idempotency

Re-creating a snapshot with the same name fails with ALREADY_EXISTS (no data change); safe to skip.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Create only | No restore | HALT — restore is destructive |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
gcloud filestore snapshots create "{{user.snapshot_name}}" \
  --instance="{{user.instance}}" --location="{{user.location}}" \
  --file-share="{{user.fileshare}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" || true
```

#### Validate

```bash
gcloud filestore snapshots describe "{{user.snapshot_name}}" \
  --instance="{{user.instance}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.name' >/dev/null && echo "✅ Snapshot created"
```

### Action C — Flag mount misconfig (T3)

> Idempotent, gated. Adds a label marking the instance for mount-review; does NOT detach or remount clients (client-side → HALT).

#### Dry-run

```bash
INSTANCE="{{user.instance}}"
echo "[DRY-RUN] Would label instance mount-review for client-side check:"
echo "  gcloud filestore instances update \"$INSTANCE\" --location=\"{{user.location}}\" \\"
echo "    --update-labels=aiops_mount_review=true --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single instance, same skill)"
```

#### Idempotency

Re-applying the same label is a no-op; the describe check confirms current labels before apply.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Label only | No detach/remount | HALT — client impact |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
gcloud filestore instances update "{{user.instance}}" --location="{{user.location}}" \
  --update-labels=aiops_mount_review=true \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

#### Validate

```bash
gcloud filestore instances describe "{{user.instance}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.labels.aiops_mount_review == "true"' \
  && echo "✅ Mount-review label applied"
```

### HALT list (never auto-mutate)

| Action | Reason |
|--------|--------|
| Delete instance / volume | Irreversible, data loss |
| Restore snapshot over live data | Overwrites live data |
| Detach / remount clients | Client-side impact |
| Tier downgrade | Performance regression |

## Error Classification

Map every detected anomaly to [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) before choosing remediation. Recovery vocabulary (`HALT` / `RETRY` / `REMEDIATE` / `ESCALATE`) and `idempotent_safe` flag are defined there.

| Filestore symptom | Taxonomy dimension | Canonical code | Recovery | Idempotent safe |
|-------------------|--------------------|----------------|----------|:----------------:|
| Capacity exhaustion | Quota | `QUOTA_EXCEEDED` | `REMEDIATE` (expand) | true |
| Snapshot drift | Configuration | `INVALID_ARGUMENT` | `REMEDIATE` (snapshot) | true |
| Volume offline | Dependency | `UNAVAILABLE` | `HALT` / escalate | false |
| Mount misconfig | Configuration | `INVALID_ARGUMENT` | `REMEDIATE` (flag) | true |
| Throughput tier low | Performance | `RESOURCE_EXHAUSTED` | `REMEDIATE` (note) | true |
| Transient API failure | Network | `UNAVAILABLE` | `RETRY` | true |
| Unknown internal | Unknown | `INTERNAL` | `RETRY` → `ESCALATE` | true |

## Blast Radius

Apply the tiers from [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) (HARD rule: only a pointer — never inline cross-domain descriptions):

- Expand capacity / snapshot / label → **T1** (same skill, single instance) → dry-run + gate.
- Cross-instance snapshot copy → **T2** (affects multiple instances) → note in output.
- Delete instance / restore snapshot → **T4** → `HALT`, never auto-mutate.

> 详见 docs/cross-skill-blast-radius.md

## GCL Connection

This runbook is the detection→remediation leg of the cross-skill GCL loop. Wire it to the runner so every self-healing action is audited and fed back:

- **State capture:** `gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` imports `StateSnapshot` (from `self_correction_mechanism.py`) and invokes it per command to capture pre/post execution state. Use `StateSnapshot` to record the instance capacity/snapshot/labels before and after each Action A/B/C so the diff is provable.
- **Degradation gate:** the same script imports `DegradationDetector` and feeds it consecutive failure patterns; when `failure_count` crosses `threshold` it degrades to human-in-the-loop. Surface repeated `HALT`/failed gates to that detector rather than retrying blindly.
- **Feedback loop:** `gcp-gcl-runner-ops/trace_feedback.py` (`scan_traces`, `aggregate`, `build_report`) consumes persisted GCL traces to compute per-skill quality (`SkillQuality`) — feed it the trace from each self-healing run so Filestore-specific failure patterns refine future auto-remediation thresholds.

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。

## See Also

- [error-taxonomy.md](../../../docs/error-taxonomy.md) — unified cross-skill error classification + recovery vocabulary
- [cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — blast radius tiers and gates
- [aiops-filestore-anomaly.md](aiops-filestore-anomaly.md) — sibling runbook (capacity/volume anomaly details)
- [gcp-filestore-ops SKILL.md](../../SKILL.md) — base operations (instances, snapshots, fileshares)
- [gcp-gcl-runner-ops](../../../gcp-gcl-runner-ops/SKILL.md) — Generator-Critic-Loop runner
