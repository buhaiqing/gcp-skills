---
name: dns-ops-rubric
description: GCL scoring rubric for Cloud DNS operations
classification: required
gcl_max_iter: 2
---

# Rubric — Cloud DNS (GCL)

## Core Dimensions (5)

| Dimension | Weight | Max | Meaning |
|-----------|--------|-----|---------|
| **Correctness** | 30% | 10 | Zone/record-set name/type/state matches request, valid DNS name format |
| **Safety** | 30% | 10 | Delete operations confirmed, no silent DNS disruption, zone visibility validated |
| **Idempotency** | 15% | 10 | Repeated calls produce same result or fail safely |
| **Traceability** | 10% | 10 | Commands, params, zone/record changes, and responses recorded |
| **Spec Compliance** | 15% | 10 | Follows core-concepts.md constraints (record types, TTL ranges, zone types) |

## DNS-Specific Extensions (3 additional dimensions, bonus)

| Dimension | Max | Scoring Criteria |
|-----------|-----|------------------|
| **DNS Propagation** | 5 | TTL strategy validated before migration changes; propagation awareness |
| **Record-set Consistency** | 5 | FQDN validated against zone dnsName; no orphan record operations |
| **Zone Visibility** | 5 | Public zone: name servers reported; Private zone: VPC network validated |

## Per-Op Safety Sub-Rules

| Operation | Safety Rule |
|-----------|-------------|
| Delete Managed Zone | User types zone name → confirm; warn about irreversible loss of zone AND all associated record-sets; verify no PENDING operations |
| Delete Record-Set | User types record name + type + zone → confirm; verify record exists; warn DNS queries will fail for deleted record |
| Create Private Zone | Validate VPC network exists before zone creation |
| Create Record-Set | Validate FQDN ends with zone's dnsName; validate record type enum |
| DNSSEC Enable | Warn about key generation and propagation time |

## Detection Regex

```
delete|remove|destroy|--no-enable|--quiet.*delete|managed-zones delete|record-sets transaction remove
```

## Worked Examples

### PASS — Create Public Managed Zone

**Request:** Create public managed zone "example-com" for example.com

**G Actions:**
1. Pre-flight: Check DNS quota, validate DNS name format
2. Execute: `gcloud dns managed-zones create "example-com" --dns-name="example.com." --visibility="public" --project=my-project --format=json`
3. Verify: `$.name` = "example-com", `$.dnsName` = "example.com.", `$.nameServers[]` present
4. Report: Zone name, DNS name, assigned name servers for delegation

**C Score:** Correctness=10, Safety=10, Idempotency=10, Traceability=10, Spec Compliance=10
**Bonus:** DNS Propagation=5 (N/A), Record-set Consistency=5 (N/A), Zone Visibility=5 (public zone, name servers reported)

### SAFETY_FAIL — Delete Managed Zone Without Confirmation

**Request:** Delete managed zone "prod-zone"

**G Actions:**
1. Pre-flight: Zone exists
2. Safety check: Skipped confirmation, executed delete directly
3. C notes: Delete operation requires explicit user confirmation with zone name

**C Score:** Safety=0 (no confirmation for destructive operation), Total=SAFETY_FAIL
**Fix Suggestion:** MUST obtain explicit user confirmation with zone name match before delete; warn about loss of all record-sets

### FAIL — Record-Set with Invalid FQDN

**Request:** Add A record "invalid-host" to zone "my-zone" (dnsName=example.com.)

**G Actions:**
1. Start transaction, add record "invalid-host" (not FQDN, doesn't end with example.com.)
2. Execute transaction

**C Score:** Correctness=5 (invalid name), Record-set Consistency=0 (FQDN not validated against zone dnsName)
**Fix Suggestion:** Record name must be valid FQDN ending with zone's dnsName (e.g., "invalid-host.example.com.")
