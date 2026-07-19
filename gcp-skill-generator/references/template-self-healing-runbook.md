<!--
============================================================================
INSTANTIATION GUIDE — template-self-healing-runbook.md
============================================================================
This is a STANDALONE copy-paste template. To use it for a new product skill:

1. Copy this file to: gcp-<product>-ops/references/advanced/self-healing-runbook.md
2. Replace every {{...}} placeholder:
   - {{SKILL_NAME}}   → e.g. gcp-logging-ops
   - {{PRODUCT}}      → e.g. Cloud Logging
   - {{user.*}}       → operator-supplied runtime values (ask once)
   - {{env.*}}        → never ask; read from environment
3. Fill the product-specific Detection Capabilities / Trigger Conditions / Self-Healing
   Actions tables with real anomalies and gcloud commands for {{PRODUCT}}.
4. Keep the Safety posture, HALT list, Error Classification, Blast Radius, GCL Connection
   sections structurally intact — only swap product names and links.
5. Do NOT print credentials (see §0.1). Verify existence only.

Model: gcp-logging-ops/references/advanced/self-healing-runbook.md
============================================================================
-->

# AIOps Self-Healing Runbook — {{PRODUCT}}

> Agent runbook for closed-loop self-healing of {{PRODUCT}} failures. Every remediation action is **dry-run first**, **idempotent**, and **gated**; destructive actions are marked `HALT`.

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

{{PRODUCT}} can degrade in ways that are invisible until an audit or dashboard goes dark. This runbook closes the loop:

```
trigger → detect → classify (error-taxonomy) → dry-run remediation → gate check → apply (or HALT) → validate → cross-skill if needed
```

### Safety posture

- **Credential masking (§0.1):** NEVER print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` value. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.
- **Dry-run first:** Every mutating action prints the exact `gcloud` command it *would* run, then requires an explicit apply step.
- **Idempotent:** Re-applying an update with identical params is a no-op if unchanged.
- **HALT on destructive:** Deleting resources, modifying reserved/system objects, unlocking immutable state, cross-project mutations → never auto-run.

## Detection Capabilities

| Anomaly | Signal | Severity | Auto-remediable |
|---------|--------|----------|:----------------:|
| {{anomaly_1}} | {{signal_1}} | {{sev_1}} | {{auto_1}} |
| {{anomaly_2}} | {{signal_2}} | {{sev_2}} | {{auto_2}} |
| {{anomaly_3}} | {{signal_3}} | {{sev_3}} | {{auto_3}} |
| {{anomaly_4}} | {{signal_4}} | {{sev_4}} | {{auto_4}} |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| {{PRODUCT}} API | `gcloud services list --enabled --filter="name:{{api_name}}"` | Enabled | `gcloud services enable {{api_name}}` |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Credentials file | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | Exists | HALT — set `GOOGLE_APPLICATION_CREDENTIALS=****` |
| Project | `gcloud config get-value project` | Set | HALT — set project |

## Trigger Conditions

### T1 — {{trigger_1}}

{{trigger_1_description}}

```bash
# Detect {{trigger_1}}
gcloud {{product_cli_path}} "{{detect_query}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Remediation:** {{remediation_1}}.

### T2 — {{trigger_2}}

{{trigger_2_description}}

