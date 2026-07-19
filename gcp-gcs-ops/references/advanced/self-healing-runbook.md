# AIOps Self-Healing Runbook — Cloud Storage

> Agent runbook for closed-loop self-healing of Cloud Storage failures: bucket anomaly / lifecycle breach, retention policy drift, public-access exposure, storage-class misconfiguration. Every remediation action is **dry-run first**, **idempotent**, and **gated**; destructive actions are marked `HALT`.

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

Cloud Storage can degrade in ways that are invisible until an audit or dashboard goes dark: a bucket silently breaches its lifecycle policy, a retention policy drifts below the compliance floor, or a bucket becomes publicly accessible. This runbook closes the loop:

```
trigger → detect → classify (error-taxonomy) → dry-run remediation → gate check → apply (or HALT) → validate → cross-skill if needed
```

### Safety posture

- **Credential masking (§0.1):** NEVER print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` value. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.
- **Dry-run first:** Every mutating action prints the exact `gcloud storage` / `gsutil` command it *would* run, then requires an explicit apply step.
- **Idempotent:** Re-applying a lifecycle/retention/IAM update with identical params is a no-op if unchanged.
- **HALT on destructive:** Deleting buckets/objects, locking retention, disabling PAP, cross-project mutations → never auto-run.

## Detection Capabilities

| Anomaly | Signal | Severity | Auto-remediable |
|---------|--------|----------|:----------------:|
| Lifecycle policy breach | Objects not transitioning / cost drift vs policy | Medium | **Yes** (re-apply) |
| Retention policy below floor | `retentionPeriod` below compliance floor | Medium | **Yes** (raise, unlocked only) |
| Public access exposure | `iamConfiguration.publicAccessPrevention` disabled + public binding | High | **Yes** (re-enable PAP) |
| Storage class misconfig | Hot objects in COLD/ARCHIVE without lifecycle | Low | **Yes** (lifecycle add) |
| Bucket anomaly (unexpected growth) | `total_bytes` deviation vs baseline | Medium | No (diagnose only) |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Storage API | `gcloud services list --enabled --filter="name:storage.googleapis.com"` | Enabled | `gcloud services enable storage.googleapis.com` |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Credentials file | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | Exists | HALT — set `GOOGLE_APPLICATION_CREDENTIALS=****` |
| Project | `gcloud config get-value project` | Set | HALT — set project |
| Monitoring API (alert trigger) | `gcloud services list --enabled --filter="name:monitoring.googleapis.com"` | Enabled | Delegate to `gcp-monitoring-ops` |

## Trigger Conditions

### T1 — Lifecycle policy breach

Detected when a bucket's live lifecycle config diverges from the desired policy (objects not transitioning to the intended storage class / not expiring).

```bash
# Diff live lifecycle against desired policy file
BUCKET="{{user.bucket_name}}"; DESIRED="{{user.lifecycle_file}}"
gcloud storage buckets describe "gs://$BUCKET" --format="json" \
  | jq -S '.lifecycle' > /tmp/live_lc.json
jq -S '.' "$DESIRED" > /tmp/desired_lc.json
diff <(cat /tmp/live_lc.json) <(cat /tmp/desired_lc.json) \
  && echo "OK lifecycle matches" || echo "DRIFT lifecycle diverges"
```

### T2 — Retention policy below floor

Detected when an unlocked bucket's `retentionPeriod` drops below the compliance floor (`{{user.retention_floor_seconds}}`, default 0 = no floor).

```bash
FLOOR="{{user.retention_floor_seconds:-0}}"
gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json" \
  | jq -r --argjson f "$FLOOR" 'select(.retentionPolicy.retentionPeriod < ($f * 1000000000)) | .name'
```

### T3 — Public access exposure

Detected when `publicAccessPrevention` is `inherited`/`unspecified` and a public IAM binding (`allUsers`/`allAuthenticatedUsers`) is present.

```bash
gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json" \
  | jq -e '.iamConfiguration.publicAccessPrevention != "enforced"' >/dev/null \
  && gcloud storage buckets get-iam-policy "gs://{{user.bucket_name}}" --format="json" \
  | jq -e '.bindings[]?.members[] | select(. == "allUsers" or . == "allAuthenticatedUsers")' \
  && echo "EXPOSED public access detected"
```

## Self-Healing Actions

### Action A — Restore lifecycle policy (T1)

> Idempotent, gated. Re-applies the desired lifecycle config. Never deletes objects (that is HALT).

#### Dry-run

```bash
BUCKET="{{user.bucket_name}}"
echo "[DRY-RUN] Would apply lifecycle from {{user.lifecycle_file}}:"
echo "  gcloud storage buckets update \"gs://$BUCKET\" --lifecycle-file=\"{{user.lifecycle_file}}\" \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single bucket, same skill)"
```

#### Idempotency

Re-applying the identical lifecycle JSON is a no-op; the diff check above confirms no change before apply.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| No object delete | Policy contains only SetStorageClass/Delete-age rules per policy | HALT — policy deletes live data |
| Bucket exists | describe returns 200 | HALT |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
gcloud storage buckets update "gs://$BUCKET" \
  --lifecycle-file="{{user.lifecycle_file}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

#### Validate

```bash
gcloud storage buckets describe "gs://$BUCKET" --format="json" \
  | jq -S '.lifecycle' | diff - <(jq -S '.' "{{user.lifecycle_file}}") \
  && echo "✅ Lifecycle restored"
