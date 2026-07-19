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
**Product-specific rollups:** Cloud SQL `QUOTA_EXCEEDED`, GKE `QUOTA_EXCEEDED` / `RESOURCE_EXHAUSTED` (zone capacity); Memorystore `QUOTA_EXCEEDED` (node/SHARD limit), Filestore `QUOTA_EXCEEDED` (instance tier), Cloud Build `QUOTA_EXCEEDED` (concurrent builds), Pub/Sub `QUOTA_EXCEEDED` (topic/throughput), Composer `QUOTA_EXCEEDED` (environment per region), Monitoring `QUOTA_EXCEEDED` (custom metrics), Logging `QUOTA_EXCEEDED` (log ingestion), CDN `QUOTA_EXCEEDED` (cache egress), Armor `QUOTA_EXCEEDED` (policy/rules per policy), DNS `QUOTA_EXCEEDED` (records per zone), Secret Manager `QUOTA_EXCEEDED` (versions per secret), KMS `QUOTA_EXCEEDED` (crypto keys per ring), GCE `QUOTA_EXCEEDED` (CPUs/disks per zone), LB `QUOTA_EXCEEDED` (forwarding rules), Terraform `QUOTA_EXCEEDED` (API rate via provider), Security Center `QUOTA_EXCEEDED` (findings ingest), Cloud Run `QUOTA_EXCEEDED` (concurrency), Cloud Functions `QUOTA_EXCEEDED` (deployments).

### 2. Permission (权限)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `PERMISSION_DENIED` | `PERMISSION_DENIED` | IAM role/binding missing for principal | `REMEDIATE` (grant required role) | true |
| `AUTH_FAILED` | `UNAUTHENTICATED` | SA key missing/invalid or token expired | `REMEDIATE` (fix `GOOGLE_APPLICATION_CREDENTIALS`) | true |

**Typical GCP API enums:** `PERMISSION_DENIED` (403), `UNAUTHENTICATED` (401).
**Product-specific rollups:** Billing `PERMISSION_DENIED: billing.*`, IAM `SA_DISABLED` (→ enable SA, `REMEDIATE`); GCS `PERMISSION_DENIED` (bucket IAM), BigQuery `PERMISSION_DENIED` (dataset/job), Cloud SQL `PERMISSION_DENIED` (IAM DB auth), Pub/Sub `PERMISSION_DENIED` (topic/subscription IAM), KMS `PERMISSION_DENIED` (CMEK key use), Secret Manager `PERMISSION_DENIED` (secret IAM), Composer `PERMISSION_DENIED` (connection/DB), Cloud Run `PERMISSION_DENIED` (invoker / SA), Cloud Functions `PERMISSION_DENIED` (invoker / runtime SA), Monitoring `PERMISSION_DENIED` (metric write), Logging `PERMISSION_DENIED` (sink write), Security Center `PERMISSION_DENIED` (source/finding), DNS `PERMISSION_DENIED` (zone IAM), Armor `PERMISSION_DENIED` (policy attach), CDN `PERMISSION_DENIED` (signed URL key), Filestore `PERMISSION_DENIED` (NFS export), Memorystore `PERMISSION_DENIED` (instance IAM), LB `PERMISSION_DENIED` (cert/SSL), GCE `PERMISSION_DENIED` (instance/disk), Terraform `PERMISSION_DENIED` (provider SA), VPC `PERMISSION_DENIED` (firewall/subnet), GKE `PERMISSION_DENIED` (Workload Identity), Cloud Build `PERMISSION_DENIED` (trigger SA).

### 3. Network (网络)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `TIMEOUT` | `TIMEOUT` / `DEADLINE_EXCEEDED` | Network timeout / deadline exceeded | `RETRY` (increase timeout) | true |
| `UNAVAILABLE` | `UNAVAILABLE` | Service/endpoint temporarily unreachable | `RETRY` (exponential backoff) | true |

