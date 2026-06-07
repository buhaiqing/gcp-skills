# Well-Architected Assessment — Memorystore for Redis

> **Objective:** Five-pillar assessment of the Memorystore for Redis skill against the [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework).

---

## 1. Security Pillar

### IAM Requirements

| Role | Use Case | Minimum for Operations |
|------|----------|----------------------|
| `roles/redis.admin` | Full management | Create/delete instances, export/import |
| `roles/redis.viewer` | Read-only | List and describe instances |
| `roles/redis.editor` | Modify (no delete) | Scale, update config |

### Data Protection
- Auth String: password-based Redis authentication
- In-transit encryption: TLS for all Redis connections
- VPC-private connectivity: no public IP exposure
- Server CA certificates for TLS verification

### Credential Safety
- Auth String is set at creation time; can be viewed via describe
- Never expose auth string in logs or command history
- Prefer IAM-based access over embedded passwords

---

## 2. Stability Pillar

### Backup / Recovery

| Component | Mechanism | Target RPO | Target RTO |
|-----------|-----------|------------|------------|
| Redis data (RDB) | Export to GCS (manual/scheduled) | 1 hour | 30 min |
| Redis data (AOF) | AOF persistence for crash recovery | Near-real-time | 5 min |
| HA failover (Standard tier) | Automatic replica promotion | N/A | 30 seconds |

### Multi-Region Patterns
- Cross-region replication is NOT natively supported
- Use export/import for cross-region data migration
- Deploy regional instances with application-level routing

---

## 3. Cost Pillar

### Pricing Model

| Tier | Cost Factor | Notes |
|------|-------------|-------|
| Basic | $ per GB per hour | No extra replica cost |
| Standard (HA) | 2x Basic (primary + replica) | Includes automatic failover |
| Read Replicas | Additional $ per replica per hour | Standard tier only |

### Optimization

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Right-size memory | High | Monitor usage, avoid over-provisioning |
| Basic tier for dev/test | Medium | No HA needed for development |
| Export snapshots | Low | Only snapshot when needed |
| Shorter retention | Low | No native tiered storage |

---

## 4. Efficiency Pillar

### Automation Patterns

| Pattern | Implementation |
|---------|---------------|
| Instance creation | Terraform or gcloud scripting |
| Auto-scaling | Not natively supported; manual scale |
| Export scheduling | Cloud Scheduler + Cloud Functions |
| Instance labeling | Use labels for cost tracking |

---

## 5. Performance Pillar

| Metric | Target Threshold | Action if Exceeded |
|--------|-----------------|-------------------|
| Memory usage | < 80% | Scale up or optimize keys |
| CPU utilization | < 70% | Scale up or optimize commands |
| Connection count | < 80% of max | Optimize connection pool |
| Cache hit rate | > 90% | Review eviction policy |
| Replication lag | < 1 second (Standard) | Check network/primary |

---

## 6. Integration Depth Matrix

| Dimension | Required | How Integrate |
|-----------|----------|--------------|
| Security | Required | Auth string, VPC-private, IAM roles |
| Stability | Required | Standard tier for HA, export/import backup |
| Cost | Required | Instance sizing, tier selection |
| Efficiency | Required | Labeling, automation |
| Performance | Required | Memory/CPU monitoring, scaling |