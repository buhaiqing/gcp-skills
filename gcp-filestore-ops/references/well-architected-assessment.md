# Well-Architected Assessment — Filestore

## §1 Security

| IAM Role | Use Case |
|----------|----------|
| roles/filestore.admin | Full Filestore API — production |
| roles/filestore.editor | Create/update/delete instances |
| roles/filestore.viewer | Read-only access |
| roles/filestore.mover | Instance migration |

**Credentials**: Never log SA key content. Only check: `test -f "$GOOGLE_APPLICATION_CREDENTIALS"`

**Encryption**:
- Default encryption at rest (Google-managed keys)
- Use CMEK for sensitive data: `--kms-key=projects/P/locations/L/keyRings/R/cryptoKeys/K`
- NFSv4.1 supports in-transit encryption with Kerberos (krb5p)

**IP-Based Access Control**: Restrict client access by IP address during instance creation or update.

**VPC Service Controls**: Restrict data exfiltration by limiting access to approved VPCs.

**IAM Best Practices**:
- Grant minimum required roles
- Use service accounts for API access
- Rotate service account keys regularly
- Audit IAM bindings periodically

## §2 Stability

| Strategy | Implementation |
|----------|---------------|
| Backups | Schedule automated daily backups; retain 7-30 days |
| Snapshots | Create point-in-time snapshots before major changes |
| Regional tier | Deploy Regional tier for zone failure transparency |
| Instance replication | Async replication to standby instance in another region |
| Monitoring | Set up alerts for low disk space, high latency |

**DR Runbook**:

1. Confirm instance zone/region is unavailable
2. For Zonal tier: Restore from backup to new instance in healthy zone
3. For Regional tier: Transparent failover (automatic)
4. For cross-region DR: Promote standby replica
5. Update application mount points
6. Verify data integrity

**Backup Best Practices**:
- Max 1 backup operation per 10 minutes (steady state)
- Burst: max 6 requests in 60 minutes
- Store backups in different region from source
- Test restore periodically

**Snapshot Best Practices**:
- Max 240 snapshots per instance (Zonal/Regional/Enterprise)
- Snapshots consume capacity — monitor snapshot storage
- Delete stale snapshots

## §3 Cost

| Tier | Cost Profile | Best For |
|------|--------------|----------|
| BASIC_HDD | Lowest | Basic file sharing, dev/test |
| BASIC_SSD | Moderate | High performance dev/test |
| Zonal | Higher | HPC, batch compute |
| Regional | Highest | Mission-critical, HA required |
| Enterprise | Premium | GKE workloads, multishares |

**Cost Optimization**:

- Right-size capacity: Monitor used space %, resize if underutilized
- Use BASIC_HDD for non-production workloads
- Delete stale backups and snapshots
- Use regional instances only when HA required
- Monitor backups quota usage (billable)
- Consider instance replication instead of frequent backups for DR

**Billable Resources**:

| Resource | Billing Unit |
|----------|--------------|
| Provisioned capacity | GiB/hour |
| Backups | GiB/month |
| Snapshot storage | GiB/month |
| Egress traffic | GiB |

## §4 Efficiency

- **Tier selection**: Match tier to workload (BASIC_HDD for dev, Regional for prod)
- **Capacity planning**: Monitor free raw capacity %, scale proactively
- **File share naming**: Use descriptive names (e.g., `app-data`, `logs`)
- **Network topology**: Co-locate Filestore in same VPC as clients
- **NFS protocol**: Use NFSv4.1 for auth and in-transit encryption
- **Labels**: Add labels for cost tracking (`env`, `app`, `team`, `project`)
- **Performance tuning**: Use custom performance for Zonal/Regional tiers

**Efficiency Best Practices**:

- Enable custom performance to scale IOPS independently of capacity
- Use appropriate capacity increments (256 GiB for Zonal, 1 GiB for BASIC)
- Monitor inode usage (`df -i`) to prevent running out of inodes
- Delete unused files/shares to free inodes

## §5 Performance

| Tier | Performance | Tuning |
|------|-------------|--------|
| BASIC_HDD | Standard fixed | Cannot tune |
| BASIC_SSD | Premium fixed | Cannot tune |
| Zonal (1-9.75 TiB) | Configurable | Set max-iops, max-throughput-mibps |
| Zonal (10-100 TiB) | Configurable | Set max-iops, max-throughput-mibps |
| Regional | Configurable | Set max-iops, max-throughput-mibps |
| Enterprise | Scales with capacity | Automatic |

**Performance Optimization**:

- Use custom performance for Zonal/Regional tiers
- Scale IOPS with capacity: 100 connections per 1000 purchased IOPS
- Monitor latency: Alert if avg read/write latency >10ms
- Use NFSv4.1 for better performance with Kerberos
- Co-locate with compute (same zone for Zonal, same region for Regional)
- Tune NFS client mount options (`rsize`, `wsize`, `hard`, `intr`)

**Performance Metrics to Monitor**:

- Average read/write latency (target <10ms)
- Disk read/write operation count (IOPS)
- Bytes read/written (throughput)
- Metadata operations count