**Typical GCP API enums:** `DEADLINE_EXCEEDED`, `UNAVAILABLE` (503).
**Product-specific rollups:** GKE `PRIVATE_CLUSTER_ENDPOINT` (→ use `--internal-ip`, `REMEDIATE`), `KUBECONFIG_EXPIRED` (→ refresh, `REMEDIATE`); Cloud SQL `UNAVAILABLE` (failover in progress, `RETRY`), Memorystore `UNAVAILABLE` (failover/restart, `RETRY`), Filestore `UNAVAILABLE` (NFS mount timeout, `RETRY`), Pub/Sub `UNAVAILABLE` (subscription endpoint, `RETRY`), Cloud Run `TIMEOUT` (request deadline, `RETRY`), Cloud Functions `TIMEOUT` (function timeout, `RETRY`), GCS `UNAVAILABLE` (retryable 503, `RETRY`), BigQuery `TIMEOUT` (query deadline, `RETRY`), Composer `UNAVAILABLE` (Airflow webserver, `RETRY`), Monitoring `TIMEOUT` (metric write, `RETRY`), Logging `TIMEOUT` (log write, `RETRY`), VPC `UNAVAILABLE` (VPN tunnel down, `RETRY`), LB `UNAVAILABLE` (backend unhealthy, `RETRY`), CDN `TIMEOUT` (origin fetch, `RETRY`), DNS `UNAVAILABLE` (resolver, `RETRY`), KMS `UNAVAILABLE` (key op, `RETRY`), Secret Manager `TIMEOUT` (version access, `RETRY`), Security Center `TIMEOUT` (finding ingest, `RETRY`), Cloud Build `TIMEOUT` (build step, `RETRY`), GCE `UNAVAILABLE` (live migration, `RETRY`), Terraform `TIMEOUT` (provider op, `RETRY`), Armor `UNAVAILABLE` (policy eval, `RETRY`), Billing `UNAVAILABLE` (API, `RETRY`).

### 4. Configuration (配置)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `INVALID_ARGUMENT` | `INVALID_ARGUMENT` | Request validation failed (bad param/format) | `HALT` (fix parameter per API) | true |
| `FAILED_PRECONDITION` | `FAILED_PRECONDITION` | Resource in wrong state for operation | `REMEDIATE` (wait / enable dependency) | true |
| `UNSUPPORTED_ARCH` | — (base code) | Architecture not supported by runtime | `REMEDIATE` (use Docker gcloud) | true |

**Typical GCP API enums:** `INVALID_ARGUMENT` (400), `FAILED_PRECONDITION` (400).
**Product-specific rollups:** Billing `INVALID_ARGUMENT: billing account ID`, `FAILED_PRECONDITION: project unlink`; GKE `VERSION_NOT_AVAILABLE`, `INSUFFICIENT_CIDR`, `AUTOSCALER_CONSTRAINTS` (all → `REMEDIATE` after diagnosis); Cloud SQL `INVALID_ARGUMENT` (tier/flag), `FAILED_PRECONDITION` (instance not running); Memorystore `INVALID_ARGUMENT` (tier), `FAILED_PRECONDITION` (instance busy); Filestore `INVALID_ARGUMENT` (file share), `FAILED_PRECONDITION` (instance busy); Pub/Sub `INVALID_ARGUMENT` (schema), `FAILED_PRECONDITION` (topic exists state); Cloud Run `INVALID_ARGUMENT` (revision), `FAILED_PRECONDITION` (service paused); Cloud Functions `INVALID_ARGUMENT` (runtime), `FAILED_PRECONDITION` (source repo); BigQuery `INVALID_ARGUMENT` (query syntax), `FAILED_PRECONDITION` (dataset locked); Composer `FAILED_PRECONDITION` (PyPI conflict / env busy), `INVALID_ARGUMENT` (DAG); Monitoring `INVALID_ARGUMENT` (metric descriptor), `FAILED_PRECONDITION` (alert policy); Logging `INVALID_ARGUMENT` (sink filter), `FAILED_PRECONDITION` (bucket state); Security Center `INVALID_ARGUMENT` (finding), `FAILED_PRECONDITION` (mute rule); DNS `INVALID_ARGUMENT` (record set), `FAILED_PRECONDITION` (zone state); Armor `INVALID_ARGUMENT` (rule expr), `FAILED_PRECONDITION` (policy state); CDN `INVALID_ARGUMENT` (signed URL), `FAILED_PRECONDITION` (origin); KMS `INVALID_ARGUMENT` (key purpose), `FAILED_PRECONDITION` (key disabled); Secret Manager `INVALID_ARGUMENT` (secret), `FAILED_PRECONDITION` (replication); VPC `INVALID_ARGUMENT` (CIDR), `FAILED_PRECONDITION` (peering active); LB `INVALID_ARGUMENT` (URL map), `FAILED_PRECONDITION` (backend); GCE `INVALID_ARGUMENT` (machine type), `FAILED_PRECONDITION` (instance state); Terraform `INVALID_ARGUMENT` (HCL), `FAILED_PRECONDITION` (state lock); Cloud Build `INVALID_ARGUMENT` (build step), `FAILED_PRECONDITION` (trigger).

