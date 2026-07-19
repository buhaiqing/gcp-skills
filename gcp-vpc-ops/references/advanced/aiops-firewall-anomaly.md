# AIOps Firewall Anomaly Detection — Google Cloud VPC

> Detect unexpected firewall rule changes (allow-all, broad `0.0.0.0/0` on sensitive ports, deleted rules, drift vs desired state) and gate remediation. Every action is **dry-run first**, **idempotent**, and **gated**; destructive actions are marked `HALT`.

Credential masking per AGENTS.md §0.1: never print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` path value; verify existence only (`test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`).

## Table of Contents

1. [Overview](#overview)
2. [Detection Capabilities](#detection-capabilities)
3. [Prerequisites](#prerequisites)
4. [Detection Script](#detection-script)
5. [Remediation: Dry-run → Gate → Apply → Validate](#remediation-dry-run--gate--apply--validate)
6. [HALT List](#halt-list)
7. [Error Classification](#error-classification)
8. [Blast Radius](#blast-radius)
9. [See Also](#see-also)

## Overview

Firewall rules are the perimeter of a VPC. A single allow-all rule or a broad `0.0.0.0/0` on port 22/3389 can expose the entire fleet. This runbook closes the loop:

```
trigger → detect (gcloud + jq) → classify (error-taxonomy) → dry-run remediation → gate check → apply (or HALT) → validate → cross-skill if needed
```

### Safety posture

- **Dry-run first:** Every mutating action prints the exact `gcloud` command it *would* run, then requires an explicit apply step.
- **Idempotent:** Re-applying a rule with identical params is a no-op if unchanged.
- **HALT on destructive:** Deleting firewall rules, reverting to a prior config that removes unknown rules → never auto-run; gate for human review.

## Detection Capabilities

| Anomaly | Signal | Severity | Auto-remediable |
|---------|--------|----------|:----------------:|
| Allow-all rule | `allowed[].IPProtocol=all` with `sourceRanges` containing `0.0.0.0/0` | Critical | No (HALT) |
| Broad CIDR on sensitive port | `0.0.0.0/0` on tcp:22 / 3389 / 443 / 80 | High | No (HALT) |
| Empty `denied` + broad allow | allow rule with no `denied` and wide source | Medium | No (HALT) |
| Deleted rule | rule present in desired state, absent in live | High | No (HALT) |
| Rule drift | live config ≠ desired config (priority/source/ports) | Medium | **Yes** (restore, gated) |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Compute API | `gcloud services list --enabled --filter="config:compute.googleapis.com"` | enabled | `gcloud services enable compute.googleapis.com` |
| Credentials | `gcloud auth print-access-token --quiet` | Token returned | HALT — authenticate |
| Credentials file | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | Exists | HALT — set `GOOGLE_APPLICATION_CREDENTIALS=****` |
| Project | `gcloud config get-value project` | Set | HALT — set project |

## Detection Script

Export live rules once, then flag risky patterns with `jq`.

```bash
# Snapshot live firewall rules (no mutation)
gcloud compute firewall-rules list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  > /tmp/fw_rules_$(date +%s).json
FW=/tmp/fw_rules_$(ls -t /tmp/fw_rules_*.json | head -1 | xargs basename)

# 1. Allow-all from anywhere
jq -r '.[] | select(.allowed[].IPProtocol=="all") | select(.sourceRanges[]?=="0.0.0.0/0") |
  "ALLOW-ALL \(.name) src=\(.sourceRanges)"' "$FW"

# 2. Broad CIDR on sensitive ports (22/3389/443/80)
jq -r '.[] | .allowed[]? | select(.ports!=null) |
  select((.ports[]?|tostring)|test("22|3389|443|80")) |
  select(.IPProtocol=="tcp") |
  . as $a | input_filename as $f |
  "SENSITIVE-PORT \(.name) proto=tcp ports=\(.ports) src=\(.sourceRanges)"' "$FW" 2>/dev/null || \
jq -r '.[] | .name as $n | .sourceRanges[]? as $s | .allowed[]? |
  select(.IPProtocol=="tcp" and (.ports[]?|tostring|test("22|3389|443|80"))) |
  select($s=="0.0.0.0/0") |
  "SENSITIVE-PORT \($n) proto=tcp ports=\(.ports) src=\($s)"' "$FW"

# 3. Allow rule with no denied block and wide source (potential over-permissive)
jq -r '.[] | select(.denied==null) | select(.sourceRanges[]?=="0.0.0.0/0") |
  "NO-DENY \(.name) src=\(.sourceRanges)"' "$FW"

