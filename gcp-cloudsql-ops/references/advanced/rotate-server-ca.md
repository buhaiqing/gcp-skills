# Rotate Server CA — Google Cloud SQL

> Provides database administrators with a complete runbook for rotating the Cloud SQL server Certificate Authority (CA) — including intermediate CA rotation, application restart requirements, and verification procedures.

## Table of Contents

1. [Overview](#overview)
2. [CA Hierarchy](#ca-hierarchy)
3. [Pre-flight Checks](#pre-flight-checks)
4. [CA Rotation Operation](#ca-rotation-operation)
5. [Application Updates](#application-updates)
6. [Verification](#verification)
7. [Failure Scenarios](#failure-scenarios)
8. [See Also](#see-also)

## Overview

Cloud SQL uses SSL/TLS certificates for encrypted connections. The server CA certificate verifies the server's identity to clients. CA rotation may be required for:

| Reason | Frequency | Impact |
|--------|-----------|--------|
| Scheduled rotation | Every ~1 year | Application restart required |
| Security incident | Rare | Emergency CA swap |
| Compliance requirement | Varies | Policy-driven |

### Rotation Requirements

- MySQL 5.7+: Supports CA rotation with minimal downtime
- PostgreSQL: Full support for CA rotation
- SQL Server: Uses Windows Certificate Store, different process

## CA Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cloud SQL CA Hierarchy                        │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Root CA                                │   │
│  │  (Google Trust Services - Long-lived, rarely rotates)    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Intermediate CA                              │   │
│  │  (Rotated periodically - Cloud SQL managed)              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               Server Certificate                         │   │
│  │  (Instance-specific, auto-managed)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Pre-flight Checks

### 1. Check Current CA Status

```bash
# Get current server CA certificate
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.serverCaCert'

# Check certificate expiration
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
    certSerialNumber: .serverCaCert.certSerialNumber,
    validAfter: .serverCaCert.validAfterTime,
    validBefore: .serverCaCert.sha1Fingerprint
  }'
```

### 2. Verify SSL/TLS Configuration

```bash
# Check SSL mode settings
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.ipConfiguration.sslMode'

# List SSL certificates
gcloud sql ssl-certs list --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="table(certSerialNumber,commonName,expirationTime)"
```

### 3. Check Client Applications

```bash
# Document application SSL/TLS configurations
# Applications should use server-ca-cert from the instance
# Check application connection strings for SSL settings

# For MySQL clients, verify they handle certificate verification
mysql --ssl-mode=VERIFY_CA --ssl-ca=server-ca.pem -h "{{user.instance_name}}" \
  -u "{{user.user_name}}" -p -e "SELECT 1" 2>/dev/null && echo "SSL connection OK"
```

### 4. Backup Current Certificate

```bash
# Download current server CA certificate
gcloud sql ssl-certs describe "$(gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format='value(serverCaCert.certSerialNumber)')" \
  --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq -r '.cert' > /tmp/current-server-ca.pem

echo "Current CA saved to /tmp/current-server-ca.pem"
```

## CA Rotation Operation

### Step 1: Initiate CA Rotation

```bash
# Rotate the server CA certificate
gcloud sql instances rotate-ssl-cert "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json

# Capture operation ID
OPERATION_ID=$(gcloud sql instances rotate-ssl-cert "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq -r '.name')

echo "CA rotation operation: $OPERATION_ID"
```

### Step 2: Monitor Rotation Progress

```bash
# Poll operation status
gcloud sql operations describe "$OPERATION_ID" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{status: .status, progress: .progress}'

# Wait for operation to complete
gcloud sql operations wait "$OPERATION_ID" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --timeout=120s
```

### Step 3: Retrieve New CA Certificate

```bash
# Get new server CA certificate details
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.serverCaCert'

# List all SSL certificates to verify new one
gcloud sql ssl-certs list --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="table(certSerialNumber,commonName,expirationTime)"
```

### Step 4: Download New CA for Clients

```bash
# Download the new server CA certificate
NEW_CERT_SERIAL=$(gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format='value(serverCaCert.certSerialNumber)')

gcloud sql ssl-certs describe "$NEW_CERT_SERIAL" \
  --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq -r '.cert' > /tmp/new-server-ca.pem

# Also get the private key (if needed for some configurations)
gcloud sql ssl-certs describe "$NEW_CERT_SERIAL" \
  --instance="{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq -r '.privateKey' > /tmp/new-server-ca-key.pem

echo "New CA saved to /tmp/new-server-ca.pem"
```

## Application Updates

### Application Restart Requirement

CA rotation requires application restart because:
- Applications cache the old CA certificate
- New connections will fail until app reloads new CA
- Connection pools should be flushed

### Distribute New CA Certificate

```bash
# Option 1: Push to application servers via secure copy
for server in "{{user.app_server_1}}" "{{user.app_server_2}}" "{{user.app_server_3}}"; do
  scp /tmp/new-server-ca.pem "{{user.ssh_user}}@${server}:/tmp/server-ca.pem"
done

# Option 2: Update via Kubernetes Secret
kubectl create secret generic mysql-server-ca \
  --from-file=ca-cert=/tmp/new-server-ca.pem \
  --namespace="{{user.namespace}}" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Restart Applications

```bash
# Restart application servers to pick up new CA
kubectl rollout restart deployment/{{user.app_deployment}} \
  --namespace="{{user.namespace}}"

# Verify rollout completes
kubectl rollout status deployment/{{user.app_deployment}} \
  --namespace="{{user.namespace}}"
```

### For Direct Connection (Non-Kubernetes)

```bash
# Restart application services
sudo systemctl restart "{{user.app_service}}"

# Or for manual process, restart the application process
sudo kill -HUP $(pgrep -f "{{user.app_process}}")
```

## Verification

### 1. Verify Instance SSL Mode

```bash
# Check SSL is enabled
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.ipConfiguration.sslMode'
```

### 2. Test SSL Connection with New CA

```bash
# MySQL SSL connection test
mysql --ssl-mode=VERIFY_CA \
  --ssl-ca=/tmp/new-server-ca.pem \
  -h "{{user.instance_name}}" \
  -u "{{user.user_name}}" \
  -p"{{env.MYSQL_PASSWORD}}" \
  --execute="SELECT 1 AS test" 2>/dev/null && echo "SSL connection with new CA: OK"

# PostgreSQL SSL connection test
PGSSLMODE=verify-ca PGSSLROOTCERT=/tmp/new-server-ca.pem \
  psql -h "{{user.instance_name}}" \
  -U "{{user.user_name}}" \
  -d "{{user.database_name}}" \
  -c "SELECT 1 AS test" 2>/dev/null && echo "SSL connection with new CA: OK"
```

### 3. Verify Application Connectivity

```bash
# Test application health endpoint
curl -s "https://{{user.app_endpoint}}/health" | jq '.database'

# Check application logs for SSL errors
kubectl logs deployment/{{user.app_deployment}} \
  --namespace="{{user.namespace}}" \
  --since=5m | grep -i "ssl\|certificate\|connect" | tail -10
```

### 4. Monitor Error Rates

```bash
# Check for connection errors in monitoring
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
    state: .state,
    ipAddresses: .ipAddresses,
    sslMode: .ipConfiguration.sslMode
  }'

# Review Cloud Logging for SSL-related errors
gcloud logging read "resource.type=cloudsql_database AND severity>=WARNING" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  -- freshness=1h \
  --format="table(timestamp,severity,textPayload)" | grep -i "ssl\|certificate"
```

## Failure Scenarios

| Scenario | Symptom | Resolution |
|----------|---------|------------|
| Application still using old CA | SSL handshake failure | Restart application; ensure new CA is distributed |
| Connection pool has stale connections | Intermittent failures | Flush connection pool; restart application |
| Certificate not propagated | SSL verification fails | Wait 60 seconds; verify certificate download |
| CA rotation timeout | Operation pending | Check operation status; retry if needed |

### Troubleshooting Commands

```bash
# If SSL connection fails, debug with verbose output
mysql --ssl-mode=VERIFY_CA \
  --ssl-ca=/tmp/new-server-ca.pem \
  -h "{{user.instance_name}}" \
  -u "{{user.user_name}}" \
  -p"{{env.MYSQL_PASSWORD}}" \
  --verbose 2>&1 | grep -E "SSL|CA|certificate"

# Check current CA fingerprint
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="value(serverCaCert.sha1Fingerprint)"

# Compare with what application has
openssl x509 -in /tmp/new-server-ca.pem -noout -fingerprint
```

## See Also

- [Cloud SQL SSL/TLS Configuration](../ssl-tls.md)
- [Cloud SQL Connection Security](../connection-security.md)
- [Cloud SQL Monitoring](../monitoring.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud SQL SSL Documentation](https://cloud.google.com/sql/docs/mysql/configure-ssl)