### 5. Dependency (依赖)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `BILLING_NOT_ENABLED` | `FAILED_PRECONDITION` | Billing account inactive / not linked | `HALT` (enable in Console — billing mutation) | false |
| `ABORTED` | `ABORTED` | Concurrent modification / etag conflict | `RETRY` (re-fetch etag, retry) | true |

**Typical GCP API enums:** `ABORTED` (409), `FAILED_PRECONDITION`.
**Product-specific rollups:** IAM `ABORTED` (etag conflict), `CONDITION_NOT_SUPPORTED` (→ set policy version 3, `REMEDIATE`); Terraform `ABORTED` (state lock conflict, `RETRY`), GCS `ABORTED` (concurrent object compose, `RETRY`), BigQuery `ABORTED` (concurrent DML, `RETRY`), Cloud SQL `ABORTED` (concurrent op, `RETRY`), Pub/Sub `ABORTED` (concurrent subscription update, `RETRY`), Composer `ABORTED` (concurrent env update, `RETRY`), Monitoring `ABORTED` (concurrent metric write, `RETRY`), Logging `ABORTED` (concurrent sink update, `RETRY`), KMS `ABORTED` (concurrent key op, `RETRY`), Secret Manager `ABORTED` (concurrent version, `RETRY`), DNS `ABORTED` (concurrent zone change, `RETRY`), VPC `ABORTED` (concurrent firewall patch, `RETRY`), LB `ABORTED` (concurrent backend update, `RETRY`), Armor `ABORTED` (concurrent policy update, `RETRY`), Cloud Run `ABORTED` (concurrent revision, `RETRY`), Cloud Functions `ABORTED` (concurrent deploy, `RETRY`), GKE `ABORTED` (concurrent cluster update, `RETRY`), GCE `ABORTED` (concurrent disk op, `RETRY`), Memorystore `ABORTED` (concurrent instance op, `RETRY`), Filestore `ABORTED` (concurrent instance op, `RETRY`), Cloud Build `ABORTED` (concurrent trigger, `RETRY`), CDN `ABORTED` (concurrent cache config, `RETRY`), Security Center `ABORTED` (concurrent finding, `RETRY`), Billing `ABORTED` (concurrent budget update, `RETRY`).

### 6. Resource State (资源状态)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `NOT_FOUND` | `NOT_FOUND` | Resource does not exist | `HALT` (verify resource name) | true |
| `ALREADY_EXISTS` | `ALREADY_EXISTS` | Duplicate name / resource | `HALT` (choose unique name) | true |
| `STORAGE_FULL` | `RESOURCE_EXHAUSTED` | Instance storage exhausted | `REMEDIATE` (resize / free space) | true |
| `REPLICA_FAILED` | — | Replication broken | `REMEDIATE` (skip/restart replication) | true |

**Typical GCP API enums:** `NOT_FOUND` (404), `ALREADY_EXISTS` (409).
**Product-specific rollups:** Cloud SQL `STORAGE_FULL`, `REPLICA_FAILED`, `BACKUP_FAILED`; GKE `POD_RESOURCE_INSUFFICIENT`, `TAINT_TOLERATION_MISMATCH`, `CLUSTER_DELETE_FAILED`; GCS `NOT_FOUND` (object/bucket), `ALREADY_EXISTS` (bucket); BigQuery `NOT_FOUND` (dataset/table), `ALREADY_EXISTS` (table); Pub/Sub `NOT_FOUND` (topic/subscription), `ALREADY_EXISTS` (topic); Cloud Run `NOT_FOUND` (revision), `ALREADY_EXISTS` (service); Cloud Functions `NOT_FOUND` (function), `ALREADY_EXISTS` (function); Composer `NOT_FOUND` (DAG/environment), `ALREADY_EXISTS` (environment); Monitoring `NOT_FOUND` (metric), `ALREADY_EXISTS` (alert); Logging `NOT_FOUND` (sink/bucket), `ALREADY_EXISTS` (sink); Security Center `NOT_FOUND` (finding/source), `ALREADY_EXISTS` (source); DNS `NOT_FOUND` (zone), `ALREADY_EXISTS` (record); Armor `NOT_FOUND` (policy), `ALREADY_EXISTS` (rule); CDN `NOT_FOUND` (origin), `ALREADY_EXISTS` (cache); KMS `NOT_FOUND` (key), `ALREADY_EXISTS` (key); Secret Manager `NOT_FOUND` (secret/version), `ALREADY_EXISTS` (secret); VPC `NOT_FOUND` (subnet), `ALREADY_EXISTS` (peering); LB `NOT_FOUND` (forwarding rule), `ALREADY_EXISTS` (URL map); GCE `NOT_FOUND` (instance), `ALREADY_EXISTS` (disk); Terraform `NOT_FOUND` (resource post-apply), `ALREADY_EXISTS` (import conflict); Cloud Build `NOT_FOUND` (trigger), `ALREADY_EXISTS` (build); Memorystore `NOT_FOUND` (instance), `ALREADY_EXISTS` (instance); Filestore `NOT_FOUND` (instance), `ALREADY_EXISTS` (file share); Billing `NOT_FOUND` (billing account), `ALREADY_EXISTS` (budget).

