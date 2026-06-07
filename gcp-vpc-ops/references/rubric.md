# Rubric — Google Cloud VPC (GCL)

> **GCL Classification:** `required` | `max_iter`: 2
> **Rubric version:** 1.0.0
> **Last updated:** 2026-06-07

## 5 Core Dimensions

| Dimension | Weight | Meaning | Score Criteria |
|-----------|--------|---------|----------------|
| **Correctness** | 3 | Resource ID/state/config matches request | 1=partial, 2=mostly, 3=exact match |
| **Safety** | 5 | Destructive ops confirmed or protected | 0=fail, 1=warn, 2=confirmed, 3=double-confirmed |
| **Idempotency** | 2 | Repeat call has no side effects | 0=destructive repeat, 1=warns, 2=handled |
| **Traceability** | 2 | Output is auditable (cmd, params, result) | 0=none, 1=partial, 2=full trace |
| **Spec Compliance** | 2 | Complies with core-concepts.md constraints | 0=violates, 1=partial, 2=full |

## 3 GCP-Specific Extensions

| Extension | Meaning | Score |
|-----------|---------|-------|
| **Firewall Fidelity** | Firewall rules correctly reference network, direction, allowed/denied, sourceRanges, targetTags | 0-2 |
| **Subnet CIDR Validation** | Subnet CIDR is valid, non-overlapping, within RFC 1918 | 0-2 |
| **Deletion Dependency** | Network deletion checks all dependent resources first | 0-3 |

## Per-Operation Safety Sub-Rules (≥3 per destructive op)

### Delete Network
| Rule | Severity | Check |
|------|----------|-------|
| Confirm network name matches exactly | required | User types exact name |
| Check no running VMs attached | required | `gcloud compute instances list --filter` returns empty |
| Check no subnets exist | required | `gcloud compute networks subnets list` returns empty |
| Check no firewall rules exist | required | `gcloud compute firewall-rules list --filter` returns empty |
| Check no active peerings | required | `gcloud compute networks peerings list` returns empty |

### Delete Subnet
| Rule | Severity | Check |
|------|----------|-------|
| Confirm subnet name + region | required | User types exact name |
| Check no VMs using subnet | required | `gcloud compute instances list` shows none with this subnet |
| Warn about secondary IP ranges | recommended | Check if GKE secondary ranges exist |

### Delete Firewall Rule
| Rule | Severity | Check |
|------|----------|-------|
| Confirm rule name matches exactly | required | User types exact name |
| Warn impact: this rule controls {direction} traffic | required | Display rule direction |
| Suggest review of remaining rules | recommended | `gcloud compute firewall-rules list --filter="network:{{user.network_name}}"` |

### Modify Firewall Rule (broadening access)
| Rule | Severity | Check |
|------|----------|-------|
| Show diff of changes (before/after) | required | Display current rule vs proposed changes |
| Confirm user intends to broaden access | required | User confirms the change |
| Flag security risk | required | Display warning about broader CIDR or protocol |

## Detection Patterns (Data-Plane Skills)

| Pattern | Detection | Example |
|---------|-----------|---------|
| CIDR overlap detection | Compare new subnet CIDR with existing subnets | `10.0.1.0/24` vs existing `10.0.0.0/16` |
| Firewall rule priority conflict | Check for rules with overlapping source+dest+protocol | Two rules port 80, different priorities |
| Routing loop detection | Check route next-hops for circular references | Route A → Route B → Route A |
| NAT port exhaustion | Check `nat_connections_used / nat_allocated_ports` ratio | > 80% warning |
| VPN tunnel flapping | Check tunnel status transitions | ESTABLISHED → null → ESTABLISHED within 5min |

## Worked Examples

### Example 1: PASS — Correct subnet creation
- **Request:** Create subnet `web-subnet` in `us-central1` with CIDR `10.0.1.0/24` on `my-vpc`
- **Generator output:** `gcloud compute networks subnets create web-subnet --network=my-vpc --region=us-central1 --range=10.0.1.0/24`
- **Critic verdict:** PASS (Correctness=3, Safety=3, Idempotency=1, Traceability=2, Spec=2)

### Example 2: SAFETY_FAIL — Network deletion without dependency check
- **Request:** Delete network `my-vpc`
- **Generator output:** `gcloud compute networks delete my-vpc --quiet`
- **Critic verdict:** SAFETY_FAIL (Safety=0) — no pre-flight check for dependent resources
- **Outcome:** ABORT — no partial result returned

### Example 3: FAIL — CIDR overlap
- **Request:** Create subnet `data-subnet` in `us-central1` with `10.0.0.0/24`
- **Generator output:** Creates without checking existing subnets
- **Critic verdict:** FAIL (Correctness=1, Spec=0) — CIDR `10.0.0.0/24` overlaps with existing `10.0.0.0/20`

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial rubric for gcp-vpc-ops (required) |