```

### Action B — Raise retention policy (T2)

> Idempotent, gated. Only for **unlocked** buckets. Never touches a **locked** bucket (immutable → `HALT`).

#### Dry-run

```bash
BUCKET="{{user.bucket_name}}"
echo "[DRY-RUN] Would raise retention to {{user.retention_period}}:"
echo "  gcloud storage buckets update \"gs://$BUCKET\" --retention-period=\"{{user.retention_period}}\" \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single bucket, same skill)"
```

#### Idempotency

Re-applying `--retention-period` with the same value is a no-op; applying a higher value only ever increases retention (never shortens), so repeats are safe.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Bucket unlocked | `retentionPolicy.isLocked == false` | HALT — locked buckets are immutable |
| Increase-only | new value ≥ current `retentionPeriod` | HALT — never shorten retention |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
gcloud storage buckets update "gs://$BUCKET" \
  --retention-period="{{user.retention_period}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

#### Validate

```bash
gcloud storage buckets describe "gs://$BUCKET" --format="json" \
  | jq -e '.retentionPolicy.retentionPeriod >= ({{user.retention_period}} * 1000000000)' \
  && echo "✅ Retention restored"
```

### Action C — Re-enable Public Access Prevention (T3)

> Idempotent, gated. Re-enables PAP and removes the public IAM binding. See `aiops-storage-anomaly.md` §Automated Remediation for the full anomaly flow.

#### Dry-run

```bash
BUCKET="{{user.bucket_name}}"
echo "[DRY-RUN] Would enforce public access prevention:"
echo "  gcloud storage buckets update \"gs://$BUCKET\" --public-access-prevention"
echo "[DRY-RUN] Would remove public IAM bindings (allUsers/allAuthenticatedUsers)"
echo "[DRY-RUN] Blast radius tier: T1 (single bucket, same skill)"
```

#### Idempotency

Re-enforcing PAP and removing an already-absent public binding are no-ops.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Intentional public? | No legitimate public use case | HALT — confirm with owner |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply + validate

```bash
gcloud storage buckets update "gs://$BUCKET" --public-access-prevention \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
# Remove public bindings (idempotent no-op if absent)
gcloud storage buckets remove-iam-policy-binding "gs://$BUCKET" \
  --member="allUsers" --role="roles/storage.objectViewer" --format="json" 2>/dev/null || true
gcloud storage buckets describe "gs://$BUCKET" --format="json" \
  | jq -e '.iamConfiguration.publicAccessPrevention == "enforced"' \
  && echo "✅ PAP enforced"
```

### HALT list (never auto-mutate)

| Action | Reason |
|--------|--------|
| Delete bucket / object | Irreversible, data loss |
| Lock retention policy | Immutable, compliance violation |
| Disable PAP on intentional public bucket | May break legitimate public serving |
| Cross-project bucket mutation | Out of scope, blast radius T3/T4 |

## Error Classification

Map every detected anomaly to [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) before choosing remediation. Recovery vocabulary (`HALT` / `RETRY` / `REMEDIATE` / `ESCALATE`) and `idempotent_safe` flag are defined there.

| GCS symptom | Taxonomy dimension | Canonical code | Recovery | Idempotent safe |
|-------------|--------------------|----------------|----------|:----------------:|
| Lifecycle drift | Configuration | `INVALID_ARGUMENT` (drift) | `REMEDIATE` (re-apply) | true |
| Retention below floor | Configuration | `INVALID_ARGUMENT` | `REMEDIATE` (raise) | true |
| Public exposure | Security | `PERMISSION_DENIED` (misconfig) | `REMEDIATE` (enforce PAP) | true |
| Storage class misconfig | Configuration | `INVALID_ARGUMENT` | `REMEDIATE` (lifecycle) | true |
| Bucket anomaly (growth) | Quota | `QUOTA_EXCEEDED` | `REMEDIATE` / delegate | true |
| Transient read failure | Network | `UNAVAILABLE` | `RETRY` | true |
| Unknown internal | Unknown | `INTERNAL` | `RETRY` → `ESCALATE` | true |

## Blast Radius

Apply the tiers from [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) (HARD rule: only a pointer — never inline cross-domain descriptions):

- Lifecycle / retention / PAP restore → **T1** (same skill, single bucket) → dry-run + gate.
- Storage-class lifecycle add → **T1** (single bucket) → dry-run + gate.
- Cross-project bucket replication / aggregated sink → **T3** → `HALT`.
- Org-level PAP / uniform access change → **T4** → `HALT`, never auto-mutate.

> 详见 docs/cross-skill-blast-radius.md

## GCL Connection

This runbook is the detection→remediation leg of the cross-skill GCL loop. Wire it to the runner so every self-healing action is audited and fed back:

- **State capture:** `gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` imports `StateSnapshot` (from `self_correction_mechanism.py`) and invokes it per command to capture pre/post execution state. Use `StateSnapshot` to record the bucket state before and after each Action A/B/C so the diff is provable.
- **Degradation gate:** the same script imports `DegradationDetector` and feeds it consecutive failure patterns; when `failure_count` crosses `threshold` it degrades to human-in-the-loop. Surface repeated `HALT`/failed gates to that detector rather than retrying blindly.
- **Feedback loop:** `gcp-gcl-runner-ops/trace_feedback.py` (`scan_traces`, `aggregate`, `build_report`) consumes persisted GCL traces to compute per-skill quality (`SkillQuality`) — feed it the trace from each self-healing run so Storage-specific failure patterns refine future auto-remediation thresholds.

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。

## See Also

- [error-taxonomy.md](../../../docs/error-taxonomy.md) — unified cross-skill error classification + recovery vocabulary
- [cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — blast radius tiers and gates
- [aiops-storage-anomaly.md](aiops-storage-anomaly.md) — sibling runbook (access/storage anomaly details)
- [gcp-gcs-ops SKILL.md](../../SKILL.md) — base operations (buckets, lifecycle, retention, IAM)
- [gcp-gcl-runner-ops](../../../gcp-gcl-runner-ops/SKILL.md) — Generator-Critic-Loop runner