### 7. Rate Limit (限流)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `RATE_LIMITED` | `RESOURCE_EXHAUSTED` | Too many concurrent requests (throttling) | `RETRY` (reduce concurrency, backoff) | true |

**Typical GCP API enums:** `RESOURCE_EXHAUSTED` (429) when caused by request rate (not quota).
**Note:** Distinguish from `QUOTA_EXCEEDED` — rate limit is transient throttling; quota is a hard allocation ceiling.
**Product-specific rollups:** Pub/Sub `RATE_LIMITED` (publish throughput), Cloud Run `RATE_LIMITED` (request concurrency), Cloud Functions `RATE_LIMITED` (invocations), BigQuery `RATE_LIMITED` (concurrent jobs), GCS `RATE_LIMITED` (request rate per bucket), Monitoring `RATE_LIMITED` (metric ingest), Logging `RATE_LIMITED` (log ingest), KMS `RATE_LIMITED` (crypto ops), Secret Manager `RATE_LIMITED` (access), Composer `RATE_LIMITED` (API calls), Cloud Build `RATE_LIMITED` (builds), DNS `RATE_LIMITED` (changes per zone), Armor `RATE_LIMITED` (policy eval), CDN `RATE_LIMITED` (cache fill), Security Center `RATE_LIMITED` (findings), IAM `RATE_LIMITED` (token mint), VPC `RATE_LIMITED` (API), GKE `RATE_LIMITED` (API), GCE `RATE_LIMITED` (API), Memorystore `RATE_LIMITED` (API), Filestore `RATE_LIMITED` (API), LB `RATE_LIMITED` (API), Terraform `RATE_LIMITED` (provider), Billing `RATE_LIMITED` (API).

### 8. Authentication (认证)

> Subsumed under `AUTH_FAILED` (Permission dimension) for the base code. Listed separately for clarity: covers credential lifecycle issues.

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `AUTH_FAILED` | `UNAUTHENTICATED` | SA key missing/invalid, token expired | `REMEDIATE` (fix creds path / re-auth) | true |

**Typical GCP API enums:** `UNAUTHENTICATED` (401).
**Product-specific rollups:** IAM `KEY_NOT_FOUND`, `MAX_KEYS_EXCEEDED` (→ manage keys, `REMEDIATE`); GKE `AUTH_FAILED` (Workload Identity token, `REMEDIATE`), Cloud Run `AUTH_FAILED` (invoker token, `REMEDIATE`), Cloud Functions `AUTH_FAILED` (runtime SA, `REMEDIATE`), Composer `AUTH_FAILED` (connection OAuth, `REMEDIATE`), Pub/Sub `AUTH_FAILED` (push auth, `REMEDIATE`), BigQuery `AUTH_FAILED` (job SA, `REMEDIATE`), Cloud SQL `AUTH_FAILED` (IAM DB auth, `REMEDIATE`), GCS `AUTH_FAILED` (CMEK/HMAC, `REMEDIATE`), Secret Manager `AUTH_FAILED` (access SA, `REMEDIATE`), KMS `AUTH_FAILED` (crypto SA, `REMEDIATE`), Monitoring `AUTH_FAILED` (write SA, `REMEDIATE`), Logging `AUTH_FAILED` (sink SA, `REMEDIATE`), Security Center `AUTH_FAILED` (source SA, `REMEDIATE`), DNS `AUTH_FAILED` (zone SA, `REMEDIATE`), Armor `AUTH_FAILED` (policy SA, `REMEDIATE`), CDN `AUTH_FAILED` (signed URL, `REMEDIATE`), VPC `AUTH_FAILED` (VPN SA, `REMEDIATE`), LB `AUTH_FAILED` (cert SA, `REMEDIATE`), GCE `AUTH_FAILED` (instance SA, `REMEDIATE`), Memorystore `AUTH_FAILED` (instance SA, `REMEDIATE`), Filestore `AUTH_FAILED` (instance SA, `REMEDIATE`), Cloud Build `AUTH_FAILED` (worker SA, `REMEDIATE`), Terraform `AUTH_FAILED` (provider SA, `REMEDIATE`), Billing `AUTH_FAILED` (billing SA, `REMEDIATE`).