# 4. Drift vs desired state (operator-supplied baseline export)
#    jq --argjson want "$(cat desired_firewall.json)" ... diff by name/priority/sourceRanges/allowed
```

> The port-scan `jq` above is portable; the first variant is a best-effort one-pass filter, the `||` fallback is the robust two-stage form. Use whichever your `jq` version supports.

## Remediation: Dry-run → Gate → Apply → Validate

### Drift restore (rule config changed unexpectedly)

> Idempotent, gated. Restore a rule to its known-good config from a prior `describe` / config export. Never deletes or creates rules — only `update` to match desired state.

#### Dry-run

```bash
RULE="{{user.firewall_rule_name}}"
echo "[DRY-RUN] Would restore rule to known-good config:"
echo "  gcloud compute firewall-rules update \"$RULE\" \\"
echo "    --source-ranges=\"{{user.known_good_source_ranges}}\" \\"
echo "    --allow=\"{{user.known_good_allow}}\" \\"
echo "    --priority=\"{{user.known_good_priority}}\" \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single rule, same skill)"
```

#### Idempotency

Re-applying identical `--source-ranges`/`--allow`/`--priority` is a no-op; unchanged rules are not mutated.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Restore-only | `update` matches desired state, no delete/create | HALT if action would delete a rule |
| Not allow-all | restored config does not introduce `0.0.0.0/0`+`all` | HALT — would widen exposure |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
gcloud compute firewall-rules update "{{user.firewall_rule_name}}" \
  --source-ranges="{{user.known_good_source_ranges}}" \
  --allow="{{user.known_good_allow}}" \
  --priority="{{user.known_good_priority}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

#### Validate

```bash
gcloud compute firewall-rules describe "{{user.firewall_rule_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.sourceRanges == ($good | split(","))' --arg good "{{user.known_good_source_ranges}}" \
  && echo "✅ Firewall rule restored"
```

### Deleted-rule recovery (rule missing vs desired state)

> **HALT** — re-creating a deleted rule changes exposure and may conflict with intent. Propose only; gate for human review.

```bash
# DRY-RUN: propose re-create from known-good export (no execution)
gcloud compute firewall-rules describe "{{user.firewall_rule_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json 2>&1 | grep -q notFound \
  && echo "[DRY-RUN] Rule '{{user.firewall_rule_name}}' absent. Propose re-create from export:" \
  && echo "  gcloud compute firewall-rules create \"{{user.firewall_rule_name}}\" --format=json (params from known-good export)"
echo "[HALT] Re-creation requires human review — do not auto-create."
```

## HALT List

| Action | Reason |
|--------|--------|
| Delete a firewall rule | Irreversible; may open/close access to resources — gate for human review |
| Auto-create a deleted rule | Changes exposure; conflicts with operator intent |
| Widen to allow-all | `0.0.0.0/0` + `IPProtocol=all` is a critical exposure — never auto-apply |
| Revert config that removes unknown rules | May drop legitimately-added rules |

## Error Classification

Map every detected anomaly to [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) before choosing remediation. Recovery vocabulary (`HALT` / `RETRY` / `REMEDIATE` / `ESCALATE`) and `idempotent_safe` flag are defined there.

| Firewall symptom | Taxonomy dimension | Canonical code | Recovery | Idempotent safe |
|------------------|--------------------|----------------|----------|:----------------:|
| Allow-all from `0.0.0.0/0` | Security/Config | `FAILED_PRECONDITION` (over-permissive) | `HALT` | false |
| Broad CIDR on 22/3389 | Security/Config | `FAILED_PRECONDITION` | `HALT` | false |
| Rule deleted vs desired | Config | `NOT_FOUND` (drift) | `HALT` | false |
| Rule drift (params changed) | Config | `INVALID_ARGUMENT` (drift) | `REMEDIATE` (restore) | true |
| Transient read failure | Network | `UNAVAILABLE` | `RETRY` | true |

## Blast Radius

Apply the tiers from [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) (HARD rule: only a pointer — never inline cross-domain descriptions):

- Firewall rule drift restore → **T1** (same skill, single rule) → dry-run + gate.
- Deleted-rule re-create → **T1** but `HALT` (changes exposure) → human review.
- Firewall change affecting GKE/GCE connectivity → see blast-radius 链路 1 (VPC → GKE/GCE) → cross-skill note.

> 详见 docs/cross-skill-blast-radius.md

## See Also

- [error-taxonomy.md](../../../docs/error-taxonomy.md) — unified cross-skill error classification + recovery vocabulary
- [cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — blast radius tiers and gates
- [aiops-network-anomaly.md](aiops-network-anomaly.md) — sibling runbook (flow-log traffic anomalies)
- [gcp-vpc-ops SKILL.md](../../SKILL.md) — base operations (firewall rules CRUD)
- [gcp-gcl-runner-ops](../../../gcp-gcl-runner-ops/SKILL.md) — Generator-Critic-Loop runner
