# Unified Error Code Taxonomy (AIOps P0-2)

> **Purpose:** Single source of truth for cross-skill error classification. Enables aggregated error analytics and unified self-healing decisions across all `gcp-*-ops` skills.
> **Version:** 1.0.0
> **Last Updated:** 2026-07-19
> **Supersedes:** Per-skill ad-hoc error code tables (kept for reference, not authoritative).

---

## Scope & Principles

- Errors are classified by **root cause dimension**, not by product symptom. A `STORAGE_FULL` in Cloud SQL and a `RESOURCE_EXHAUSTED` in GKE both roll up to the **Resource State** dimension.
- This taxonomy is the **authoritative** classification layer. Per-skill tables remain valid for product-specific diagnosis but MUST map their codes to one of the dimensions below.
- The 6 base codes from `docs/diagnostic-logging-standard.md` (§Error Classification) are a **subset** of this taxonomy — no conflict, no redefinition.
- gRPC-style codes from `gcp-gcl-runner-ops/gcl_trace_schema.py` (`GCPErrorType`) are the canonical wire format and are mapped 1:1 where applicable.

### Recovery Action Vocabulary

| Action | Meaning | Agent Behavior |
|--------|---------|----------------|
| `HALT` | Stop, require human decision | Do not auto-mutate; surface to human |
| `RETRY` | Retry with backoff | Safe to retry; honor idempotency flag |
| `REMEDIATE` | Auto-fix via known safe action | Apply fix (e.g. grant role, resize) |
| `ESCALATE` | Escalate to support / ticket | File case; no further auto-action |

### Idempotency Flag

`idempotent_safe` = the recovery action can be repeated without side effects (e.g. granting an already-granted role is a no-op). `false` means the action must be guarded (e.g. create, delete, unlink).

---

## Taxonomy by Root-Cause Dimension

### 1. Quota (配额)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `QUOTA_EXCEEDED` | `RESOURCE_EXHAUSTED` | Project/region quota or concurrent-op limit hit | `REMEDIATE` (request increase / reduce concurrency) | true |

**Typical GCP API enums:** `RESOURCE_EXHAUSTED` (429), `QUOTA_EXCEEDED`.
**Product-specific rollups:** Cloud SQL `QUOTA_EXCEEDED`, GKE `QUOTA_EXCEEDED` / `RESOURCE_EXHAUSTED` (zone capacity).

### 2. Permission (权限)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `PERMISSION_DENIED` | `PERMISSION_DENIED` | IAM role/binding missing for principal | `REMEDIATE` (grant required role) | true |
| `AUTH_FAILED` | `UNAUTHENTICATED` | SA key missing/invalid or token expired | `REMEDIATE` (fix `GOOGLE_APPLICATION_CREDENTIALS`) | true |

**Typical GCP API enums:** `PERMISSION_DENIED` (403), `UNAUTHENTICATED` (401).
**Product-specific rollups:** Billing `PERMISSION_DENIED: billing.*`, IAM `SA_DISABLED` (→ enable SA, `REMEDIATE`).

### 3. Network (网络)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `TIMEOUT` | `TIMEOUT` / `DEADLINE_EXCEEDED` | Network timeout / deadline exceeded | `RETRY` (increase timeout) | true |
| `UNAVAILABLE` | `UNAVAILABLE` | Service/endpoint temporarily unreachable | `RETRY` (exponential backoff) | true |

**Typical GCP API enums:** `DEADLINE_EXCEEDED`, `UNAVAILABLE` (503).
**Product-specific rollups:** GKE `PRIVATE_CLUSTER_ENDPOINT` (→ use `--internal-ip`, `REMEDIATE`), `KUBECONFIG_EXPIRED` (→ refresh, `REMEDIATE`).

### 4. Configuration (配置)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `INVALID_ARGUMENT` | `INVALID_ARGUMENT` | Request validation failed (bad param/format) | `HALT` (fix parameter per API) | true |
| `FAILED_PRECONDITION` | `FAILED_PRECONDITION` | Resource in wrong state for operation | `REMEDIATE` (wait / enable dependency) | true |
| `UNSUPPORTED_ARCH` | — (base code) | Architecture not supported by runtime | `REMEDIATE` (use Docker gcloud) | true |

**Typical GCP API enums:** `INVALID_ARGUMENT` (400), `FAILED_PRECONDITION` (400).
**Product-specific rollups:** Billing `INVALID_ARGUMENT: billing account ID`, `FAILED_PRECONDITION: project unlink`; GKE `VERSION_NOT_AVAILABLE`, `INSUFFICIENT_CIDR`, `AUTOSCALER_CONSTRAINTS` (all → `REMEDIATE` after diagnosis).

### 5. Dependency (依赖)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `BILLING_NOT_ENABLED` | `FAILED_PRECONDITION` | Billing account inactive / not linked | `HALT` (enable in Console — billing mutation) | false |
| `ABORTED` | `ABORTED` | Concurrent modification / etag conflict | `RETRY` (re-fetch etag, retry) | true |

**Typical GCP API enums:** `ABORTED` (409), `FAILED_PRECONDITION`.
**Product-specific rollups:** IAM `ABORTED` (etag conflict), `CONDITION_NOT_SUPPORTED` (→ set policy version 3, `REMEDIATE`).

