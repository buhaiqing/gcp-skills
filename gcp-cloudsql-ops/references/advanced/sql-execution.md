# SQL Execution (Security-Sensitive) — Google Cloud SQL

> Provides database administrators and security engineers with a guide to executing SQL queries in Cloud SQL with security controls — connection security, query validation, parameterized queries, audit logging, and access control verification.

## Table of Contents

1. [Overview](#overview)
2. [Security Model](#security-model)
3. [Pre-Execution Validation](#pre-execution-validation)
4. [Query Execution Methods](#query-execution-methods)
5. [Parameterized Queries](#parameterized-queries)
6. [Audit & Compliance](#audit--compliance)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [See Also](#see-also)

## Overview

Security-sensitive SQL execution in Cloud SQL requires:
- **Connection security**: SSL/TLS enforcement for all connections
- **Access control**: IAM-based authentication + VPC network restrictions
- **Query validation**: Syntax and safety checks before execution
- **Audit trail**: Cloud SQL audit logs for compliance
- **Injection prevention**: Parameterized queries only
- **Least privilege**: Dedicated database users with minimal permissions

### Security Considerations

| Concern | Mitigation | Severity |
|---------|------------|----------|
| Credential exposure | IAM Auth, Secret Manager, never plaintext | Critical |
| SQL injection | Parameterized queries only | Critical |
| Network exposure | Private IP + VPC firewall rules | Critical |
| Data exfiltration | Column-level grants, egress monitoring | High |
| Audit compliance | Cloud SQL Audit Logs | High |
| Connection exhaustion | Connection limits, pool sizing | Medium |

## Security Model

```
┌────────────────────────────────────────────────────────────────────────┐
│                     Security-Sensitive SQL Execution                     │
│                                                                          │
│  Client Connection                                                        │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐ │
│  │ IAM Auth     │───►│ SSL/TLS          │───►│ VPC Network        │ │
│  │ (passwordless)│    │ Enforcement      │    │ (Private IP only)  │ │
│  └──────────────┘    └──────────────────┘    └─────────────────────┘ │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐ │
│  │ Query        │───►│ Parameterized     │───►│ Execution with     │ │
│  │ Validation   │    │ Query Builder    │    │ Row/Column Limits   │ │
│  └──────────────┘    └──────────────────┘    └─────────────────────┘ │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐ │
│  │ Cloud SQL    │───►│ Cloud Audit      │───►│ Result             │ │
│  │ Proxy        │    │ Logs             │    │ Validation         │ │
│  └──────────────┘    └──────────────────┘    └─────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

## Pre-Execution Validation

### 1. Connection Security Check

```bash
# Verify SSL/TLS is enforced on Cloud SQL instance
gcloud sql instances describe "{{user.instance_id}}" \
  --format=json | jq '{
    name: .name,
    sslStatus: .serverCaCert,
    ipAddresses: .ipAddresses,
    privateIp: .privateIpAddress,
    requireSsl: .settings.ipConfiguration.requireSsl
  }'
```

### 2. Network Access Check

```bash
# Verify Private IP is enabled and no public IP exposure
gcloud sql instances describe "{{user.instance_id}}" \
  --format=json | jq '{
    requireSsl: .settings.ipConfiguration.requireSsl,
    privateIp: .privateIpAddress,
    authorizedNetworks: .settings.ipConfiguration.authorizedNetworks,
    ipv6Enabled: .ipAddresses[] | select(.type == "IPV6") | .ipAddress
  }'
```

### 3. IAM Authentication Check

```bash
# Verify IAM authentication is enabled
gcloud sql instances describe "{{user.instance_id}}" \
  --format=json | jq '.settings.availabilityType'

# List users with IAM auth enabled
gcloud sql users list \
  --instance="{{user.instance_id}}" \
  --format=json | jq '.[] | select(.plugin == "cloud_sql_auth_proxy") | .name'
```

### 4. Database Existence Check

```bash
# List databases on the instance
gcloud sql databases list \
  --instance="{{user.instance_id}}" \
  --format=json | jq '.[] | select(.name == "{{user.database_name}}")'

# Create database if not exists
gcloud sql databases create "{{user.database_name}}" \
  --instance="{{user.instance_id}}" \
  --charset=utf8mb4 \
  --collation=utf8mb4_unicode_ci
```

## Query Execution Methods

### Cloud SQL Proxy Connection

```bash
# Start Cloud SQL Proxy for secure connection
 cloudsql-proxy --instances="$CLOUDSDK_CORE_PROJECT:{{user.region}}:{{user.instance_id}}=tcp:5432" &

# Verify connection
pg_isready -h 127.0.0.1 -p 5432
```

### PostgreSQL — Execute Query

```bash
# Execute SELECT with row limit (using environment variable for password)
PGPASSWORD="${{env.PG_PASSWORD}}" psql \
  --host=127.0.0.1 \
  --port=5432 \
  --username="{{user.db_user}}" \
  --dbname="{{user.database_name}}" \
  --command="SELECT * FROM {{user.table_name}} LIMIT 100;"
```

### PostgreSQL — Execute Script File

```bash
# Execute SQL script file (never pass inline user input)
PGPASSWORD="${{env.PG_PASSWORD}}" psql \
  --host=127.0.0.1 \
  --port=5432 \
  --username="{{user.db_user}}" \
  --dbname="{{user.database_name}}" \
  --file="{{user.sql_script_path}}"
```

### MySQL — Execute Query

```bash
# Execute SELECT with row limit
mysql \
  --host=127.0.0.1 \
  --port=3306 \
  --user="{{user.db_user}}" \
  --password="${{env.MYSQL_PASSWORD}}" \
  "{{user.database_name}}" \
  --execute="SELECT * FROM {{user.table_name}} LIMIT 100;"
```

### Export Query Results to GCS

```bash
# Export query results to CSV via GCS
PGPASSWORD="${{env.PG_PASSWORD}}" psql \
  --host=127.0.0.1 \
  --port=5432 \
  --username="{{user.db_user}}" \
  --dbname="{{user.database_name}}" \
  --command="\COPY (SELECT * FROM {{user.table_name}} LIMIT 10000) TO STDOUT WITH CSV HEADER" \
  | gsutil cp - "gs://{{user.bucket}}/exports/{{user.filename}}-$(date +%Y%m%d).csv"
```

## Parameterized Queries

### PostgreSQL (Python)

```python
import psycopg2
import os

conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    dbname="{{user.database_name}}",
    user="{{user.db_user}}",
    password=os.environ["PG_PASSWORD"],
    sslmode="require"
)

cursor = conn.cursor()
cursor.execute(
    "SELECT * FROM %s WHERE id = %%s AND status = %%s",
    ( "{{user.table_name}}", "{{user.status}}")
)
results = cursor.fetchall()
cursor.close()
conn.close()
```

### PostgreSQL (Bash with psql)

```bash
# Use parameterized query — table name must be escaped, values parameterized
TABLE_NAME="{{user.table_name}}"
STATUS="{{user.status}}"

PGPASSWORD="${{env.PG_PASSWORD}}" psql \
  --host=127.0.0.1 \
  --port=5432 \
  --username="{{user.db_user}}" \
  --dbname="{{user.database_name}}" \
  --command="SELECT * FROM $TABLE_NAME WHERE status = '$STATUS' LIMIT 100;"
```

### MySQL (Python)

```python
import mysql.connector
import os

conn = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    database="{{user.database_name}}",
    user="{{user.db_user}}",
    password=os.environ["MYSQL_PASSWORD"]
)

cursor = conn.cursor()
cursor.execute(
    "SELECT * FROM %s WHERE id = %s AND status = %s",
    ("{{user.table_name}}", "{{user.id}}", "{{user.status}}")
)
results = cursor.fetchall()
cursor.close()
conn.close()
```

## Audit & Compliance

### Enable Cloud SQL Audit Logs

```bash
# Verify audit configuration
gcloud sql instances describe "{{user.instance_id}}" \
  --format=json | jq '.settings.audit'

# Enable audit logs (PostgreSQL)
gcloud sql instances patch "{{user.instance_id}}" \
  --backup-start-time="{{user.backup_start_time}}" \
  --enable-bin-log
```

### Query Audit Log

```bash
# Read Cloud SQL audit logs for query activity
gcloud logging read \
  'resource.type="cloudsql_database"
   resource.labels.database_id="{{user.instance_id}}"
   logName="cloudsql.googleapis.com/postgresql.log"' \
  --project="$CLOUDSDK_CORE_PROJECT" \
  --format=json \
  --order-by="timestamp desc" \
  --limit=50
```

### User Activity Audit

```bash
# List recent database user connections
gcloud sql users list \
  --instance="{{user.instance_id}}" \
  --format=json | jq '.[] | {name: .name, plugin: .plugin, validUntil: .validUntil}'
```

## Error Handling

### Error Code Reference

| Error | Cause | Resolution |
|-------|-------|------------|
| `accessDenied` | Insufficient IAM | Grant `cloudsql.instanceUser` role |
| `connectionFailed` | Network/VPC issue | Check proxy, firewall rules |
| `sslRequired` | SSL not enforced | Enable `--ssl-mode=require` |
| `quotaExceeded` | Connection limit | Reduce pool size or request increase |
| `syntaxError` | Invalid SQL | Fix query syntax |
| `tableNotFound` | Wrong table name | Verify table exists |

### Error Recovery

```bash
# Handle connection failure
if ! pg_isready -h 127.0.0.1 -p 5432; then
  echo "RETRY: Starting Cloud SQL Proxy..."
  cloudsql-proxy --instances="$CLOUDSDK_CORE_PROJECT:{{user.region}}:{{user.instance_id}}=tcp:5432" &
  sleep 5
fi

# Handle SSL requirement
if echo "$ERROR" | grep -q "sslRequired"; then
  echo "FIX: Add --sslmode=require to connection string"
  exit 1
fi
```

## Best Practices

1. **Use Cloud SQL Proxy**: Always use proxy or Private IP for connections
2. **Enforce SSL/TLS**: Require SSL for all database connections
3. **Use IAM Authentication**: Prefer IAM auth over password auth
4. **Parameterize all queries**: Never interpolate user input directly into SQL
5. **Limit result sets**: Always use `LIMIT` to prevent accidental data exposure
6. **Enable audit logs**: Cloud SQL Audit Logs for all query activity
7. **Use least privilege**: Dedicated database users with minimal permissions
8. **Store credentials in Secret Manager**: Never hardcode passwords
9. **VPC network**: Restrict access to VPC network only
10. **Connection pooling**: Use connection pools to avoid exhaustion

## Troubleshooting

### Connection Timeout

```bash
# Check if Cloud SQL Proxy is running
ps aux | grep cloudsql-proxy

# Test connectivity
nc -zv 127.0.0.1 5432

# Check instance status
gcloud sql instances describe "{{user.instance_id}}" \
  --format=json | jq '{state: .state, ipAddresses: .ipAddresses}'
```

### Authentication Failure

```bash
# Verify user exists
gcloud sql users list \
  --instance="{{user.instance_id}}" \
  --format=json | jq '.[] | select(.name == "{{user.db_user}}")'

# Reset password if needed (use Secret Manager)
gcloud sql users set-password "{{user.db_user}}" \
  --instance="{{user.instance_id}}" \
  --password="$(openssl rand -base64 32)"
```

### Query Performance Issues

```bash
# Show running queries (PostgreSQL)
PGPASSWORD="${{env.PG_PASSWORD}}" psql \
  --host=127.0.0.1 \
  --port=5432 \
  --username="{{user.db_user}}" \
  --dbname="{{user.database_name}}" \
  --command="SELECT pid, now() - query_start AS duration, state, query FROM pg_stat_activity WHERE state != 'idle';"
```

## See Also

- [Cloud SQL Core Concepts](../core-concepts.md)
- [Cloud SQL Monitoring](../monitoring.md)
- [Cloud SQL Troubleshooting](../troubleshooting.md)
- [Cloud SQL IAM Authentication](https://cloud.google.com/sql/docs/postgres/authentication)
- [Cloud SQL Audit Logs](https://cloud.google.com/sql/docs/postgres/audit)
- [Cloud SQL Best Practices](https://cloud.google.com/sql/docs/postgres/best-practices)
