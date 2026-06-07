# Core Concepts — Cloud KMS

## Architecture

Google Cloud KMS is a cryptographic key management service that supports symmetric and asymmetric keys, HSM-backed keys, key rotation, and IAM integration.

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **Key Ring** | Logical grouping of keys (organizational, not security boundary) | Location |
| **Crypto Key** | Logical key containing one or more key versions | Key ring |
| **Key Version** | Individual cryptographic key material with version number | Crypto key |
| **Primary Version** | Active key version used by default for encrypt/decrypt | Crypto key |
| **Import Job** | Import external key material into KMS | Key ring |

### Key Purposes

| Purpose | Key Type | Use Case |
|---------|----------|----------|
| `encryption` | Symmetric (AES-256-GCM) | Encrypt/decrypt data ≤ 64KB |
| `asymmetric-encryption` | Asymmetric (RSA) | Encrypt with public, decrypt with private |
| `asymmetric-signing` | Asymmetric (EC/RSA) | Sign/verify digital signatures |
| `mac` | Symmetric (HMAC) | Compute/verify MACs |

### Protection Levels

| Level | Backed By | Key Features |
|-------|-----------|--------------|
| `software` | Software | No extra cost, lower latency |
| `hsm` | Cloud HSM | FIPS 140-2 Level 3, higher cost |
| `external` | External key manager | Customer-controlled, highest control |

## Key Version States

| State | Description | Duration |
|-------|-------------|----------|
| `ENABLED` | Active and usable for crypto operations | Indefinite |
| `DISABLED` | Cannot be used for crypto operations | Indefinite |
| `DESTROY_SCHEDULED` | Scheduled for permanent deletion | 24 hours |
| `DESTROYED` | Permanently deleted; cannot be restored | Permanent |
| `PENDING_GENERATION` | Awaiting automatic generation | Transient |
| `PENDING_IMPORT` | Awaiting key material import | Transient |
| `IMPORT_FAILED` | Import failed | Transient |

## Quotas

| Resource | Default Limit |
|----------|--------------|
| Key rings per location per project | 1,000 |
| Keys per key ring | 1,000 |
| Key versions per key | 10 |
| Encrypt requests per minute (software) | 6,000 |
| Encrypt requests per minute (HSM) | 600 |
| Key material import jobs per project | 50 |

## Dependencies

| Depend On | Reason |
|-----------|--------|
| Cloud IAM | Key access control |
| Cloud HSM | HSM protection level |
| Cloud Logging | Audit logging of key operations |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Primary key version destroyed | Encrypt/decrypt fails | Restore within 24h; designate new primary |
| CMEK key disabled | Dependent resources inaccessible | Enable version; check IAM |
| Key ring deleted | All keys in ring lost | Ring deletion not supported; protect via IAM |
| External key unavailable | Encrypt/decrypt fails | Ensure external KMS availability |