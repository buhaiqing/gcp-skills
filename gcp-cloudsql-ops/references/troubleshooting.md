# Troubleshooting — Cloud SQL

## Error Codes

| gRPC/HTTP | Meaning | Agent Action |
|-----------|---------|--------------|
| INVALID_ARGUMENT / 400 | Request validation failed | Fix parameter per API |
| PERMISSION_DENIED / 403 | Insufficient IAM | Grant cloudsql.admin or cloudsql.client |
| NOT_FOUND / 404 | Resource not found | Verify instance name, backup ID, database name |
| ALREADY_EXISTS / 409 | Duplicate name | Choose unique instance/database/user name |
| QUOTA_EXCEEDED / 429 | Quota limit | Request increase |
| INTERNAL / 500 | Server error | Retry, then escalate |
| UNAVAILABLE / 503 | Service unavailable | Retry with backoff |
| FAILED_PRECONDITION | Wrong instance state | Wait for RUNNABLE state |
| ABORTED | Operation conflict | Retry after completion |
| RESOURCE_EXHAUSTED | Too many concurrent ops | Reduce concurrency |
| BILLING_NOT_ENABLED | Billing inactive | Enable in Cloud Console |
| INVALID_TIER | Tier not available | List available tiers for region |
| INVALID_DB_VERSION | DB version not supported | Check supported versions |
| INVALID_STORAGE_SIZE | Disk size out of range | Use 10GB-30720GB range |
| STORAGE_FULL | Instance storage exhausted | Resize storage or free space |
| REPLICA_FAILED | Replication broken | Check logs, skip/restart replication |
| RESTORE_FAILED | Backup restore error | Verify backup integrity, retry |
| BACKUP_FAILED | Backup operation failed | Check storage, retry |
| EXPORT_FAILED | Export to GCS failed | Check bucket permissions, file size |
| IMPORT_FAILED | Import from GCS failed | Check file format, schema compatibility |

## Diagnostic Order

1. Describe instance: `gcloud sql instances describe NAME --format=json`
2. List operations: `gcloud sql operations list --instance=NAME --format=json`
3. Check backup status: `gcloud sql backups list --instance=NAME --format=json`
4. Check flags: `gcloud sql instances describe NAME --format=json | jq '.settings.databaseFlags'`
5. Check Query Insights (if enabled): `gcloud sql instances describe NAME --format=json | jq '.settings.insightsConfig'`
6. Check Cloud Logging: `resource.type="cloudsql_database"`
7. Test connectivity: `gcloud sql connect NAME --user=USER --quiet`

## Common Issues

### Connection Refused
- **Firewall**: Check authorized networks allow your IP
- **SSL**: Verify SSL cert if enforced (`gcloud sql instances describe NAME | jq '.settings.ipConfiguration.requireSsl'`)
- **Instance state**: Verify `gcloud sql instances describe` shows `state: RUNNABLE`
- **Private IP**: Ensure client is in same VPC / peering

### Instance Won't Start
- **Storage full**: Resize or delete data
- **Maintenance**: Check `gcloud sql operations list`
- **Flag misconfiguration**: Remove invalid flags
- **Quota exhausted**: Request increase

### Backup Failed
- **Storage quota**: Check project-level quota
- **Instance not RUNNABLE**: Restart instance
- **Concurrent backup**: Wait for running backup to complete
- **Table-level corruption**: Check `mysqlcheck` / `pg_repack`

### Replication Lag
```bash
# Check replica status (MySQL)
gcloud sql instances describe REPLICA --format="json" | jq '.replicaConfiguration'

# Check replica status (PostgreSQL)
gcloud sql instances describe REPLICA --format="json" | jq '.replicaConfiguration'

# Promote replica if lag critical
gcloud sql instances promote-replica REPLICA
```

### Storage Full
```bash
# Check current storage
gcloud sql instances describe NAME --format="json" | jq '{name, state, settings: {dataDiskSizeGb, storageAutoResize}}'

# Resize storage
gcloud sql instances patch NAME --storage-size=NEW_SIZE_GB
```

### Query Performance Issues
```bash
# Enable Query Insights for diagnostics
gcloud sql instances patch NAME \
  --insights-config-query-insights-enabled \
  --insights-config-record-application-tags \
  --insights-config-record-client-address

# Check slow queries via Cloud Monitoring
# Use the Query Insights dashboard in Cloud Console
```

### Password Reset
```bash
# Never use -p flag; use env var for local client
# For MySQL:
MYSQL_PWD="new_password" mysql -u USER -h INSTANCE_IP -e "SELECT 1"

# For PostgreSQL:
PGPASSWORD="new_password" psql -U USER -h INSTANCE_IP -d DB -c "SELECT 1"

# Reset via gcloud:
gcloud sql users set-password USER --instance=NAME --password=NEW_PASSWORD
```