# AIOps Self-Healing Runbook — Pub/Sub

> Agent runbook for closed-loop self-healing of Pub/Sub failures: backlog growth, DLQ spike, subscription stale, topic misconfig. Every remediation action is **dry-run first**, **idempotent**, and **gated**; destructive actions (delete topic/subscription, purge messages) are marked `HALT`.

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

Pub/Sub can degrade in ways that silently drop or stall messages: a subscription's backlog grows unbounded because consumers are down, a dead-letter topic fills with poison messages, or a subscription goes stale with no active puller. This runbook closes the loop:

```
trigger → detect → classify (error-taxonomy) → dry-run remediation → gate check → apply (or HALT) → validate → cross-skill if needed
```

### Safety posture

- **Credential masking (§0.1):** NEVER print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` value. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.
- **Dry-run first:** Every mutating action prints the exact `gcloud pubsub` command it *would* run, then requires an explicit apply step.
- **Idempotent:** Re-applying a config with identical params is a no-op if unchanged.
- **HALT on destructive:** Delete topic/subscription, purge messages, detach subscription → never auto-run.

## Detection Capabilities

| Anomaly | Signal | Severity | Auto-remediable |
|---------|--------|----------|:----------------:|
| Backlog growth | `num_undelivered_messages` > `{{user.backlog_threshold}}` | High | **Yes** (scale throughput / raise ack-deadline) |
| DLQ spike | `dead_letter_topic` delivery failures rising | High | **Yes** (replay/inspect) |
| Subscription stale | No `num_ack_messages` for > 30 min | Medium | **Yes** (flag for review) |
| Topic misconfig | Missing schema / retention mismatch | Low | **Yes** (patch config) |
| Push endpoint down | `push_request_count` 5xx rising | Critical | No (HALT — external) |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Pub/Sub API | `gcloud services list --enabled --filter="name:pubsub.googleapis.com"` | Enabled | `gcloud services enable pubsub.googleapis.com` |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Credentials file | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | Exists | HALT — set `GOOGLE_APPLICATION_CREDENTIALS=****` |
| Project | `gcloud config get-value project` | Set | HALT — set project |
| Monitoring API (alert trigger) | `gcloud services list --enabled --filter="name:monitoring.googleapis.com"` | Enabled | Delegate to `gcp-monitoring-ops` |

## Trigger Conditions

### T1 — Backlog growth

Detected as `num_undelivered_messages` above the configured threshold.

```bash
gcloud pubsub subscriptions describe "{{user.subscription}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '. | .topic' >/dev/null \
  && gcloud monitoring time-series list \
    --filter='metric.type="pubsub.googleapis.com/subscription/num_undelivered_messages" AND resource.labels.subscription_id="{{user.subscription}}"' \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -r '.[].points[-1].value.int64Value // 0' | head -1
```

### T2 — DLQ spike

Detected as the dead-letter topic receiving deliveries (poison messages accumulating).

```bash
gcloud pubsub topics describe "{{user.dlq_topic}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.name' >/dev/null \
  && gcloud monitoring time-series list \
    --filter='metric.type="pubsub.googleapis.com/topic/send_message_operation_count" AND resource.labels.topic_id="{{user.dlq_topic}}"' \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -r '.[].points[-1].value.int64Value // 0' | head -1
```

### T3 — Subscription stale

Detected as no `num_ack_messages` for > 30 min.

```bash
gcloud monitoring time-series list \
  --filter='metric.type="pubsub.googleapis.com/subscription/num_ack_messages" AND resource.labels.subscription_id="{{user.subscription}}"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e 'length == 0 or (.[].points | length == 0)' \
  && echo "STALE no ack activity"
```

## Self-Healing Actions

### Action A — Raise ack-deadline / throughput (T1)

> Idempotent, gated. Increases `ackDeadlineSeconds` (within bounds) so slow consumers stop redelivering. Never changes message content.

#### Dry-run

```bash
SUB="{{user.subscription}}"
echo "[DRY-RUN] Would set ackDeadlineSeconds={{user.new_ack_deadline}}:"
echo "  gcloud pubsub subscriptions update \"$SUB\" --ack-deadline={{user.new_ack_deadline}} \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single subscription, same skill)"
```

#### Idempotency

Re-applying the same deadline is a no-op; the describe check confirms current value before apply.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Within bounds | 10 ≤ new ≤ 600 | HALT — out of range |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
gcloud pubsub subscriptions update "{{user.subscription}}" \
  --ack-deadline="{{user.new_ack_deadline}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

#### Validate

```bash
gcloud pubsub subscriptions describe "{{user.subscription}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.ackDeadlineSeconds == ({{user.new_ack_deadline}})' \
  && echo "✅ Ack deadline updated"
