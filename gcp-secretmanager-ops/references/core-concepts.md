# Core Concepts — Cloud Secret Manager

## Architecture

Google Cloud Secret Manager provides centralized secret storage, version management, and access control. Secrets are stored with automatic multi-region replication or user-managed per-region replication, with fine-grained IAM controls and audit logging.

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **Secret** | Logical container for secret data with replication and rotation config | Project-unique |
| **Secret Version** | Individual version of secret payload (numbered sequentially) | Secret |
| **Replication Policy** | Automatic (multi-region) or User-managed (per-region locations) | Secret |
| **Rotation Schedule** | Optional automatic rotation period with next-rotation-time | Secret |
| **Topics** | Pub/Sub notification topics for rotation and lifecycle events | Secret |

### Replication Policies

| Policy | Description | Use Case |
|--------|-------------|----------|
| `automatic` | Google-managed multi-region replication | General-purpose secrets |
| `user-managed` | User-specified locations (e.g., us-central1, europe-west1) | Compliance, data residency |

### Secret Version States

| State | Description | Accessible | Duration |
|-------|-------------|------------|----------|
| `ENABLED` | Active and accessible | Yes | Indefinite |
| `DISABLED` | Cannot be accessed | No | Indefinite |
| `DESTROYED` | Permanently deleted; cannot be recovered | No | Permanent |

### Quotas

| Resource | Default Limit |
|----------|--------------|
| Secrets per project | 10,000 |
| Secret versions per secret | Unlimited (practical limit: storage cost) |
| Payload size per version | 64 KB (65,536 bytes) |
| API requests per minute | 3,000 (per project) |
| Access requests per secret per minute | 600 |

> **TE-1 Compliance:** Quotas are subject to change. Use `gcloud services quota` or [Quotas page](https://console.cloud.google.com/iam-admin/quotas) for current limits.

## Dependencies

| Depend On | Reason |
|-----------|--------|
| Cloud IAM | Secret access control |
| Cloud Pub/Sub | Notification topics for rotation events |
| Cloud KMS | CMEK for user-managed replication (optional) |
| Cloud Logging | Audit logging of secret operations |

## Security Model

| Feature | Description |
|---------|-------------|
| **IAM-based access** | roles/secretmanager.admin, roles/secretmanager.secretAccessor, roles/secretmanager.viewer |
| **Encryption at rest** | Google-managed keys (automatic) or CMEK (user-managed) |
| **VPC Service Controls** | Restrict access to specific VPC networks |
| **Audit logging** | All operations logged to Cloud Audit Logs |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Secret deleted | All applications lose access to secret | Use version aliases; confirm before delete |
| All versions destroyed | Secret data permanently lost | Maintain at least one ENABLED version |
| Secret disabled | No versions accessible | Re-enable secret or create new version |
| Replication failure | Secret unavailable in some regions | Use automatic replication for HA |
