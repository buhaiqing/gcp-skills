# Well-Architected Assessment — Cloud DNS

## Framework Mapping

This assessment maps Cloud DNS operations to the [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework) five pillars.

### 2.1 Security Pillar

| Recommendation | Implementation | Priority |
|----------------|----------------|----------|
| **DNSSEC signing** | Enable DNSSEC on public zones; publish DS record at registrar | High |
| **Private zones for internal DNS** | Use private zones with VPC binding instead of public zones for internal services | High |
| **IAM least privilege** | Grant `roles/dns.reader` for read-only; `roles/dns.admin` only for writers | High |
| **VPC Service Controls** | Include DNS API in VPC SC perimeters for data exfiltration protection | Medium |
| **Audit logging** | Enable Cloud Audit Logs for DNS API calls | Medium |
| **Service account key rotation** | Rotate SA keys regularly; use workload identity where possible | High |

#### DNSSEC Configuration

```bash
# Enable DNSSEC
gcloud dns managed-zones update "{{user.zone_name}}" \
  --dnssec-state="on" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# List DNS keys (for DS record at registrar)
gcloud dns dns-keys list --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

#### IAM Policy Check

```bash
# Check DNS IAM bindings
gcloud projects get-iam-policy "{{env.CLOUDSDK_CORE_PROJECT}}" \
  --flatten="bindings[].members" \
  --format="table(bindings.role, bindings.members)" \
  --filter="bindings.role:roles/dns"
```

### 2.2 Stability Pillar

| Recommendation | Implementation | Priority |
|----------------|----------------|----------|
| **DNS propagation management** | Lower TTL (60-300s) before planned changes; wait for propagation before restoring | High |
| **Failover record configuration** | Use multiple A records with different TTLs for basic failover | Medium |
| **Multi-region DNS** | Use Cloud DNS with global anycast name servers (built-in) | High |
| **Backup zone configuration** | Document zone configuration in IaC (Terraform) for disaster recovery | High |
| **Transaction atomicity** | Use transaction API for multi-record changes to ensure consistency | High |

#### TTL Strategy

| Scenario | Recommended TTL | Rationale |
|----------|----------------|-----------|
| Production stable | 3600s (1 hour) | Good cache performance |
| Pre-migration | 60s (1 minute) | Fast propagation of changes |
| Testing | 300s (5 minutes) | Balance between speed and cache |
| Failover records | 60s (1 minute) | Quick failover response |

#### DNS Export for Backup

```bash
# Export zone file (BIND format)
gcloud dns record-sets export zone-backup-$(date +%Y%m%d).zone \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Import zone file (restore)
gcloud dns record-sets import zone-backup.zone \
  --zone="{{user.zone_name}}" \
  --delete-all-existing \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 2.3 Cost Pillar

| Factor | Cost Model | Optimization |
|--------|-----------|--------------|
| **Managed zones** | Per zone per month | Minimize zone count; use subdomains within a zone |
| **DNS queries** | Per query (first billion free) | Optimize TTL to reduce query volume |
| **DNSSEC** | Included (no additional cost) | No cost impact |
| **Response policies** | Per policy per month | Evaluate necessity before creating |

#### Cost Optimization Commands

```bash
# Count zones (cost driver)
gcloud dns managed-zones list --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="value(name)" | wc -l

# List policies (additional cost)
gcloud dns policies list --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="value(name)" | wc -l
```

### 2.4 Efficiency Pillar

| Recommendation | Implementation | Priority |
|----------------|----------------|----------|
| **Bulk operations via transaction** | Group multiple record changes into single transaction | High |
| **Automation with SDK** | Use Python SDK for programmatic bulk operations | Medium |
| **Zone file import/export** | Use BIND format for batch zone management | Medium |
| **gcloud filters** | Use `--filter` to reduce API response size | Low |

#### Bulk Record Operation Example

```bash
# Single transaction with multiple changes
gcloud dns record-sets transaction start --zone="{{user.zone_name}}"

gcloud dns record-sets transaction add "www.{{user.dns_name}}" \
  --type="A" --ttl="300" --rrdatas="192.0.2.1" \
  --zone="{{user.zone_name}}"

gcloud dns record-sets transaction add "api.{{user.dns_name}}" \
  --type="A" --ttl="300" --rrdatas="192.0.2.2" \
  --zone="{{user.zone_name}}"

gcloud dns record-sets transaction execute \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 2.5 Performance Pillar

| Metric | Target | Monitoring |
|--------|--------|------------|
| **Query latency** | < 50ms p99 | Cloud Monitoring `dns.googleapis.com/query/response_latencies` |
| **Name server availability** | 99.99% | Built-in Google Cloud SLA |
| **Propagation time** | < 60s internal | Verify with `dig` against name servers |
| **Zone operation time** | < 30s | `managed-zone operations list` |

#### Performance Verification

```bash
# Measure DNS query latency
for i in $(seq 1 10); do
  time dig @ns-cloud-a1.googledomains.com "{{user.record_name}}" "{{user.record_type}}" +short
done

# Check name server response
gcloud dns managed-zones describe "{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="value(nameServers)" | tr ',' '\n' | while read ns; do
    echo "Testing $ns..."
    dig @"$ns" "{{user.dns_name}}" SOA +time=2
  done
```

## Summary Assessment

| Pillar | Status | Key Actions |
|--------|--------|-------------|
| **Security** | Review | Enable DNSSEC, enforce IAM least privilege, use private zones |
| **Stability** | Good | Use TTL management, transaction atomicity, zone backups |
| **Cost** | Review | Minimize zone count, optimize TTL |
| **Efficiency** | Good | Use transaction batches, SDK for automation |
| **Performance** | Good | Built-in global anycast, < 50ms p99 latency |
