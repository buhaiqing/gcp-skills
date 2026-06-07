# Well-Architected Assessment — Cloud SQL

## §1 Security

| IAM Role | Use Case |
|----------|----------|
| roles/cloudsql.admin | Full Cloud SQL API — production |
| roles/cloudsql.client | Connect to instances (read-only) |
| roles/cloudsql.editor | Create/update/delete instances |
| roles/cloudsql.viewer | Read-only instance monitoring |

**IAM DB Authentication** (PostgreSQL only): Eliminates passwords by using IAM principals.
- Enable with `--database-flags=cloudsql.iam_authentication=on`
- Create IAM users via `gcloud sql users create` with `--type=cloud_iam_service_account`
- Connect via Cloud SQL Auth Proxy with `--auto-iam-authn`

**Credentials**: NEVER log SA key content. Only check: `test -f "$GOOGLE_APPLICATION_CREDENTIALS"`
**SSL/TLS**: Always enforce SSL for production connections.
**Authorized Networks**: Restrict to specific IP ranges; use Cloud SQL Auth Proxy for dynamic IPs.
**CMEK**: Use Customer-Managed Encryption Keys for sensitive data at rest.
**Deletion Protection**: Set `--deletion-protection` on production instances.

### Security checklist

| # | Item | Command |
|---|------|---------|
| 1 | Enforce SSL | `gcloud sql instances patch NAME --require-ssl` |
| 2 | Restrict authorized networks | `gcloud sql instances patch NAME --authorized-networks=CIDR` |
| 3 | Enable deletion protection | `gcloud sql instances patch NAME --deletion-protection` |
| 4 | Use private IP | `gcloud sql instances patch NAME --network=VPC` |
| 5 | Enable IAM DB auth (PG) | `gcloud sql instances patch NAME --database-flags=cloudsql.iam_authentication=on` |
| 6 | Rotate server CA cert | `gcloud sql instances rotate-server-ca NAME` |

## §2 Stability

| Strategy | Implementation |
|----------|---------------|
| HA failover | REGIONAL availability type — synchronous replication across zones |
| Automated backups | Enable with `--backup-start-time` and `--enable-point-in-time-recovery` |
| Read replicas | Same-region or cross-region for read offload |
| Cross-region disaster recovery | Read replica in different region + promote to standalone |
| Cloning | Point-in-time clone for testing/fast recovery |

### DR Runbook

1. Primary instance fails → check state: `gcloud sql instances describe PRIMARY --format="json" | jq -r '.state'`
2. If cross-region replica exists, promote: `gcloud sql instances promote-replica REPLICA_NAME`
3. If no replica, restore latest backup: `gcloud sql backups restore BACKUP_ID --restore-instance=INSTANCE`
4. Update connection strings in application config
5. Verify connectivity: `gcloud sql connect NEW_PRIMARY --user=USER`

### Backup Strategy

| Type | Frequency | Retention | RPO | RTO |
|------|-----------|-----------|-----|-----|
| Automated | Daily | Configurable (1-365d) | ~24h | ~15-60min |
| PITR (MySQL/PG) | Continuous | Configurable (1-7d) | ~1-5min | ~15-60min |
| On-demand | As needed | Manual delete | Immediate | ~15-60min |
| Export to GCS | As needed | GCS lifecycle | At export time | ~30min-2h |

## §3 Cost

| Model | Discount | Best For |
|-------|----------|----------|
| Pay-as-you-go | Standard | Dev/test, variable workloads |
| Committed Use (1yr) | Up to 25% | Predictable production |
| Committed Use (3yr) | Up to 40% | Long-term, stable workloads |

**Idle detection**: Alert on CPU < 5% for 7 days → right-size or stop.

### Cost Optimization

| Strategy | Action |
|----------|--------|
| Right-size tier | Use Query Insights to detect over-provisioned instances |
| Delete idle instances | Alert on zero connections for >30d |
| Use SSD over HDD | HDD only for very large, infrequently accessed data |
| Manage backup retention | Reduce to 7-14d for non-production |
| Delete old exports | Set GCS lifecycle rules for export files |
| Use pgBouncer (PG) | Connection pooling reduces instance size requirements |

## §4 Efficiency

- **Database flags**: Optimize per workload (e.g., `max_connections`, `work_mem`, `innodb_buffer_pool_size`)
- **Maintenance window**: Schedule during low-traffic hours
- **Query Insights**: Identify slow queries, missing indexes, and high-frequency queries
- **Connection pooling**: Use pgBouncer (PG) or ProxySQL (MySQL) for efficient connection management
- **Labels**: Cost tracking (`env`, `app`, `team`)

### Flag Optimization Examples

| Engine | Flag | Recommended | Rationale |
|--------|------|-------------|-----------|
| MySQL | `max_connections` | 250-1000 | Match app needs; avoid OOM |
| MySQL | `innodb_buffer_pool_size` | 70-80% of memory | Default is conservative |
| MySQL | `slow_query_log` | ON | Enable with Query Insights |
| PG | `max_connections` | 100-500 | PG is connection-heavy |
| PG | `work_mem` | 4-16MB | Balance memory and sort perf |
| PG | `shared_buffers` | 25% of memory | Default is conservative |

## §5 Performance

| Tier Family | vCPU | Memory | Network | Use Case |
|-------------|------|--------|---------|----------|
| db-f1-micro | 0.5 | 0.6 GB | Low | Dev, low-traffic apps |
| db-g1-small | 1 | 1.7 GB | Low | Small apps, testing |
| db-n1-standard-1 | 1 | 3.75 GB | Moderate | Small production |
| db-n1-standard-2 | 2 | 7.5 GB | Moderate | General purpose |
| db-n1-standard-4 | 4 | 15 GB | Moderate | Medium production |
| db-n1-standard-8 | 8 | 30 GB | High | Large production |
| db-n1-standard-16 | 16 | 60 GB | High | Memory-intensive |
| db-n1-standard-32 | 32 | 120 GB | High | Very large workloads |
| db-custom-* | Custom | Custom | Varies | Custom configurations |

### Storage Type Selection

| Storage Type | Max IOPS | Max Throughput | Use Case |
|-------------|----------|---------------|----------|
| SSD (PD-SSD) | 15,000-60,000 | 480 MB/s | General production |
| HDD (PD-HDD) | 300-2,500 | 120 MB/s | Archive, dev, staging |

> **Performance tip**: Use read replicas to offload read traffic from the primary instance. Enable Query Insights to identify and optimize slow queries.