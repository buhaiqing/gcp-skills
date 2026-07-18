# Cross-Region Replica Failover — Google Cloud SQL

> Provides database administrators with a complete runbook for cross-region replica failover operations — promoting cross-region replicas to primary, managing DNS TTL updates, application reconnection patterns, and verification procedures.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Pre-flight Checks](#pre-flight-checks)
4. [Failover Operation](#failover-operation)
5. [DNS and Connectivity](#dns-and-connectivity)
6. [Application Reconnection](#application-reconnection)
7. [Post-Failover Verification](#post-failover-verification)
8. [Failure Scenarios](#failure-scenarios)
9. [Rollback Procedures](#rollback-procedures)
10. [See Also](#see-also)

## Overview

Cross-region failover provides disaster recovery by maintaining a replica in a different region. When the primary fails, you promote the replica to become the new primary.

| Component | Primary | Replica |
|-----------|---------|---------|
| Region | us-central1 | us-east1 |
| Instance Type | High availability | Standard replica |
| Data Lag | N/A | Near real-time |

### Failover Types

| Type | RTO | RPO | Use Case |
|------|-----|-----|----------|
| Planned switchover | ~5-10 min | Zero | Regional maintenance |
| Emergency failover | ~10-15 min | < 1 min | Primary region outage |
| Failback | ~20-30 min | Varies | Returning to primary region |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Cross-Region Failover                             │
│                                                                          │
│  ┌─────────────────────────┐         ┌─────────────────────────┐      │
│  │      Primary Region      │         │     Replica Region       │      │
│  │       (us-central1)      │         │       (us-east1)        │      │
│  │                          │         │                         │      │
│  │  ┌─────────────────┐    │         │  ┌─────────────────┐    │      │
│  │  │   Primary DB    │◄───┼─────────┼──│  Cross-Region   │    │      │
│  │  │   (Primary)     │    │  Async  │  │    Replica     │    │      │
│  │  └─────────────────┘    │  Rep.   │  └────────┬────────┘    │      │
│  │           │             │         │           │             │      │
│  │           │ DNS         │         │           │ Promote     │      │
│  │           ▼             │         │           ▼             │      │
│  │  ┌─────────────────┐    │         │  ┌─────────────────┐    │      │
│  │  │  Cloud DNS      │    │         │  │  New Primary   │    │      │
│  │  │  (Low TTL)      │    │         │  │  (Promoted)    │    │      │
│  │  └─────────────────┘    │         │  └─────────────────┘    │      │
│  └─────────────────────────┘         └─────────────────────────┘      │
│                                                                      │
│                         Application Tier                               │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │  │
│  │  │  App Server  │  │  App Server  │  │  App Server  │         │  │
│  │  │     #1       │  │     #2       │  │     #3       │         │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Pre-flight Checks

### 1. Verify Replica Status

```bash
# Check replica health and replication lag
gcloud sql instances describe "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
    name: .name,
    state: .state,
    region: .region,
    masterInstanceName: .masterInstanceName,
    replicaConfiguration: .replicaConfiguration,
    settings: .settings.availabilityType
  }'
```

### 2. Check Replication Lag

```bash
# MySQL: Check replication status
gcloud sql connect "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database="mysql" \
  --execute="SHOW SLAVE STATUS\G" 2>/dev/null | grep -E "Seconds_Behind_Master|Slave_IO_Running|Slave_SQL_Running"

# PostgreSQL: Check replication slot
gcloud sql connect "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database="postgres" \
  --execute="SELECT * FROM pg_stat_replication;" 2>/dev/null
```

### 3. Verify Data Freshness

```bash
# Check latest transaction timestamp
gcloud sql connect "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database="{{user.database_name}}" \
  --execute="SELECT MAX(updated_at) as latest_update FROM {{user.table_name}};" 2>/dev/null

# Compare with primary
gcloud sql connect "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database="{{user.database_name}}" \
  --execute="SELECT MAX(updated_at) as latest_update FROM {{user.table_name}};" 2>/dev/null
```

### 4. DNS TTL Check

```bash
# Check current DNS TTL on Cloud DNS
gcloud dns managed-zones describe "{{user.dns_zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{dnsName: .dnsName, dnssecConfig: .dnssecConfig}'

# Verify low TTL is set (should be 60 seconds or less for failover)
dig +short "{{user.db_hostname}}" || nslookup "{{user.db_hostname}}"
```

## Failover Operation

### Step 1: Stop Applications

```bash
# Scale down application servers (Kubernetes example)
kubectl scale deployment/{{user.app_deployment}} --replicas=0

# Or for direct connection: stop application services
sudo systemctl stop "{{user.app_service}}"
```

### Step 2: Verify Zero Replication Lag

```bash
# Wait until lag is zero before promoting
while true; do
  LAG=$(gcloud sql connect "{{user.replica_name}}" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --database="mysql" \
    --execute="SHOW SLAVE STATUS\G" 2>/dev/null | grep "Seconds_Behind_Master" | awk '{print $2}')

  if [ "$LAG" = "0" ] || [ "$LAG" = "NULL" ]; then
    echo "Replication lag: $LAG - Safe to promote"
    break
  fi
  echo "Replication lag: $LAG seconds - Waiting..."
  sleep 10
done
```

### Step 3: Promote Replica

```bash
# Promote cross-region replica to standalone instance
gcloud sql instances promote-replica "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json

# Capture operation ID
OPERATION_ID=$(gcloud sql instances promote-replica "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq -r '.name')

echo "Promotion operation: $OPERATION_ID"
```

### Step 4: Wait for Promotion Complete

```bash
# Poll operation status
gcloud sql operations describe "$OPERATION_ID" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{status: .status, progress: .progress}'

# Verify replica is now standalone
sleep 30
gcloud sql instances describe "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name: .name, state: .state, masterInstanceName: .masterInstanceName}'
```

## DNS and Connectivity

### Update DNS Records

```bash
# Update DNS A record to point to new primary IP
gcloud dns record-sets transaction start --zone="{{user.dns_zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Get new primary IP
NEW_PRIMARY_IP=$(gcloud sql instances describe "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="value(ipAddresses[0].ipAddress)")

# Delete old A record
gcloud dns record-sets transaction remove \
  --zone="{{user.dns_zone}}" \
  --name="{{user.db_hostname}}" \
  --type=A \
  --ttl=60 \
  --old-ip-address="{{user.old_primary_ip}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Add new A record
gcloud dns record-sets transaction add "$NEW_PRIMARY_IP" \
  --zone="{{user.dns_zone}}" \
  --name="{{user.db_hostname}}" \
  --type=A \
  --ttl=60 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Execute transaction
gcloud dns record-sets transaction execute --zone="{{user.dns_zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Verify DNS Propagation

```bash
# Wait for TTL and verify new IP
sleep 65
dig +short "{{user.db_hostname}}"
nslookup "{{user.db_hostname}}"
```

### Update Security Groups / Firewall

```bash
# Update authorized networks if using IP-based access
gcloud sql instances describe "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.ipConfiguration.authorizedNetworks'

# Add new region IP ranges if needed
gcloud sql instances patch "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --authorized-networks="{{user.network_cidr}}" \
  --format=json
```

## Application Reconnection

### Connection String Update

```bash
# Update application database connection string
# Replace old primary hostname with new primary hostname
export DATABASE_HOST="{{user.db_hostname}}"
export DATABASE_PORT="{{user.db_port}}"

# For Kubernetes: update Secret
kubectl patch secret db-credentials \
  --namespace="{{user.namespace}}" \
  --type=opaque \
  --patch='{"data":{"host":"'$(echo -n "$DATABASE_HOST" | base64)'"}}'
```

### Application Restart

```bash
# Restart application servers to pick up new connection
kubectl rollout restart deployment/{{user.app_deployment}} \
  --namespace="{{user.namespace}}"

# Verify rollout completes
kubectl rollout status deployment/{{user.app_deployment}} \
  --namespace="{{user.namespace}}"
```

### Connection Pool Flush

```bash
# If using PgBouncer or ProxySQL, flush connection pools
# PgBouncer
echo "FLUSH POOLS;" | psql -h "{{user.db_hostname}}" -U "{{user.db_user}}"

# ProxySQL
mysql -h "{{user.proxy_host}}" -u "{{user.proxy_user}}" -p -e \
  "LOAD SCHEDULES TO RUNTIME; SELECT * FROM stats_mysql_connection_pool;"
```

## Post-Failover Verification

### Instance Health

```bash
# Verify promoted instance is RUNNABLE
gcloud sql instances describe "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name: .name, state: .state, region: .region, ipAddresses: .ipAddresses}'
```

### Data Integrity

```bash
# Verify row counts match expected
gcloud sql connect "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database="{{user.database_name}}" \
  --execute="SELECT COUNT(*) FROM {{user.table_name}};" 2>/dev/null

# Verify no replication-related errors
gcloud sql instances list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="table(name,state,region)"
```

### Application Health

```bash
# Test application database connectivity
curl -s "https://{{user.app_endpoint}}/health" | jq '.database'

# Check application logs for connection errors
kubectl logs deployment/{{user.app_deployment}} \
  --namespace="{{user.namespace}}" \
  --since=5m | grep -i "database\|connection\|error" | tail -20
```

### Replication Setup (for future failback)

```bash
# Create new cross-region replica from promoted instance
gcloud sql instances create "{{user.new_replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.primary_region}}" \
  --master-instance-name="{{user.replica_name}}" \
  --master-instance-region="{{user.replica_region}}" \
  --format=json
```

## Failure Scenarios

| Scenario | Symptom | Resolution |
|----------|---------|------------|
| Promotion fails | 412/FAILED_PRECONDITION | Verify replica is healthy and replication is caught up |
| Application can't connect | Connection timeout | Check security groups, authorized networks, DNS propagation |
| Data mismatch | Row count differs | Use backup restore as fallback; investigate replication gap |
| DNS not updating | Old IP still resolving | Force DNS update; check Cloud DNS status |
| High replication lag | Seconds_Behind_Master > 0 | Wait for lag to close before promoting |

### Emergency Procedures

```bash
# If application cannot connect to new primary:
# 1. Check instance IP configuration
gcloud sql instances describe "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.ipAddresses'

# 2. Check SSL/TLS configuration
gcloud sql instances describe "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.serverCaCert'

# 3. Temporarily allow all IPs if network issue
gcloud sql instances patch "{{user.replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --no-assign-ip \
  --format=json
```

## Rollback Procedures

### Revert to Original Primary

```bash
# Only possible if original primary is still accessible and data is intact

# 1. Stop applications
kubectl scale deployment/{{user.app_deployment}} --replicas=0

# 2. Create new replica from original primary
gcloud sql instances create "{{user.new_replica_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.replica_region}}" \
  --master-instance-name="{{user.instance_name}}" \
  --format=json

# 3. Wait for replication to catch up
# 4. Update DNS to point back to original primary
# 5. Restart applications
kubectl scale deployment/{{user.app_deployment}} --replicas=3
```

## See Also

- [Cloud SQL High Availability](../high-availability.md)
- [Cloud SQL Replicas](../replicas.md)
- [Cloud DNS Documentation](https://cloud.google.com/dns/docs)
- [Cloud SQL Monitoring](../monitoring.md)
- [Google Cloud Architecture Framework — Reliability](https://cloud.google.com/architecture/framework/resilience)
