# Point-in-Time Recovery and Clone Operations — Google Cloud SQL

> Provides database administrators with a complete guide to performing point-in-time recovery (PITR) and clone operations on Google Cloud SQL instances — including binary log (MySQL) and WAL (PostgreSQL) based recovery, cross-region considerations, and verification steps.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Point-in-Time Recovery (PITR)](#point-in-time-recovery-pitr)
4. [Clone Instance](#clone-instance)
5. [Cross-Region PITR](#cross-region-pitr)
6. [Verification](#verification)
7. [Failure Scenarios](#failure-scenarios)
8. [See Also](#see-also)

## Overview

Cloud SQL supports point-in-time recovery (PITR) for MySQL and PostgreSQL instances:

| DB Engine | PITR Method | Recovery Window | Retention |
|-----------|-------------|-----------------|-----------|
| MySQL | Binary logs | 7 days | Based on backup retention |
| PostgreSQL | WAL archive | 7 days | Based on backup retention |

PITR creates a new instance with data recovered to the specified timestamp. The original instance remains unchanged.

### Use Cases

| Scenario | Operation | RTO | RPO |
|----------|-----------|-----|-----|
| Accidental data deletion | PITR to before deletion | ~15-30 min | < 1 min |
| Failed migration rollback | PITR to before migration | ~15-30 min | < 1 min |
| Test environment from prod | Clone | ~10-15 min | Zero |
| Disaster recovery | PITR cross-region | ~30-45 min | < 1 min |

## Prerequisites

```bash
# 1. Verify PITR is enabled
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{pitrEnabled: .settings.backupConfiguration.pointInTimeRecoveryEnabled, backupStartTime: .settings.backupConfiguration.startTime}'

# 2. Verify binary logging (MySQL) or WAL (PostgreSQL)
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.settings.backupConfiguration'

# 3. List recent backups (PITR uses these as base)
gcloud sql backups list --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="status=SUCCESSFUL" --limit=5
```

## Point-in-Time Recovery (PITR)

### Pre-flight Check

```bash
# Verify instance is RUNNABLE and PITR is enabled
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{state: .state, pitrEnabled: .settings.backupConfiguration.pointInTimeRecoveryEnabled}'
```

### Execute PITR (MySQL)

```bash
# PITR to specific timestamp (MySQL)
# Timestamp must be after the latest backup and before current time
gcloud sql instances restore-point-in-time "{{user.pitr_instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --restore-instance="{{user.instance_name}}" \
  --point-in-time="{{user.pitr_timestamp}}" \
  --format=json

# Example: Restore to 2026-01-15 14:30:00 UTC
gcloud sql instances restore-point-in-time "restored-instance" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --restore-instance="my-mysql-instance" \
  --point-in-time="2026-01-15T14:30:00Z" \
  --format=json
```

### Execute PITR (PostgreSQL)

```bash
# PostgreSQL PITR uses the same command structure
gcloud sql instances restore-point-in-time "{{user.pitr_instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --restore-instance="{{user.instance_name}}" \
  --point-in-time="{{user.pitr_timestamp}}" \
  --format=json
```

### Clone Instance (Latest State)

```bash
# Clone creates an instance with data at clone time (not PITR)
gcloud sql instances clone "{{user.clone_instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --source-instance="{{user.instance_name}}" \
  --format=json
```

### Clone with PITR

```bash
# Clone to a point-in-time (creates clone, then applies PITR)
gcloud sql instances create "{{user.clone_instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --clone-context-source-instance="{{user.instance_name}}" \
  --clone-context-point-in-time="{{user.pitr_timestamp}}" \
  --region="{{user.region}}" \
  --tier="{{user.tier}}" \
  --format=json
```

### Validate PITR

```bash
# Poll operation until DONE
OPERATION_ID=$(gcloud sql instances restore-point-in-time ... --format=json | jq -r '.name')
gcloud sql operations describe "$OPERATION_ID" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{status: .status, progress: .progress}'

# Verify new instance is RUNNABLE
sleep 30
gcloud sql instances describe "{{user.pitr_instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name: .name, state: .state, region: .region}'
```

| Error | Action |
|-------|--------|
| 400/INVALID_ARGUMENT | Timestamp format invalid or before backup window |
| 404/NOT_FOUND | Source instance not found |
| 409/ALREADY_EXISTS | Target instance name already exists |
| 412/FAILED_PRECONDITION | PITR not enabled on source instance |

## Cross-Region PITR

### Cross-Region Considerations

```bash
# Check if instance supports cross-region PITR
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{region: .region, availableRegions: .availableRegions}'

# List backup runs with their locations
gcloud sql backups list --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.[] | {id: .id, location: .location, status: .status}'
```

### Cross-Region PITR Execution

```bash
# Create PITR instance in different region
gcloud sql instances restore-point-in-time "{{user.pitr_instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --restore-instance="{{user.instance_name}}" \
  --point-in-time="{{user.pitr_timestamp}}" \
  --region="{{user.cross_region}}" \
  --format=json

# Note: Cross-region PITR requires backup to be accessible in target region
# or may require copying backup to target region first
```

### Network Configuration for Cross-Region

```bash
# If using private IP, ensure VPC peering or interconnect is configured
gcloud compute networks peering list --format="json" | jq '.[] | {name: .name, network: .network}'

# Check if private IP is configured
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.ipAddresses'
```

## Verification

### Instance Health Check

```bash
# Verify instance state
gcloud sql instances describe "{{user.pitr_instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name: .name, state: .state, version: .databaseVersion}'

# Verify data integrity - check table count
gcloud sql connect "{{user.pitr_instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database="{{user.database_name}}" \
  --execute="SELECT COUNT(*) FROM information_schema.tables;" 2>/dev/null
```

### PITR Timestamp Verification

```bash
# Verify recovered data matches PITR timestamp
gcloud sql connect "{{user.pitr_instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database="{{user.database_name}}" \
  --execute="SELECT MAX(updated_at) FROM {{user.table_name}};" 2>/dev/null

# Compare with expected timestamp
echo "Expected: {{user.pitr_timestamp}}"
```

### Application Connectivity

```bash
# Test application connection
curl -s "https://{{user.app_endpoint}}/health" | jq '.database'

# Verify connection pool status
gcloud sql instances describe "{{user.pitr_instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.settings.ipConfiguration'
```

## Failure Scenarios

| Scenario | Symptom | Resolution |
|----------|---------|------------|
| PITR timestamp too old | 400/INVALID_ARGUMENT | Timestamp must be within retention window (7 days) |
| PITR not enabled | 412/FAILED_PRECONDITION | Enable PITR via backup configuration |
| Backup corruption | RESTORE_FAILED | Use earlier backup as base, or restore from previous backup |
| Cross-region network issue | 403/PERMISSION_DENIED | Configure VPC peering or use public IP temporarily |
| Insufficient quota | 429/QUOTA_EXCEEDED | Increase project quota or use smaller instance tier |
| Disk space issue | 500/INTERNAL_ERROR | Increase storage size before PITR |

### Recovery Procedures

```bash
# If PITR fails, diagnose with operation error
gcloud sql operations describe "$OPERATION_ID" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.error'

# List available backups for manual restore
gcloud sql backups list --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="status=SUCCESSFUL" --format="table(id,description,enqueuedTime)"

# Manual backup restore as fallback
gcloud sql backups restore "$BACKUP_ID" \
  --restore-instance="{{user.backup_instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## See Also

- [Cloud SQL Backup and Recovery](../backup-recovery.md)
- [Cloud SQL High Availability](../high-availability.md)
- [Cloud SQL Monitoring](../monitoring.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud SQL PITR Documentation](https://cloud.google.com/sql/docs/mysql/point-in-time-recovery)