```

### Action B — Inspect / flag DLQ (T2)

> Idempotent, gated. Lists poison messages in the DLQ for review; does NOT auto-replay (replay is a business decision → HALT). Only flags.

#### Dry-run

```bash
echo "[DRY-RUN] Would list DLQ messages for inspection (no mutation):"
echo "  gcloud pubsub topics subscriptions list \"{{user.dlq_topic}}\" --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\""
echo "[DRY-RUN] Blast radius tier: T1 (single topic, same skill)"
```

#### Idempotency

Listing is read-only; re-running is a safe no-op.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Inspect only | No replay/purge | HALT — business decision |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply (inspect only)

```bash
gcloud pubsub topics subscriptions list "{{user.dlq_topic}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
echo "✅ DLQ inspected — escalate replay decision to owner"
```

#### Validate

```bash
gcloud pubsub topics describe "{{user.dlq_topic}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.name' >/dev/null && echo "✅ DLQ reachable"
```

### Action C — Flag stale subscription (T3)

> Idempotent, gated. Adds a label marking the subscription stale for owner review; does NOT delete or detach.

#### Dry-run

```bash
SUB="{{user.subscription}}"
echo "[DRY-RUN] Would label subscription stale for review:"
echo "  gcloud pubsub subscriptions update \"$SUB\" --update-labels=aiops_stale=true \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single subscription, same skill)"
```

#### Idempotency

Re-applying the same label is a no-op; the describe check confirms current labels before apply.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Label only | No detach/delete | HALT — data-loss risk |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
gcloud pubsub subscriptions update "{{user.subscription}}" \
  --update-labels=aiops_stale=true \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

#### Validate

```bash
gcloud pubsub subscriptions describe "{{user.subscription}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.labels.aiops_stale == "true"' \
  && echo "✅ Stale label applied"
```

### HALT list (never auto-mutate)

| Action | Reason |
|--------|--------|
| Delete topic / subscription | Irreversible, data loss |
| Purge messages | Irreversible, data loss |
| Detach subscription | Data-loss risk |
| Auto-replay DLQ | Business decision, poison risk |
| Push endpoint fix | External dependency |

## Error Classification

Map every detected anomaly to [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) before choosing remediation. Recovery vocabulary (`HALT` / `RETRY` / `REMEDIATE` / `ESCALATE`) and `idempotent_safe` flag are defined there.

| Pub/Sub symptom | Taxonomy dimension | Canonical code | Recovery | Idempotent safe |
|-----------------|--------------------|----------------|----------|:----------------:|
| Backlog growth | Resource | `RESOURCE_EXHAUSTED` | `REMEDIATE` (tune) | true |
| DLQ spike | Dependency | `UNAVAILABLE` | `REMEDIATE` (inspect) | true |
| Subscription stale | Configuration | `INVALID_ARGUMENT` | `REMEDIATE` (flag) | true |
| Topic misconfig | Configuration | `INVALID_ARGUMENT` | `REMEDIATE` (patch) | true |
| Push endpoint down | Dependency | `UNAVAILABLE` | `HALT` / escalate | false |
| Transient API failure | Network | `UNAVAILABLE` | `RETRY` | true |
| Unknown internal | Unknown | `INTERNAL` | `RETRY` → `ESCALATE` | true |

## Blast Radius

Apply the tiers from [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) (HARD rule: only a pointer — never inline cross-domain descriptions):

- Ack-deadline / label / inspect → **T1** (same skill, single subscription/topic) → dry-run + gate.
- Cross-subscription throughput change → **T2** (affects multiple consumers) → note in output.
- Delete topic / purge / detach → **T4** → `HALT`, never auto-mutate.

> 详见 docs/cross-skill-blast-radius.md

## GCL Connection

This runbook is the detection→remediation leg of the cross-skill GCL loop. Wire it to the runner so every self-healing action is audited and fed back:

- **State capture:** `gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` imports `StateSnapshot` (from `self_correction_mechanism.py`) and invokes it per command to capture pre/post execution state. Use `StateSnapshot` to record the subscription/topic config before and after each Action A/B/C so the diff is provable.
- **Degradation gate:** the same script imports `DegradationDetector` and feeds it consecutive failure patterns; when `failure_count` crosses `threshold` it degrades to human-in-the-loop. Surface repeated `HALT`/failed gates to that detector rather than retrying blindly.
- **Feedback loop:** `gcp-gcl-runner-ops/trace_feedback.py` (`scan_traces`, `aggregate`, `build_report`) consumes persisted GCL traces to compute per-skill quality (`SkillQuality`) — feed it the trace from each self-healing run so Pub/Sub-specific failure patterns refine future auto-remediation thresholds.

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。

## See Also

- [error-taxonomy.md](../../../docs/error-taxonomy.md) — unified cross-skill error classification + recovery vocabulary
- [cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — blast radius tiers and gates
- [aiops-pubsub-anomaly.md](aiops-pubsub-anomaly.md) — sibling runbook (backlog/DLQ anomaly details)
- [gcp-pubsub-ops SKILL.md](../../SKILL.md) — base operations (topics, subscriptions, DLQ)
- [gcp-gcl-runner-ops](../../../gcp-gcl-runner-ops/SKILL.md) — Generator-Critic-Loop runner
