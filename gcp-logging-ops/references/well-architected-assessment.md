# Well-Architected Assessment — Cloud Logging

> **Objective:** Five-pillar assessment of the Cloud Logging skill against the [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework).

---

## 1. Security Pillar

### IAM Requirements

| Role | Use Case | Minimum for Operations |
|------|----------|----------------------|
| `roles/logging.admin` | Full management | Create/delete buckets, sinks, metrics, exclusions |
| `roles/logging.viewer` | Read-only | List and read log entries |
| `roles/logging.logWriter` | Write-only | Send logs to Logging |
| `roles/logging.privateLogViewer` | Read _Required bucket | Access audit logs |

### CMEK (Customer-Managed Encryption Keys)
- Log buckets support CMEK encryption
- Requires Cloud KMS key with EncrypterDecrypter permission for Logging service account (`cloud-logs@system.gserviceaccount.com`)
- Key revocation makes the bucket inaccessible

### VPC Service Controls
- Log buckets can be protected by VPC-SC perimeters
- Prevents data exfiltration to unauthorized networks

### Credential Safety
- Service account keys: set expiry, rotate regularly
- Prefer Workload Identity Federation for GKE/Cloud Run
- Never hardcode credentials in logs or config files

---

## 2. Stability Pillar

### Backup / Recovery

| Component | Mechanism | Target RPO | Target RTO |
|-----------|-----------|------------|------------|
| Log buckets | Bucket cannot be restored after delete; sink to external destination | 1 hour | 15 minutes |
| _Required bucket | Protected from deletion; 400-day retention | N/A | N/A |
| _Default bucket | 30-day retention; can be restored via undelete within 7 days | N/A | 15 minutes |

### Multi-Region Patterns
- Use `global` location for region-independent log storage
- For data residency: use `us` or `eu` locations
- Export critical logs to BigQuery or Cloud Storage for cross-region durability

### Sink Failover
- Configure multiple sinks for critical logs
- Monitor sink delivery using Cloud Monitoring

---

## 3. Cost Pillar

### Pricing Model

| Component | Pricing |
|-----------|---------|
| Log ingestion | $ per GiB ingested (tiered pricing) |
| Log storage | $ per GiB per month (varies by retention) |
| Log export (sinks) | No additional cost beyond destination usage |

### Optimization

| Strategy | Savings Potential | Implementation |
|----------|------------------|----------------|
| Exclusion rules | High (30-70%) | Exclude verbose / debug / health check logs |
| Retention tuning | Medium | Reduce retention for non-compliance logs |
| _Default bucket monitoring | High | Move high-volume logs to custom buckets with shorter retention |
| Log-based metric storage | Low | Metrics storage is cheaper than log storage for aggregated data |

### Idle Resource Detection
- Empty log sinks: sinks with no matching log entries for >7 days
- Overly broad exclusions: filters that exclude >90% of logs
- Underused buckets: buckets with <1 MB/day ingestion

---

## 4. Efficiency Pillar

### Automation Patterns

| Pattern | Implementation |
|---------|---------------|
| Sink creation | Automate via gcloud commands or Terraform |
| Log-based metrics | Create counter metrics for error rates, request latency |
| Exclusion management | Use exclusion rules to filter noisy logs |
| Multi-project aggregation | Configure aggregated sinks to route logs from multiple projects |

### CI/CD Integration
- Use gcloud or Terraform for infrastructure-as-code log routing
- Include log sink and metric configuration in deployment pipelines

---

## 5. Performance Pillar

### Key Metrics & Thresholds

| Metric | Target Threshold | Action if Exceeded |
|--------|-----------------|-------------------|
| Log ingestion rate | < 10K entries/sec per project | Create exclusions, request quota increase |
| Query response time | < 5 seconds for 7-day range | Narrow time range, optimize filter |
| Log entry visibility | < 2 minutes (ingestion → queryable) | Check for throttling |

### Cloud Logging is Fully Managed
- Auto-scaling: built-in, no user configuration
- Performance optimization: use specific filters, avoid overly broad queries
- Log Analytics: use SQL-like queries for large dataset analysis

---

## 6. Integration Depth Matrix

| Dimension | Required | How Integrate |
|-----------|----------|--------------|
| Security | Required | IAM roles, CMEK, VPC-SC configuration |
| Stability | Required | Multi-region buckets, sink failover, _Required bucket protection |
| Cost | Required | Exclusion rules, retention tuning, volume monitoring |
| Efficiency | Required | Automated sink creation, log-based metrics, CI/CD |
| Performance | Required | Ingestion rate monitoring, filter optimization |