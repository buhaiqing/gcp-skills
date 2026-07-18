# Reschedule Maintenance — Google Cloud SQL

> Provides database administrators with a complete runbook for rescheduling Cloud SQL maintenance operations — understanding in-place vs blue-green maintenance, configuring maintenance windows, and verification procedures.

## Table of Contents

1. [Overview](#overview)
2. [Maintenance Types](#maintenance-types)
3. [Pre-flight Checks](#pre-flight-checks)
4. [Maintenance Window Configuration](#maintenance-window-configuration)
5. [Reschedule Operation](#reschedule-operation)
6. [In-Place vs Blue-Green](#in-place-vs-blue-green)
7. [Verification](#verification)
8. [Failure Scenarios](#failure-scenarios)
9. [See Also](#see-also)

## Overview

Cloud SQL performs periodic maintenance that may include minor version updates, security patches, and infrastructure improvements. By default, maintenance occurs during your region's maintenance window with some randomization.

| Maintenance Type | Frequency | Downtime | Notice |
|-----------------|-----------|----------|--------|
| Minor version update | ~Quarterly | 0-30 sec (in-place) | 7 days |
| Major version upgrade | ~Yearly | 30-60 sec (blue-green) | 30 days |
| Security patch | As needed | 0-30 sec (in-place) | 3-7 days |

### Maintenance Scheduling Options

| Option | Description | Use Case |
|--------|-------------|-----------|
| Default | Google-assigned window | Development/test |
| Custom window | User-specified day/hour | Production with defined maintenance windows |
| Deferral | Postpone up to 30 days | Business-critical periods |

## Maintenance Types

### In-Place Maintenance

- Engine version stays the same
- Rolling update with brief connection interruption (~30 seconds)
- No new IP addresses or topology changes
- Application should implement retry logic

### Blue-Green Maintenance

- Creates new instance with updated version
- Brief cutover (30-60 seconds)
- IP address may change (or use DNS for stable endpoint)
- More resilient for critical workloads

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       In-Place Maintenance                              │
│                                                                          │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐  │
│  │   Old Version   │────►│  Rolling Update │────►│   New Version   │  │
│  │   (Running)     │     │  (~30 sec I/O)  │     │   (Running)      │  │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘  │
│                                                                          │
│                       Blue-Green Maintenance                             │
│                                                                          │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐  │
│  │   Old Version   │     │   New Version   │     │   Cutover       │  │
│  │   (Running)     │────►│   (Standby)     │────►│   (~60 sec)     │  │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘  │
│                                │                       │                 │
│                                │                 ┌─────▼─────┐          │
│                                │                 │  Delete   │          │
│                                │                 │  Old Ver. │          │
│                                │                 └───────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Pre-flight Checks

### 1. Check Current Maintenance Configuration

```bash
# Get current maintenance settings
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
    maintenanceWindow: .settings.maintenanceWindow,
    databaseFlags: .settings.databaseFlags,
    version: .databaseVersion
  }'
```

### 2. Check Scheduled Maintenance

```bash
# List any pending maintenance
gcloud sql instances list --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.[] | {
    name: .name,
    pendingMaintenance: .pendingMaintenance,
    updateTime: .updateTime
  }'

# Check for maintenance announcements
gcloud sql operations list --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="operationType=MAINTENANCE" \
  --format="table(name,startTime,status)"
```

### 3. Verify Application Resilience

```bash
# Test application connection retry logic
for i in {1..5}; do
  mysql -h "{{user.instance_name}}" \
    -u "{{user.user_name}}" \
    -p"{{env.MYSQL_PASSWORD}}" \
    -e "SELECT 1" 2>/dev/null && echo "Connection $i: OK" || echo "Connection $i: FAILED"
  sleep 2
done

# Verify connection pool can handle brief disconnection
# Check max_connections setting
gcloud sql connect "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database="{{user.database_name}}" \
  --execute="SHOW VARIABLES LIKE 'max_connections';" 2>/dev/null
```

## Maintenance Window Configuration

### View Available Update Preferences

```bash
# List available update preferences for your instance
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.availableMaintenanceVersions'

# Get instance region to determine maintenance window
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="value(region)"
```

### Configure Maintenance Window

```bash
# Set preferred maintenance window (Sunday 03:00-07:00 in instance timezone)
gcloud sql instances patch "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --maintenance-window-day="sunday" \
  --maintenance-window-hour="03" \
  --maintenance-window-start-hour="03" \
  --maintenance-window-end-hour="07" \
  --format=json

# Alternative: Allow Google to schedule (removes custom window)
gcloud sql instances patch "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --remove-maintenance-window \
  --format=json
```

### Set Update Preference

```bash
# Set to prefer in-place updates (faster, less disruptive)
gcloud sql instances patch "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --update-preference=in-place \
  --format=json

# Or prefer blue-green updates (more resilient)
gcloud sql instances patch "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --update-preference=blue-green \
  --format=json
```

## Reschedule Operation

### Step 1: Check Reschedule Options

```bash
# Get current maintenance schedule
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
    scheduledMaintenance: .scheduledMaintenance,
    maintenanceWindow: .settings.maintenanceWindow
  }'
```

### Step 2: Reschedule Maintenance

```bash
# Defer maintenance (postpone for a specified number of days, max 30)
gcloud sql instances reschedule-maintenance "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --reschedule-type=POSTPONE \
  --postpone-duration="{{user.postpone_days}}d" \
  --format=json

# Or: Schedule at specific time within current window
gcloud sql instances reschedule-maintenance "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --reschedule-type=SCHEDULE_NEXT_WINDOW \
  --format=json
```

### Step 3: Verify Reschedule

```bash
# Check updated maintenance schedule
sleep 5
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
    scheduledMaintenance: .scheduledMaintenance,
    maintenanceWindow: .settings.maintenanceWindow
  }'
```

### Cancel Reschedule (Revert)

```bash
# If you need to revert to original schedule
gcloud sql instances reschedule-maintenance "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --reschedule-type=SCHEDULE_NEXT_WINDOW \
  --format=json
```

## In-Place vs Blue-Green

### When to Choose In-Place

| Factor | In-Place | Blue-Green |
|--------|----------|------------|
| Downtime tolerance | < 30 sec | < 60 sec |
| IP address stability | Preserved | May change |
| Risk tolerance | Lower | Higher |
| Cost | Lower (no extra instance) | Higher (dual running) |
| Rollback complexity | Automatic rollback | Manual intervention |

### In-Place Maintenance

```bash
# No special preparation needed for in-place
# Ensure application has connection retry logic
# Verify instance has deletion protection enabled
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.deletionProtection'
```

### Blue-Green Maintenance

```bash
# Blue-green creates a new instance - prepare for IP change
# Get current IP for reference
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="value(ipAddresses[0].ipAddress)"

# If using private IP, verify VPC peering is ready
gcloud compute networks peerings list \
  --network="{{user.vpc_network}}" \
  --format="json" | jq '.[] | {name: .name, state: .state}'

# Ensure DNS alias is configured for stable endpoint
# Update DNS to point to instance name, not IP
```

## Verification

### Verify Maintenance Settings

```bash
# Confirm updated maintenance window
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
    maintenanceWindow: .settings.maintenanceWindow,
    updatePreference: .settings.updatePreference
  }'
```

### Verify Application Resilience

```bash
# Test database connectivity
gcloud sql connect "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database="{{user.database_name}}" \
  --execute="SELECT 1 AS test;" 2>/dev/null && echo "Database: OK"

# Verify application health
curl -s "https://{{user.app_endpoint}}/health" | jq '.database'

# Run load test to verify connection handling
for i in {1..10}; do
  (mysql -h "{{user.instance_name}}" \
    -u "{{user.user_name}}" \
    -p"{{env.MYSQL_PASSWORD}}" \
    -e "SELECT 1" 2>/dev/null || echo "FAIL") &
done
wait
echo "Connection test complete"
```

### Post-Maintenance Verification

```bash
# Verify instance is RUNNABLE after maintenance
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name: .name, state: .state, version: .databaseVersion}'

# Verify no pending maintenance
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.scheduledMaintenance'

# Check for any maintenance-related operations
gcloud sql operations list --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="operationType=MAINTENANCE" \
  --limit=5 --format="table(name,startTime,status)"
```

## Failure Scenarios

| Scenario | Symptom | Resolution |
|----------|---------|------------|
| Maintenance window conflict | 400/INVALID_ARGUMENT | Choose different day/hour |
| Instance not ready | 409/INSTANCE_NOT_READY | Wait for instance to be RUNNABLE |
| Reschedule limit reached | 400/MAX_RESCHEDULES_EXCEEDED | Cannot reschedule further |
| Maintenance during business hours | Disruption | Reschedule to off-hours |

### Recovery Procedures

```bash
# If maintenance causes issues, check operation status
gcloud sql operations list --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="operationType=MAINTENANCE OR operationType=UPDATE" \
  --limit=5 --format="table(name,operationType,startTime,status)"

# Check instance state
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{state: .state, status: .state}'

# If instance is unhealthy, restart
gcloud sql instances restart "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json
```

## See Also

- [Cloud SQL High Availability](../high-availability.md)
- [Cloud SQL Monitoring](../monitoring.md)
- [Cloud SQL Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud SQL Maintenance Documentation](https://cloud.google.com/sql/docs/mysql/maintenance)