```bash
# Detect {{trigger_2}}
gcloud {{product_cli_path}} "{{detect_query_2}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Remediation:** {{remediation_2}}.

## Self-Healing Actions

### Action A — {{action_a_name}} (T1)

> Idempotent, gated. Only for **unlocked** / non-reserved resources. Never touches reserved/system objects (immutable → `HALT`).

#### Dry-run

```bash
RESOURCE="{{user.resource_name}}"; REGION="{{user.region}}"
echo "[DRY-RUN] Would apply remediation:"
echo "  gcloud {{product_cli_path}} update \"$RESOURCE\" \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single resource, same skill)"
```

#### Idempotency

Re-applying with the same value is a no-op; repeats are safe.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Resource unlocked | `describe` shows not locked | HALT — locked resources are immutable |
| Not reserved | `name` not a reserved/system object | HALT — protected resource |
| Increase-only / safe direction | new value ≥ current | HALT — never regress |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
gcloud {{product_cli_path}} update "$RESOURCE" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

#### Validate

```bash
gcloud {{product_cli_path}} describe "$RESOURCE" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '{{validation_jq}}' && echo "✅ Remediation applied"
```

### Action B — {{action_b_name}} (T2)

> Idempotent, gated. Primary auto-remediable path.

#### Dry-run

```bash
TARGET="{{user.target_name}}"
echo "[DRY-RUN] Would re-create/restore desired state:"
echo "  gcloud {{product_cli_path}} create \"$TARGET\" \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T2 (writes to resource owned by another skill)"
```

#### Idempotency

Re-creating with identical params re-applies the desired config; unchanged resources are no-ops.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Idempotent | Params match desired state | HALT if name collides with unrelated resource |
| Destination exists | Destination reachable | HALT — delegate to destination skill |
| Blast radius | Tier ≤ T2 | HALT if T3/T4 (cross-project / system) |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply + validate

```bash
gcloud {{product_cli_path}} create "$TARGET" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

### HALT list (never auto-mutate)

| Action | Reason |
|--------|--------|
| Delete resource | Irreversible, data loss |
| Modify reserved/system object | Protected, org-critical |
| Shorten / unlock immutable state | Compliance + immutability violation |
| Cross-project / org mutation | Out of scope, blast radius T3/T4 |

## Error Classification

Map every detected anomaly to [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) before choosing remediation. Recovery vocabulary (`HALT` / `RETRY` / `REMEDIATE` / `ESCALATE`) and `idempotent_safe` flag are defined there.

| {{PRODUCT}} symptom | Taxonomy dimension | Canonical code | Recovery | Idempotent safe |
|---------------------|--------------------|----------------|----------|:----------------:|
| {{symptom_1}} | {{dim_1}} | {{code_1}} | {{rec_1}} | {{idemp_1}} |
| {{symptom_2}} | {{dim_2}} | {{code_2}} | {{rec_2}} | {{idemp_2}} |
| {{symptom_3}} | {{dim_3}} | {{code_3}} | {{rec_3}} | {{idemp_3}} |

## Blast Radius

Apply the tiers from [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) (HARD rule: only a pointer — never inline cross-domain descriptions):

- {{action_a_name}} → **T1** (same skill, single resource) → dry-run + gate.
- {{action_b_name}} → **T2** (writes to resource owned by another skill) → dry-run + cross-skill note, confirm destination exists.
- Cross-project mutation → **T3** → `HALT`.
- Reserved/system object → **T4** → `HALT`, never auto-mutate.

> 详见 docs/cross-skill-blast-radius.md

## GCL Connection

This runbook is the detection→remediation leg of the cross-skill GCL loop. Wire it to the runner so every self-healing action is audited and fed back:

- **State capture:** `gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` imports `StateSnapshot` (from `self_correction_mechanism.py`) and invokes it per command to capture pre/post execution state. Use `StateSnapshot` to record the resource state before and after each Action A/B so the diff is provable.
- **Degradation gate:** the same script imports `DegradationDetector` and feeds it consecutive failure patterns; when `failure_count` crosses `threshold` it degrades to human-in-the-loop. Surface repeated `HALT`/failed gates to that detector rather than retrying blindly.
- **Feedback loop:** `gcp-gcl-runner-ops/trace_feedback.py` (`scan_traces`, `aggregate`, `build_report`) consumes persisted GCL traces to compute per-skill quality (`SkillQuality`) — feed it the trace from each self-healing run so {{PRODUCT}}-specific failure patterns refine future auto-remediation thresholds.

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。

## See Also

- [error-taxonomy.md](../../../docs/error-taxonomy.md) — unified cross-skill error classification + recovery vocabulary
- [cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — blast radius tiers and gates
- [{{SKILL_NAME}} SKILL.md](../../SKILL.md) — base operations
- [gcp-gcl-runner-ops](../../../gcp-gcl-runner-ops/SKILL.md) — Generator-Critic-Loop runner
