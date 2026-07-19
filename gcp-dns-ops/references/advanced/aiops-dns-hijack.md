# AIOps DNS Hijack Detection — Google Cloud DNS

> Detect unexpected NS record changes, new wildcard records, suspicious CNAME targets, and zone-transfer anomalies; gate remediation. Every action is **dry-run first**, **idempotent**, and **gated**; destructive actions are marked `HALT`.

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

DNS is a prime hijack target: an attacker who changes NS records or injects a wildcard `*` record can redirect all traffic for a domain. This runbook closes the loop:

```
trigger → detect (gcloud + jq) → classify (error-taxonomy) → dry-run remediation → gate check → apply (or HALT) → validate → cross-skill if needed
```

### Safety posture

- **Dry-run first:** Every mutating action prints the exact `gcloud` command it *would* run, then requires an explicit apply step.
- **Idempotent:** Re-applying a record-set with identical params is a no-op if unchanged.
- **HALT on destructive:** Deleting record-sets, reverting to a prior export that removes unknown records → never auto-run; gate for human review.

## Detection Capabilities

| Anomaly | Signal | Severity | Auto-remediable |
|---------|--------|----------|:----------------:|
| NS record change | `NS` rrdatas point to unknown registrar/nameserver | Critical | No (HALT) |
| New wildcard `*` record | record name `*.example.com` newly present | High | No (HALT) |
| Suspicious CNAME target | CNAME points to unknown/external domain | High | No (HALT) |
| Unexpected A/AAAA change | live IP ≠ known-good baseline | Medium | No (HALT) |
| Zone-transfer anomaly | unexpected `AXFR`/transfer config or SOA serial jump | Medium | No (HALT) |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| DNS API | `gcloud services list --enabled --filter="config:dns.googleapis.com"` | enabled | `gcloud services enable dns.googleapis.com` |
| Credentials | `gcloud auth print-access-token --quiet` | Token returned | HALT — authenticate |
| Credentials file | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | Exists | HALT — set `GOOGLE_APPLICATION_CREDENTIALS=****` |
| Project | `gcloud config get-value project` | Set | HALT — set project |

## Detection Script

Export live record-sets once, then flag anomalies with `jq`.

```bash
# Snapshot live record-sets (no mutation)
ZONE="{{user.zone_name}}"
gcloud dns record-sets list --zone="$ZONE" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  > /tmp/rr_${ZONE}_$(date +%s).json
RR=/tmp/rr_${ZONE}_$(ls -t /tmp/rr_${ZONE}_*.json | head -1 | xargs basename)

# 1. NS records pointing to unknown nameservers (operator-supplied allowlist)
KNOWN_NS='("ns1.example-dns.com" "ns2.example-dns.com")'
jq -r --argjson known "$KNOWN_NS" '.[] | select(.type=="NS") |
  .rrdatas[]? | select(. as $n | $known | index($n) | not) |
  "NS-UNKNOWN \(.name) -> \($n)"' "$RR"

# 2. New wildcard records
jq -r '.[] | select(.name | test("^\\*\\.")) |
  "WILDCARD \(.name) type=\(.type) data=\(.rrdatas)"' "$RR"

# 3. Suspicious CNAME targets (operator-supplied allowlist of trusted domains)
KNOWN_CNAME='("internal.example.com" "lb.example.com")'
jq -r --argjson known "$KNOWN_CNAME" '.[] | select(.type=="CNAME") |
  .rrdatas[]? | select(. as $c | $known | index($c) | not) |
  "CNAME-SUSPECT \(.name) -> \($c)"' "$RR"

# 4. Unexpected A/AAAA change vs known-good baseline
#    jq --argjson good "$(cat known_good_a.json)" ... diff rrdatas by name
```

> Replace `example-dns.com` / `example.com` allowlists with the operator's real trusted nameservers and domains. The `jq` filters are portable across versions.

## Remediation: Dry-run → Gate → Apply → Validate

### Restore from known-good export (record-set drift)

> Idempotent, gated. Restore a record-set to its known-good data via a transaction. Never deletes or creates records outside the transaction diff — only corrects the flagged record.

#### Dry-run