### 9. Unknown (未知)

| Canonical Code | gRPC Mapping | Semantic | Recovery | Idempotent Safe |
|----------------|--------------|----------|----------|:----------------:|
| `INTERNAL` | `INTERNAL` | Server-side error of unknown cause | `RETRY` then `ESCALATE` | true |
| `UNCLASSIFIED` | — | Error not mapped to any dimension | `ESCALATE` (capture raw code/message) | true |

**Typical GCP API enums:** `INTERNAL` (500), `UNKNOWN`.
**Product-specific rollups:** Cloud SQL `RESTORE_FAILED` / `EXPORT_FAILED` / `IMPORT_FAILED` (→ diagnose, `REMEDIATE` or `ESCALATE`); GKE `INTERNAL` (control plane, `RETRY`→`ESCALATE`), Cloud Run `INTERNAL` (runtime, `RETRY`→`ESCALATE`), Cloud Functions `INTERNAL` (runtime, `RETRY`→`ESCALATE`), Composer `INTERNAL` (scheduler, `RETRY`→`ESCALATE`), Pub/Sub `INTERNAL` (backend, `RETRY`→`ESCALATE`), BigQuery `INTERNAL` (job, `RETRY`→`ESCALATE`), GCS `INTERNAL` (backend, `RETRY`→`ESCALATE`), Monitoring `INTERNAL` (ingest, `RETRY`→`ESCALATE`), Logging `INTERNAL` (ingest, `RETRY`→`ESCALATE`), Security Center `INTERNAL` (ingest, `RETRY`→`ESCALATE`), KMS `INTERNAL` (crypto, `RETRY`→`ESCALATE`), Secret Manager `INTERNAL` (access, `RETRY`→`ESCALATE`), DNS `INTERNAL` (change, `RETRY`→`ESCALATE`), Armor `INTERNAL` (policy eval, `RETRY`→`ESCALATE`), CDN `INTERNAL` (cache, `RETRY`→`ESCALATE`), VPC `INTERNAL` (API, `RETRY`→`ESCALATE`), LB `INTERNAL` (forwarding, `RETRY`→`ESCALATE`), GCE `INTERNAL` (instance, `RETRY`→`ESCALATE`), Memorystore `INTERNAL` (instance, `RETRY`→`ESCALATE`), Filestore `INTERNAL` (instance, `RETRY`→`ESCALATE`), Cloud Build `INTERNAL` (build, `RETRY`→`ESCALATE`), Terraform `INTERNAL` (provider, `RETRY`→`ESCALATE`), Billing `INTERNAL` (API, `RETRY`→`ESCALATE`).

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

---

## Skill Directory Coverage (27 skills)

All 27 `gcp-*-ops` skills are mapped to the dimensions above. Directory → primary dimensions:

| Skill Directory | Primary Dimensions |
|-----------------|--------------------|
| `gcp-gce-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-lb-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-logging-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-kms-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-memorystore-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-cloudbuild-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-billing-ops` | Quota, Permission, Config, Dependency, Rate Limit, Auth, Unknown |
| `gcp-vpc-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-gke-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-cloudsql-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-gcs-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-iam-ops` | Permission, Dependency, Authentication, Rate Limit, Auth, Unknown |
| `gcp-dns-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-pubsub-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-cloudrun-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-cloudfunctions-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-monitoring-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-bigquery-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-secretmanager-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-cdn-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-securitycenter-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-filestore-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-gcl-runner-ops` | Dependency (GCL orchestration), Unknown |
| `gcp-terraform-ops` | Quota, Permission, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-armor-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
| `gcp-composer-ops` | Quota, Permission, Network, Config, Dependency, Resource State, Rate Limit, Auth, Unknown |
