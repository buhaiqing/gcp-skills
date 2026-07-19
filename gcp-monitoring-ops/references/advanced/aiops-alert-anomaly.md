# AIOps Alert Anomaly & Self-Healing — Google Cloud Monitoring

> Runbook for agents to detect alerting anomalies in Cloud Monitoring (alert storms, misconfigured policies) and apply **safe, idempotent, gated** self-healing. This file focuses on the **alerting plane itself** — it does NOT cover security-center auto-mute (see `gcp-securitycenter-ops`) or cross-product remediation details (delegated via links below).

## Table of Contents

1. [Overview](#overview)
2. [Detection: Alert Storm](#detection-alert-storm)
3. [Detection: Misconfigured / Flapping Policies](#detection-misconfigured--flapping-policies)
4. [Self-Healing: Silence / Suppression](#self-healing-silence--suppression)
5. [Safety Gates (MANDATORY)](#safety-gates-mandatory)
6. [Cross-Skill Trigger Map](#cross-skill-trigger-map)
7. [Error Taxonomy](#error-taxonomy)
8. [See Also](#see-also)

## Overview

Cloud Monitoring is the natural trigger surface for AIOps self-healing: when an alert fires, an agent can investigate and remediate. But the alerting plane itself can also misbehave — **alert storms** (hundreds of firings from one bad policy) and **flapping** (rapid fire/clear cycles) cause fatigue and hide real incidents.

This runbook defines:

- How to **detect** alerting anomalies via Monitoring APIs / `gcloud`.
- How to **self-heal** with silence/suppression — always `dry-run` first, **idempotent**, behind a **human-review gate**.
- How a monitoring anomaly **triggers other skills' AIOps runbooks** (delegation, not duplication).

> **Credential Masking (§0.1):** NEVER print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` value. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.

## Detection: Alert Storm

**Definition:** A single alert policy (or a small set sharing a label/condition) produces an abnormally high number of firing incidents within a short window — typically a misconfigured threshold, a broken exporter, or a cascading dependency.

### Step 1 — Count firing incidents per policy (last 10 min)

```bash
# List currently open incidents grouped by policy
gcloud monitoring policies list-incidents \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="state=OPEN" \
  --format="json" | jq -r '
    [.[] | select(.metadata.severity != null)] as $all
    | group_by(.alertPolicy.name)[] 
    | {policy: .[0].alertPolicy.name, count: length}
    | select(.count > 10)'   # threshold: >10 open incidents per policy
```

### Step 2 — Confirm storm vs. real spread

```bash
# Inspect time distribution — a storm clusters in seconds/minutes
gcloud monitoring policies list-incidents \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="state=OPEN" \
  --format="json" | jq -r '
    .[] | .metadata.startTime' | sort | head -20
```

| Signal | Storm (likely misconfig) | Real incident (spread) |
|--------|--------------------------|------------------------|
| Incidents per policy | >10 in <5 min | <10, staggered |
| Resource diversity | Same resource / same label | Many distinct resources |
| Value vs threshold | Just barely over, flat | Clear sustained breach |

### Step 3 — Identify root cause candidate

```bash
# Pull the firing policy's condition to inspect threshold/duration
gcloud monitoring policies describe "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{displayName, conditions, combiner}'
```

## Detection: Misconfigured / Flapping Policies

**Definition:** A policy whose incidents open and close repeatedly (flapping) within minutes — usually `duration` too short or threshold too tight.

```bash
# Count open+closed transitions per policy in last hour
gcloud monitoring policies list-incidents \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="state=CLOSED" \
  --format="json" | jq -r '
    group_by(.alertPolicy.name)[] 
    | {policy: .[0].alertPolicy.name, closed_count: length}
    | select(.closed_count > 5)'
```

| Signal | Flapping | Healthy |
|--------|----------|---------|
| Open→close cycles/hour | >5 | ≤1 |
| `duration` field | <60s | ≥60s |
| Incident lifetime | seconds | minutes+ |

## Self-Healing: Silence / Suppression

When a storm or flapping policy is confirmed, the **lowest-risk** self-healing action is to **silence** (mute) the offending policy temporarily — NOT delete it, NOT modify its threshold (those are HALT, see below).

### Dry-run (ALWAYS first)

```bash
# Preview what would be silenced — no mutation
gcloud monitoring policies describe "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, displayName, enabled}'

echo "[DRY-RUN] Would silence policy {{user.alert_policy_id}} for 30m"
```

### Apply silence (idempotent + gated)

Silencing is **idempotent**: re-applying `enabled=false` on an already-disabled policy is a no-op (no error, no state change). The gate below still applies.

```bash
# HALT: requires human-review gate (see Safety Gates) before executing
gcloud monitoring policies update "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --no-enabled
```

### Auto-unsilence (scheduled, idempotent)

```bash
# Re-enable after the storm window — safe to run even if already enabled
gcloud monitoring policies update "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --enabled
```

### What is NOT allowed here (HALT — delegate / require explicit approval)

| Action | Risk | Gate |
|--------|------|------|
| Delete alert policy | **High** — irreversible, loses detection | HALT: explicit user confirmation with exact policy ID |
| Modify threshold / condition | **Medium** — may hide real incidents | HALT: human review + change ticket |
| Bulk-silence across project | **High** — blinds monitoring | HALT: never auto-bulk |
| Security-center auto-mute | Out of scope | See `gcp-securitycenter-ops` (not duplicated here) |

## Safety Gates (MANDATORY)

Every self-healing action in this runbook obeys three gates:

1. **Dry-run first** — Always preview the target policy state before any mutation. No exception.
2. **Idempotent** — Re-applying the same silence/unsilence yields identical state; safe to retry.
3. **Human-review gate** — Any `enabled=false` (silence) or `enabled=true` (unsilence) on a **production** policy requires an explicit approval token / interactive confirmation. The agent MUST NOT auto-silence without it.

```
[HH:MM:SS] [DIAG] policy={{user.alert_policy_id}} open_incidents=N
[HH:MM:SS] [DIAG] storm_detected=true|false
[HH:MM:SS] [DRY-RUN] action=silence duration=30m (no mutation)
[HH:MM:SS] [WARN] HALT: awaiting human-review gate before silence
[HH:MM:SS] [EXEC] action=silence approved_by=human (if gate passed)
[HH:MM:SS] [RESULT] policy_enabled=false
```

> **Blast radius:** Silencing a policy removes detection coverage for its condition during the mute window. Always record the mute window and auto-unsilence. See [docs/cross-skill-blast-radius.md](../docs/cross-skill-blast-radius.md).

## Cross-Skill Trigger Map

Monitoring detects an anomaly → delegates investigation/remediation to the owning skill's AIOps runbook. Monitoring itself only silences its own alerting; it does NOT remediate the underlying resource.

```
Alert fires (monitoring)
   │
   ├─ VM CPU/Memory breach ──────► gcp-gce-ops  (aiops runbook: resize/restart)
   ├─ GKE node pressure ─────────► gcp-gke-ops  (aiops runbook: drain/scale)
   ├─ DB slow query / failover ──► gcp-cloudsql-ops (aiops runbook: failover)
   ├─ Network egress anomaly ────► gcp-vpc-ops  (aiops-network-anomaly.md)
   ├─ Security finding ──────────► gcp-securitycenter-ops (auto-mute runbook)
   └─ Alert storm / flapping ───► THIS FILE (silence own policy only)
```

| Trigger | Delegated Skill | Monitoring's Role |
|---------|----------------|-------------------|
| Resource metric breach | `gcp-gce-ops` / `gcp-gke-ops` / `gcp-cloudsql-ops` | Detect + hand off; do not remediate resource |
| Network anomaly | `gcp-vpc-ops` | Detect + hand off |
| Security finding | `gcp-securitycenter-ops` | Detect + hand off (auto-mute lives there) |
| Alerting-plane anomaly | (self) | Silence own policy per Safety Gates |

## Error Taxonomy

| Error | Cause | Resolution |
|-------|-------|------------|
| `policy not found` | Wrong `{{user.alert_policy_id}}` | Re-list policies; verify ID |
| `permission denied` | Missing `roles/monitoring.admin` | Request least-privilege role; HALT if ungrantable |
| `incident query timeout` | Too large time window | Narrow `--filter` to last 10 min |
| `silence rejected` | Human-review gate not satisfied | Await approval; do not retry blindly |
| `already disabled` | Idempotent no-op | Treat as success; log RESULT |
| `auto-unsilence failed` | Policy deleted meanwhile | Log WARN; verify via `list-incidents` |

## See Also

- [Cloud Monitoring Docs](https://cloud.google.com/monitoring/docs)
- [VPC AIOps Anomaly](../gcp-vpc-ops/references/advanced/aiops-network-anomaly.md)
- [Security Center Auto-Mute](../../gcp-securitycenter-ops/SKILL.md) — out-of-scope auto-mute logic
- [Error Taxonomy (repo-wide)](../../docs/error-taxonomy.md)
- [Cross-Skill Blast Radius](../../docs/cross-skill-blast-radius.md)
