# Cloud Filestore — Operational Best Practices

## Tier Selection

| Tier | Use Case |
|------|----------|
| BASIC_HDD | Infrequently accessed data |
| BASIC_SSD | General purpose workloads |
| HIGH_SCALE_SSD | High performance (scale-out) |
| ENTERPRISE | Mission-critical workloads, replication |

## Capacity Planning

- Monitor usage via `used_bytes` metric
- Set alerts at 80% capacity utilization
- Increase capacity before hitting limits (update operation)

## Security

- Use VPC-private connectivity (not public IP)
- Restrict NFS access with firewall rules (`gcloud compute firewall-rules`)
- Use IAM roles (roles/file.editor, roles/file.viewer)
- Enable VPC Service Controls for sensitive data

## Backup and Snapshot Strategy

- Schedule regular backups for critical data
- Test restore procedures periodically
- Use snapshots for point-in-time recovery
- Manage snapshot lifecycle (delete old snapshots)

## Monitoring

- Set alerts for:
  - Capacity usage (> 80%)
  - Instance state (not RUNNING)
  - Backup failures
- Use Cloud Monitoring dashboards (see `references/monitoring.md`)

## Naming Convention

Follow `{env}-{app}-filestore` convention for instance names:
- `prod-app-filestore`
- `staging-analytics-filestore`
- `dev-test-filestore`
