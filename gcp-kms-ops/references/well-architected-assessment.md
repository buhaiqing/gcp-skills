# Well-Architected Assessment — Cloud KMS

> **Objective:** Five-pillar assessment of the Cloud KMS skill against the [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework).

---

## 1. Security Pillar

### IAM Requirements

| Role | Use Case | Minimum for Operations |
|------|----------|----------------------|
| `roles/cloudkms.admin` | Full management | Create/delete keys, manage IAM, rotation policies |
| `roles/cloudkms.cryptoKeyEncrypterDecrypter` | Encrypt/decrypt | Encrypt and decrypt operations |
| `roles/cloudkms.cryptoKeyEncrypter` | Encrypt-only | Encrypt operations only |
| `roles/cloudkms.cryptoKeyDecrypter` | Decrypt-only | Decrypt operations only |
| `roles/cloudkms.viewer` | Read-only | List and describe keys |

### Key Protection
- Key destruction: 24-hour scheduled window before permanent deletion
- Key version cannot be deleted individually from the system once DESTROYED
- IAM conditions can restrict key access by IP, time, or identity

### Credential Safety
- Service account keys: set expiry, rotate regularly
- Prefer Workload Identity Federation
- Never output key material or credentials in logs

---

## 2. Stability Pillar

### Backup / Recovery

| Component | Mechanism | Target RPO | Target RTO |
|-----------|-----------|------------|------------|
| Key Version (destroyed) | Restore within 24h | N/A | 5 minutes |
| Key Version (DESTROYED >24h) | Irreversible — must use backup key | N/A | N/A |
| Key Ring | Cannot be deleted; always recoverable | N/A | N/A |

### Multi-Region Patterns
- Create key rings in multiple locations for geo-redundancy
- Use CMEK keys backed by KMS for cross-region resource encryption
- Export key material for external backup (where supported)

---

## 3. Cost Pillar

### Pricing Model

| Protection Level | Cost per Key Version | API Request Cost |
|-----------------|---------------------|------------------|
| Software | $0.06/month | $0.03 per 10K operations |
| HSM | $1.00/month | $0.10 per 10K operations |
| External | Varies | $0.03 per 10K operations |

### Optimization

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Share keys across services | Medium | One CMEK key per purpose, not per resource |
| Use software keys when possible | Medium | HSM only for compliance workloads |
| Rotate only when necessary | Low | Avoid frequent rotation unless required |

---

## 4. Efficiency Pillar

### Automation Patterns

| Pattern | Implementation |
|---------|---------------|
| Key rotation | `gcloud kms keys update` with rotation-period |
| Key ring organization | Location-based naming: `{purpose}-{env}-keys` |
| IAM automation | gcloud or Terraform for key permissions |
| Key labeling | Use labels for cost tracking and lifecycle management |

---

## 5. Performance Pillar

| Metric | Target Threshold | Action if Exceeded |
|--------|-----------------|-------------------|
| Encrypt latency (software) | < 20ms | Check network; consider client-side caching |
| Encrypt latency (HSM) | < 100ms | Check HSM utilization |
| Rate limit (software) | 6,000/min | Implement client-side rate limiting |
| Rate limit (HSM) | 600/min | Consider batching or software keys |

---

## 6. Integration Depth Matrix

| Dimension | Required | How Integrate |
|-----------|----------|--------------|
| Security | Required | IAM roles, key version state protection, 24h restore window |
| Stability | Required | Version lifecycle, key ring immutability |
| Cost | Required | Protection level selection, key version management |
| Efficiency | Required | Rotation policy, labeling, automation |
| Performance | Required | Rate limits, latency monitoring |