# Self-Healing Runbook — Google Cloud Armor (AIOps)

> Mainlined AIOps self-healing entry point for Cloud Armor. Closed-loop runbook: **detect → classify → dry-run preview → human review gate → idempotent apply → validate**, driven by `docs/error-taxonomy.md` recovery vocabulary and the `gcp-gcl-runner-ops` feedback loop.
>
> **Adaptive-protection auto-deploy detail** lives in [`adaptive-protection.md` §Attack Mitigation Self-Healing](adaptive-protection.md#attack-mitigation-self-healing-自愈闭环) — this runbook is the orchestration entry point; it does **not** re-narrate those commands. Read that section for the per-step gcloud/SDK invocations.

## Table of Contents

1. [Overview](#overview)
2. [Trigger Conditions](#trigger-conditions)
3. [Detection (Cloud Armor / SCC)](#detection-cloud-armor--scc)
4. [Classification (error-taxonomy)](#classification-error-taxonomy)
5. [Self-Healing Actions](#self-healing-actions)
6. [Human Review Gate](#human-review-gate)
7. [GCL Integration](#gcl-integration)
8. [Safety Constraints](#safety-constraints)
9. [See Also](#see-also)

## Overview

This runbook automates response to Cloud Armor security events without silent mutation. Every healing action is **dry-run-first**, **idempotent**, and **human-gated** at the appropriate blast-radius tier. It reuses the adaptive-protection auto-deploy flow as its core mitigation primitive and wraps it with unified classification + GCL feedback.

```
Trigger ──► Detect ──► Classify (error-taxonomy) ──► DRY-RUN preview
   │                                                  │
   │                                                  ▼
   └──────────────────────────────────────► Human review gate (T1/T2/T3)
                                                      │
                                                      ▼
                                            Idempotent APPLY ──► Validate + GCL feedback
```

> **Cross-domain blast radius (Armor → LB → GCE/VPC/CDN):** 详见 [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md). Never inline cross-domain descriptions here.

## Trigger Conditions

| Trigger | Signal | Typical error-taxonomy dimension |
|---------|--------|----------------------------------|
| DDoS / volumetric spike | `adaptive_protection_blocked_requests` surge; request count > 3× baseline | `UNAVAILABLE` (Network) / `RATE_LIMITED` (Rate Limit) |
| Adaptive-protection alert | `AUTO_DEPLOY_RULE_CREATED` log event | product-specific → route via `HALT`/`RETRY` |
| WAF false-positive surge | Legitimate traffic blocked; support tickets spike | `INVALID_ARGUMENT` (Config) / `FAILED_PRECONDITION` (Config) |
| Bot-management evasion | Bot score distribution collapses | product-specific anomaly |
| Policy config drift | Fingerprint mismatch vs Git/known baseline | `FAILED_PRECONDITION` (Config) |

Only the first three are auto-detectable from Cloud Armor / SCC signals. Bot-evasion and config-drift require the detector enrichment listed in [Detection](#detection-cloud-armor--scc).

## Detection (Cloud Armor / SCC)

All queries use `--format=json` + `jq` for machine parsing. Credentials are read from `GOOGLE_APPLICATION_CREDENTIALS` (masked — root `AGENTS.md` §0.1); never echo the file content.

```bash
# Verify creds exist ONLY (never print value)
test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists (credentials masked)"

# 1. Adaptive-protection auto-deploy event
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.method="GOOGLE_ARMOR_ADAPTIVE_PROTECTION_AUTO_DEPLOY_RULE_CREATED"' \
  --limit=20 --order=desc --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# 2. Blocked-request surge (volumetric / DDoS)
gcloud monitoring time-series list \
  --filter='metric.type="compute.googleapis.com/security_policy/adaptive_protection_blocked_requests"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json

# 3. WAF false-positive signal — legitimate traffic denied
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.enforcedSecurityPolicy.outcome="DENY" AND jsonPayload.httpRequest.userAgent=~"<known-good-agent>"' \
  --limit=50 --freshness=1h --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# 4. Security Command Center — high-severity Armor-related finding
gcloud scc findings list "{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='severity="HIGH" AND category="CLOUD_ARMOR"' \
  --format=json
```

> SCC detection requires `securitycenter.googleapis.com` enabled (see `adaptive-protection.md` §Enable Adaptive Protection). The auto-deploy event and blocked-request queries are the primary Armor-local signals; SCC is the cross-product corroboration layer.

## Classification (error-taxonomy)

Map the detected trigger to a recovery action from [`docs/error-taxonomy.md`](../../../docs/error-taxonomy.md) Recovery Action Vocabulary:

| Detected trigger | Recovery action | Idempotent safe |
|-------------------|-----------------|:----------------:|
| DDoS / volumetric spike | `REMEDIATE` (mirror auto-deploy rule as permanent deny) | true |
| Adaptive-protection alert | `RETRY` (re-read policy fingerprint, then preview) | true |
| WAF false-positive surge | `HALT` (do not auto-unblock; require human allowlist review) | true |
| Cross-skill / destructive (fail-closed, delete) | `HALT` (stop, request explicit confirmation) | false |

Recovery vocabulary (from error-taxonomy):
- `HALT` — stop, require human decision; do not auto-mutate.
- `RETRY` — retry with backoff; honor idempotency flag.
- `REMEDIATE` — auto-fix via known safe action (e.g. mirror auto-deploy rule).
- `ESCALATE` — escalate to support / ticket; no further auto-action.

> Per-skill error codes MUST map to a root-cause dimension in `docs/error-taxonomy.md`. Do not redefine codes here — the taxonomy is authoritative.

## Self-Healing Actions

Each action below follows the same shape: **dry-run preview (no mutation) → gate → idempotent apply**. The concrete gcloud/SDK invocations are in `adaptive-protection.md` §Attack Mitigation Self-Healing (Steps 3, 5) — this runbook references them instead of duplicating.

### Action A — Mirror auto-deploy rule as permanent hardening (`REMEDIATE`)

- **Detect:** auto-deploy rule created (Step 1 of adaptive-protection flow).
- **Classify:** `REMEDIATE` (volumetric / DDoS trigger).
- **Dry-run:** list current rules + show proposed priority/expression WITHOUT creating — `adaptive-protection.md` §Step 3.
- **Idempotency:** proposed priority derived deterministically from attack-signature hash → re-running converges to same rule (no duplicate creation).
- **Apply:** only after T2 human gate — `adaptive-protection.md` §Step 5.
- **Validate:** `adaptive-protection.md` §Step 6.

### Action B — Quarantine WAF false-positive (`HALT`)

- **Detect:** legitimate traffic denied surge (Detection #3).
- **Classify:** `HALT` — never auto-allowlist; auto-unblock risks opening an attack vector.
- **Dry-run:** show the candidate allowlist expression for human review (no apply).
- **Idempotency:** allowlist entry keyed by source signature → re-running is a no-op.
- **Apply:** only after explicit human confirmation with resource identifier.
- **Validate:** confirm false-positive rate drops; monitor blocked-request metric.

### Action C — Adaptive-protection config re-tune (`RETRY` / `REMEDIATE`)

- **Detect:** false-positive or missed-attack trend (Tuning Process in adaptive-protection.md).
- **Classify:** `RETRY` (re-read fingerprint) then `REMEDIATE` (adjust thresholds).
- **Dry-run:** `gcloud compute security-policies describe ... --format="yaml(adaptiveProtectionConfig)"` to preview current thresholds.
- **Idempotency:** thresholds are set-state, not additive → converged on repeat.
- **Apply:** after T2 gate; see adaptive-protection.md §Threshold Tuning for concrete commands.
- **Validate:** monitor auto-deploy event rate over 24h.

> T3 actions (cross-skill fail-closed / policy delete) are **HALT** and MUST NOT auto-apply — ever. Rollback for Action A is deleting the hardened rule by its deterministic priority (idempotent).

## Human Review Gate

| Blast-radius tier | Gate | Source of truth |
|-------------------|------|-----------------|
| T1 (single rule, same priority) | Dry-run log only; auto-approve after preview | `adaptive-protection.md` §Step 4 |
| T2 (policy-wide, e.g. enable auto-deploy / re-tune) | **Human gate** — present preview, await confirm | `adaptive-protection.md` §Step 4 |
| T3 (cross-skill: fail-closed / delete) | **HALT** — explicit resource-identifier confirmation required | `adaptive-protection.md` §Step 4 |

Destructive or cross-skill actions are marked **HALT** and MUST NOT auto-apply. The only unattended step is auto-expired auto-deploy rule retirement (a no-op when already expired).

## GCL Integration

This runbook feeds the Generator-Critic-Loop runner for audit + feedback:

- **Runner:** [`gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py`](../../../gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py) — executes the self-heal as a GCL iteration (Generator = apply action, Critic = verify idempotency + safety gate). Persist the JSON trace to `./audit-results/gcl-trace-*.json`.
- **Feedback:** [`gcp-gcl-runner-ops/trace_feedback.py`](../../../gcp-gcl-runner-ops/trace_feedback.py) — returns each self-heal outcome (trigger, action, tier, gate result, idempotency verified) into the GCL scoring + knowledge base, closing the detect → heal → feedback loop referenced by `docs/cross-skill-blast-radius.md` §与其他 AIOps 资产的关系.

> The recovery action emitted (`HALT` / `RETRY` / `REMEDIATE` / `ESCALATE`) is the classification handed to the GCL Critic so cross-skill aggregation in `docs/error-taxonomy.md` stays consistent.

## Safety Constraints

- **Credential masking (root `AGENTS.md` §0.1):** Never log `GOOGLE_APPLICATION_CREDENTIALS` or SA key content; verify existence only (`test -f ... && echo "✅ SA exists"`).
- **No silent apply:** T2/T3 require human gate; auto-deploy rule retirement is the only unattended step (no-op when expired).
- **Idempotency verified:** every apply action converges to target state; re-runs are no-ops.
- **Blast radius:** compute cross-skill impact before any preview — 详见 [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md).
- **Unified taxonomy:** all error codes resolve to `docs/error-taxonomy.md` root-cause dimensions.

## See Also

- [Adaptive Protection (auto-deploy self-healing detail)](adaptive-protection.md)
- [Advanced WAF Rules](advanced-waf-rules.md)
- [Bot Management](bot-management.md)
- [Unified Error Taxonomy](../../../docs/error-taxonomy.md)
- [Cross-Skill Blast Radius](../../../docs/cross-skill-blast-radius.md)
- [GCL Runner](../../../gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py)
- [GCL Trace Feedback](../../../gcp-gcl-runner-ops/trace_feedback.py)