```bash
ZONE="{{user.zone_name}}"
echo "[DRY-RUN] Would restore record-set to known-good data (transaction):"
echo "  gcloud dns record-sets transaction start --zone=\"$ZONE\""
echo "  gcloud dns record-sets transaction remove \"{{user.record_name}}\" \\"
echo "    --type=\"{{user.record_type}}\" --ttl=\"{{user.ttl}}\" --rrdatas=\"{{user.bad_data}}\" --zone=\"$ZONE\" --dry-run"
echo "  gcloud dns record-sets transaction add \"{{user.record_name}}\" \\"
echo "    --type=\"{{user.record_type}}\" --ttl=\"{{user.ttl}}\" --rrdatas=\"{{user.good_data}}\" --zone=\"$ZONE\" --dry-run"
echo "  gcloud dns record-sets transaction execute --zone=\"$ZONE\" \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single zone, same skill)"
```

#### Idempotency

Re-applying identical `--rrdatas` is a no-op; unchanged records are not mutated.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Restore-only | transaction replaces flagged record with known-good | HALT if action would delete unrelated records |
| Not widening | restored data does not introduce wildcard/`0.0.0.0` | HALT — would widen exposure |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
ZONE="{{user.zone_name}}"
gcloud dns record-sets transaction start --zone="$ZONE"
gcloud dns record-sets transaction remove "{{user.record_name}}" \
  --type="{{user.record_type}}" --ttl="{{user.ttl}}" --rrdatas="{{user.bad_data}}" --zone="$ZONE"
gcloud dns record-sets transaction add "{{user.record_name}}" \
  --type="{{user.record_type}}" --ttl="{{user.ttl}}" --rrdatas="{{user.good_data}}" --zone="$ZONE"
gcloud dns record-sets transaction execute \
  --zone="$ZONE" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

#### Validate

```bash
gcloud dns record-sets describe "{{user.record_name}}" \
  --type="{{user.record_type}}" --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.rrdatas == ($good | split(" "))' --arg good "{{user.good_data}}" \
  && echo "✅ Record-set restored"
```

### NS / wildcard / CNAME hijack recovery

> **HALT** — changing NS or removing a wildcard record alters domain resolution and may break mail/TLS. Propose only; gate for human review.

```bash
# DRY-RUN: propose restore of NS delegation from known-good export (no execution)
echo "[DRY-RUN] Would restore NS delegation for zone '{{user.zone_name}}' from known-good export:"
echo "  gcloud dns record-sets transaction ... (NS rrdatas from known-good export)"
echo "[HALT] NS/CNAME/wildcard changes require human review — do not auto-apply."
```

## HALT List

| Action | Reason |
|--------|--------|
| Delete record-sets | Irreversible; may break domain resolution, mail, TLS — gate for human review |
| Auto-restore NS delegation | Changes domain delegation; conflicts with registrar intent |
| Remove wildcard `*` record | May drop legitimately-added catch-all routing |
| Revert export that removes unknown records | May drop legitimately-added records |

## Error Classification

Map every detected anomaly to [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) before choosing remediation. Recovery vocabulary (`HALT` / `RETRY` / `REMEDIATE` / `ESCALATE`) and `idempotent_safe` flag are defined there.

| DNS symptom | Taxonomy dimension | Canonical code | Recovery | Idempotent safe |
|-------------|--------------------|----------------|----------|:----------------:|
| NS record hijack | Security/Config | `FAILED_PRECONDITION` (delegation changed) | `HALT` | false |
| New wildcard `*` record | Security/Config | `FAILED_PRECONDITION` | `HALT` | false |
| Suspicious CNAME target | Security/Config | `FAILED_PRECONDITION` | `HALT` | false |
| A/AAAA drift vs baseline | Config | `INVALID_ARGUMENT` (drift) | `HALT` | false |
| Zone-transfer anomaly | Security/Config | `FAILED_PRECONDITION` | `HALT` | false |

## Blast Radius

Apply the tiers from [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) (HARD rule: only a pointer — never inline cross-domain descriptions):

- Record-set drift restore → **T1** (same skill, single zone) → dry-run + gate.
- NS/CNAME/wildcard change → **T1** but `HALT` (changes domain-wide resolution) → human review.
- DNS change affecting LB/VPC private zones → see blast-radius (DNS ↔ VPC/LB) → cross-skill note.

> 详见 docs/cross-skill-blast-radius.md

## See Also

- [error-taxonomy.md](../../../docs/error-taxonomy.md) — unified cross-skill error classification + recovery vocabulary
- [cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — blast radius tiers and gates
- [aiops-dns-anomaly.md](aiops-dns-anomaly.md) — sibling runbook (resolution/propagation/DNSSEC)
- [gcp-dns-ops SKILL.md](../../SKILL.md) — base operations (record-sets, zones)
- [gcp-gcl-runner-ops](../../../gcp-gcl-runner-ops/SKILL.md) — Generator-Critic-Loop runner
