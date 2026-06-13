# Backup for GKE — Execution Flow

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Backup Plan Operations](#backup-plan-operations)
- [Backup and Restore Operations](#backup-and-restore-operations)
- [Restore Operations](#restore-operations)
- [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

Backup for GKE provides native backup and restore capabilities for GKE clusters, including PV data, workloads, and cluster configurations. This guide covers the complete execution flow for managing backups.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Backup for GKE Architecture                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  GKE        │    │  Backup     │    │  GCS        │        │
│  │  Cluster    │◄──►│  Plan       │◄──►│  Bucket     │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Workloads  │    │  Backup     │    │  Backup     │        │
│  │  + PVs      │    │  CRDs       │    │  Artifacts  │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# Enable Backup for GKE API
gcloud services enable gkebackup.googleapis.com

# Verify API enabled
gcloud services list --enabled | grep gkebackup

# Required IAM roles
# - roles/gkebackup.admin (full management)
# - roles/gkebackup.viewer (read-only)
# - roles/gkebackup.agentBackup (backup agent on cluster)
# - roles/gkebackup.agentRestore (restore agent on cluster)
```

## Backup Plan Operations

### Create Backup Plan

```bash
# Create backup plan for a cluster
gcloud container backup-protection backup-plans create BACKUP_PLAN_NAME \
  --cluster=CLUSTER_NAME \
  --location=LOCATION \
  --retention-policy-days=RETENTION_DAYS \
  --backup-schedule="CRON_SCHEDULE"

# Example: Daily backup with 30-day retention
gcloud container backup-protection backup-plans create daily-backup \
  --cluster=my-cluster \
  --location=us-central1 \
  --retention-policy-days=30 \
  --backup-schedule="0 2 * * *"
```

### List Backup Plans

```bash
# List all backup plans in a location
gcloud container backup-protection backup-plans list \
  --location=LOCATION

# Describe a specific backup plan
gcloud container backup-protection backup-plans describe BACKUP_PLAN_NAME \
  --location=LOCATION
```

### Update Backup Plan

```bash
# Update retention policy
gcloud container backup-protection backup-plans update BACKUP_PLAN_NAME \
  --location=LOCATION \
  --retention-policy-days=60
```

## Backup and Restore Operations

### Create On-Demand Backup

```bash
# Create a backup using existing backup plan
gcloud container backup-protection backups create BACKUP_NAME \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION

# Example: Create immediate backup
gcloud container backup-protection backups create manual-backup-$(date +%Y%m%d) \
  --backup-plan=daily-backup \
  --location=us-central1
```

### List Backups

```bash
# List all backups for a backup plan
gcloud container backup-protection backups list \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION

# Describe a specific backup
gcloud container backup-protection backups describe BACKUP_NAME \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION
```

### View Backup Details

```bash
# Get backup with JSON output
gcloud container backup-protection backups describe BACKUP_NAME \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION \
  --format=json

# Check backup state
gcloud container backup-protection backups describe BACKUP_NAME \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION \
  --format="value(state)"
```

## Restore Operations

### Create Restore

```bash
# Create restore from a backup
gcloud container backup-protection restores create RESTORE_NAME \
  --backup=BACKUP_NAME \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION \
  --target-cluster=TARGET_CLUSTER

# Example: Restore to same cluster
gcloud container backup-protection restores create restore-$(date +%Y%m%d) \
  --backup=daily-backup-20260613 \
  --backup-plan=daily-backup \
  --location=us-central1 \
  --target-cluster=my-cluster
```

### Restore Options

```bash
# Restore with namespace mapping
gcloud container backup-protection restores create RESTORE_NAME \
  --backup=BACKUP_NAME \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION \
  --target-cluster=TARGET_CLUSTER \
  --namespace-name-mapping=OLD_NS:NEW_NS

# Restore with name mapping
gcloud container backup-protection restores create RESTORE_NAME \
  --backup=BACKUP_NAME \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION \
  --target-cluster=TARGET_CLUSTER \
  --name-replacement=OLD_NAME:NEW_NAME
```

### List Restores

```bash
# List all restores
gcloud container backup-protection restores list \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION

# Describe a restore
gcloud container backup-protection restores describe RESTORE_NAME \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION
```

## Monitoring and Troubleshooting

### Check Backup Status

```bash
# Get backup state
gcloud container backup-protection backups describe BACKUP_NAME \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION \
  --format="value(state)"

# States: CREATING, SUCCEEDED, FAILED, DELETING, DELETED
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Backup stuck in CREATING | Large PV data or network issues | Check cluster connectivity; verify GCS bucket access |
| Backup failed | Insufficient permissions | Verify backup agent IAM roles |
| Restore failed | Namespace conflict | Use namespace mapping to avoid conflicts |
| Backup not scheduled | Invalid cron expression | Validate cron format: `MIN HOUR DOM MON DOW` |

### View Operations

```bash
# List operations for backup plan
gcloud container backup-protection operations list \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION

# Describe specific operation
gcloud container backup-protection operations describe OPERATION_NAME \
  --backup-plan=BACKUP_PLAN_NAME \
  --location=LOCATION
```

## Best Practices

1. **Retention Policy**: Set appropriate retention based on compliance requirements
2. **Scheduling**: Use off-peak hours for scheduled backups
3. **Testing**: Regularly test restores to validate backup integrity
4. **Monitoring**: Set up alerts for backup failures
5. **Cross-Region**: Consider cross-region backup plans for DR scenarios
6. **PV Selection**: Use backup resource selectors to include/exclude specific PVs
7. **Labels**: Apply labels for cost tracking and organization

## See Also

- [GKE Backup Documentation](https://cloud.google.com/kubernetes-engine/docs/backup)
- [Backup for GKE API Reference](https://cloud.google.com/gke-backup/docs/reference/rest)