### 6. Resource State (资源状态)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `NOT_FOUND` | `NOT_FOUND` | Resource does not exist | `HALT` (verify resource name) | true |
| `ALREADY_EXISTS` | `ALREADY_EXISTS` | Duplicate name / resource | `HALT` (choose unique name) | true |
| `STORAGE_FULL` | `RESOURCE_EXHAUSTED` | Instance storage exhausted | `REMEDIATE` (resize / free space) | true |
| `REPLICA_FAILED` | — | Replication broken | `REMEDIATE` (skip/restart replication) | true |

**Typical GCP API enums:** `NOT_FOUND` (404), `ALREADY_EXISTS` (409).
**Product-specific rollups:** Cloud SQL `STORAGE_FULL`, `REPLICA_FAILED`, `BACKUP_FAILED`; GKE `POD_RESOURCE_INSUFFICIENT`, `TAINT_TOLERATION_MISMATCH`, `CLUSTER_DELETE_FAILED`.

### 7. Rate Limit (限流)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `RATE_LIMITED` | `RESOURCE_EXHAUSTED` | Too many concurrent requests (throttling) | `RETRY` (reduce concurrency, backoff) | true |

**Typical GCP API enums:** `RESOURCE_EXHAUSTED` (429) when caused by request rate (not quota).
**Note:** Distinguish from `QUOTA_EXCEEDED` — rate limit is transient throttling; quota is a hard allocation ceiling.

### 8. Authentication (认证)

> Subsumed under `AUTH_FAILED` (Permission dimension) for the base code. Listed separately for clarity: covers credential lifecycle issues.

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `AUTH_FAILED` | `UNAUTHENTICATED` | SA key missing/invalid, token expired | `REMEDIATE` (fix creds path / re-auth) | true |

**Typical GCP API enums:** `UNAUTHENTICATED` (401).
**Product-specific rollups:** IAM `KEY_NOT_FOUND`, `MAX_KEYS_EXCEEDED` (→ manage keys, `REMEDIATE`).

### 9. Unknown (未知)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `INTERNAL` | `INTERNAL` | Server-side error of unknown cause | `RETRY` then `ESCALATE` | true |
| `UNCLASSIFIED` | — | Error not mapped to any dimension | `ESCALATE` (capture raw code/message) | true |

**Typical GCP API enums:** `INTERNAL` (500), `UNKNOWN`.
**Product-specific rollups:** Cloud SQL `RESTORE_FAILED` / `EXPORT_FAILED` / `IMPORT_FAILED` (→ diagnose, `REMEDIATE` or `ESCALATE`).

---

## Dimension → Canonical Code Index

| Dimension | Canonical Codes |
|-----------|-----------------|
| Quota | `QUOTA_EXCEEDED` |
| Permission | `PERMISSION_DENIED`, `AUTH_FAILED` |
| Network | `TIMEOUT`, `UNAVAILABLE` |
| Configuration | `INVALID_ARGUMENT`, `FAILED_PRECONDITION`, `UNSUPPORTED_ARCH` |
| Dependency | `BILLING_NOT_ENABLED`, `ABORTED` |
| Resource State | `NOT_FOUND`, `ALREADY_EXISTS`, `STORAGE_FULL`, `REPLICA_FAILED` |
| Rate Limit | `RATE_LIMITED` |
| Authentication | `AUTH_FAILED` |
| Unknown | `INTERNAL`, `UNCLASSIFIED` |

> `AUTH_FAILED` appears in both Permission and Authentication dimensions by design — it is the credential-lifecycle code; route to Authentication for diagnosis, Permission for the IAM-grant remediation path.

---

## How Skills Reference This Taxonomy

In the troubleshooting section of a `SKILL.md` (or `references/troubleshooting.md`), add a one-line pointer instead of redefining codes:

```
> 错误码遵循 docs/error-taxonomy.md — product-specific codes MUST map to a root-cause dimension above.
```

Per-skill tables stay for product diagnosis but should annotate each row with its canonical dimension code (e.g. `QUOTA_EXCEEDED`) so cross-skill aggregation works.

---

## Mapping to Existing Baselines

- **`docs/diagnostic-logging-standard.md`** §Error Classification (6 base codes) — all 6 are present here: `AUTH_FAILED`, `PERMISSION_DENIED`, `QUOTA_EXCEEDED`, `NOT_FOUND`, `TIMEOUT`, `UNSUPPORTED_ARCH`. No redefinition; this taxonomy extends them.
- **`gcp-gcl-runner-ops/gcl_trace_schema.py`** `GCPErrorType` — gRPC codes map as: `INVALID_ARGUMENT`→Config, `PERMISSION_DENIED`→Permission, `NOT_FOUND`→Resource State, `TIMEOUT`→Network, `INTERNAL`→Unknown, `UNAUTHENTICATED`→Auth, `RESOURCE_EXHAUSTED`→Quota/Resource State/Rate Limit, `FAILED_PRECONDITION`→Config/Dependency, `ABORTED`→Dependency, `OUT_OF_RANGE`→Config, `UNAVAILABLE`→Network.
