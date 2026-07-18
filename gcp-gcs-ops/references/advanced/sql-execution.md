# SQL Execution (Security-Sensitive) — Google Cloud Storage

> Provides data engineers and security administrators with a guide to executing SQL queries on Cloud Storage data — GCS Select, data validation, cost estimation, result handling, and audit trail verification.

## Table of Contents

1. [Overview](#overview)
2. [Security Model](#security-model)
3. [Pre-Execution Validation](#pre-execution-validation)
4. GCS Select Execution
5. [Result Handling](#result-handling)
6. [Audit & Compliance](#audit--compliance)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [See Also](#see-also)

## Overview

Security-sensitive SQL execution on Cloud Storage uses **GCS Select** to query CSV/JSON/Parquet/Avro objects in-place without downloading. Key security considerations:

- **Data exposure**: Only query objects you have access to; results contain subset of data
- **Cost control**: GCS Select charges per GB scanned, not per result
- **SQL injection**: GCS Select has limited SQL dialect; no UDFs or external calls
- **Audit trail**: Cloud Audit Logs track all Select operations
- **Encryption**: Data encrypted at rest by default; CMEK available

### Security Considerations

| Concern | Mitigation | Severity |
|---------|------------|----------|
| Cost explosion | Estimate scanned bytes before execution | Critical |
| Data exfiltration | IAM + bucket/object ACLs restrict access | Critical |
| Sensitive data scan | CMEK + VPC Service Controls | High |
| Audit compliance | Cloud Audit Logs for all Select ops | High |
| Unintended data access | Least privilege IAM + bucket policy | High |
| Result size | LIMIT and column projection | Medium |

## Security Model

```
┌────────────────────────────────────────────────────────────────────────┐
│                     Security-Sensitive GCS Select                       │
│                                                                          │
│  User Request                                                            │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐ │
│  │ Object       │───►│ IAM/ACL          │───►│ Bucket Policy       │ │
│  │ Access      │    │ Check            │    │ Verification        │ │
│  └──────────────┘    └──────────────────┘    └─────────────────────┘ │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐ │
│  │ SQL          │───►│ Scanned Bytes    │───►│ Cost Estimation     │ │
│  │ Validation   │    │ Estimation       │    │ ($0.0025/GB)        │ │
│  └──────────────┘    └──────────────────┘    └─────────────────────┘ │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐ │
│  │ Execute      │───►│ Result            │───►│ Audit Log           │ │
│  │ (GCS Select) │    │ Validation        │    │ (Cloud Logging)     │ │
│  └──────────────┘    └──────────────────┘    └─────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

## Pre-Execution Validation

### 1. Object Existence and Access Check

```bash
# Check object exists and is accessible
gsutil ls -L "gs://{{user.bucket}}/{{user.object_path}}" 2>&1

# Check IAM permissions on bucket
gcloud storage buckets describe "gs://{{user.bucket}}" \
  --format=json | jq '{name: .name, location: .location, iamConfiguration: .iamConfiguration}'
```

### 2. Object Size and Type Check

```bash
# Get object metadata for cost estimation
gsutil ls -l "gs://{{user.bucket}}/{{user.object_path}}" | head -5

# Check object content type
gsutil stat "gs://{{user.bucket}}/{{user.object_path}}" | grep "Content-Type:"
```

### 3. SQL Syntax Validation

```bash
# GCS Select supports standard SQL (SELECT, WHERE, GROUP BY, ORDER BY, LIMIT)
# Unsupported: JOINs, subqueries in WHERE, UDFs, HAVING, window functions
# Validate basic SQL structure
echo "{{user.sql_query}}" | grep -qE "^(SELECT|FROM)" && echo "✅ Basic SQL structure valid" || echo "❌ Invalid SQL"
```

### 4. IAM Permission Check

```bash
# Verify user has storage.objects.list and storage.objects.get
gcloud projects get-iam-policy "$CLOUDSDK_CORE_PROJECT" \
  --format=json | jq -r '
    .bindings[] |
    select(.members[] | contains("user:{{user.email}}")) |
    .role' | grep -qE "storage\.(objectViewer|objectAdmin)" && {
  echo "✅ User has GCS object permissions"
} || {
  echo "ERROR: User lacks GCS object permissions"
  exit 1
}
```

## GCS Select Execution

### Estimate Scanned Bytes (Pre-flight)

```bash
# GCS Select pricing: $0.0025/GB scanned (first 1TB/month)
# Estimate by checking file size (actual scanned depends on SQL predicates)

OBJECT_SIZE_BYTES=$(gsutil ls -l "gs://{{user.bucket}}/{{user.object_path}}" | awk '{print $1}')
OBJECT_SIZE_GB=$(echo "scale=6; $OBJECT_SIZE_BYTES / 1073741824" | bc)
ESTIMATED_COST=$(echo "scale=4; $OBJECT_SIZE_GB * 0.0025" | bc)

echo "Object size: $OBJECT_SIZE_BYTES bytes ($OBJECT_SIZE_GB GB)"
echo "Estimated Select cost: \$$ESTIMATED_COST (if full scan)"
echo "Actual cost depends on SQL predicates (WHERE clause reduces scanned data)"
```

### CSV/JSON — Execute GCS Select

```bash
# GCS Select on CSV with SQL query
# Only specified columns and rows matching WHERE clause are returned
gcloud storage objects select "gs://{{user.bucket}}/{{user.object_path}}" \
  --format=json \
  --sql="SELECT {{user.columns}} FROM {{user.object_path}} WHERE {{user.where_clause}} LIMIT {{user.limit}}" \
  --input-format=CSV \
  --csv-delimiter="," \
  --csv-header
```

### Parquet — Execute GCS Select

```bash
# GCS Select on Parquet (columnar — only referenced columns scanned)
gcloud storage objects select "gs://{{user.bucket}}/{{user.object_path}}" \
  --format=json \
  --sql="SELECT {{user.columns}} FROM {{user.object_path}} WHERE {{user.where_clause}} LIMIT {{user.limit}}" \
  --input-format=Parquet
```

### Avro — Execute GCS Select

```bash
# GCS Select on Avro
gcloud storage objects select "gs://{{user.bucket}}/{{user.object_path}}" \
  --format=json \
  --sql="SELECT {{user.columns}} FROM {{user.object_path}} WHERE {{user.where_clause}} LIMIT {{user.limit}}" \
  --input-format=Avro
```

### Write Results to GCS

```bash
# GCS Select with output to another GCS object
gcloud storage objects select "gs://{{user.bucket}}/{{user.object_path}}" \
  --output-path="gs://{{user.bucket}}/{{user.output_path}}" \
  --format=CSV \
  --sql="SELECT {{user.columns}} FROM {{user.object_path}} WHERE {{user.where_clause}} LIMIT {{user.limit}}" \
  --input-format=CSV \
  --csv-header
```

### Python SDK (Secure)

```python
from google.cloud import storage

client = storage.Client()

bucket = client.bucket("{{user.bucket}}")
blob = bucket.blob("{{user.object_path}}")

# GCS Select via Python SDK
# Note: Python SDK uses google.cloud.storage.bucket.acl and blob.download_as_text
# For Select, use the REST API or gsutil
# This example downloads and filters locally (for smaller datasets)

if blob.size < 100 * 1024 * 1024:  # < 100MB
    content = blob.download_as_text()
    lines = [l for l in content.split('\n') if '{{user.filter_expression}}' in l]
    print('\n'.join(lines[:100]))
else:
    print("ERROR: Object too large for local processing — use GCS Select instead")
```

### Go SDK (REST API)

```go
// GCS Select via REST API
import "cloud.google.com/go/storage"

func runGCSSelect(ctx context.Context, client *storage.Client, bucket, object, sql string) error {
    attrs, err := client.Bucket(bucket).Object(object).Attrs(ctx)
    if err != nil {
        return err
    }
    fmt.Printf("Object size: %d bytes\n", attrs.Size)
    // GCS Select is called via gsutil or REST API
    // gsutil ls -L gs://bucket/object | head
    return nil
}
```

## Result Handling

### Validate Result Size

```bash
# After GCS Select, check output size
gcloud storage objects describe "gs://{{user.bucket}}/{{user.output_path}}" \
  --format=json | jq '{size: .size, contentType: .contentType, updated: .updated}'
```

### Download and Validate Results

```bash
# Download result to local for inspection
gsutil cp "gs://{{user.bucket}}/{{user.output_path}}" /tmp/select_result.json

# Validate result format
head -5 /tmp/select_result.json | jq type 2>/dev/null || head -5 /tmp/select_result.json

# Clean up
rm /tmp/select_result.json
```

## Audit & Compliance

### Enable Cloud Audit Logs

```bash
# Verify Data Access audit logs are enabled for GCS
gcloud logging write "test-log" "test" --severity=INFO 2>&1

# GCS Data Access logs are written automatically when enabled in audit config
gcloud projects get-iam-policy "$CLOUDSDK_CORE_PROJECT" \
  --format=json | jq '.auditConfigs[] | select(.service=="storage.googleapis.com")'
```

### Query Audit Log

```bash
# Query Cloud Audit Logs for GCS Select operations
gcloud logging read \
  'resource.type="gcs_bucket"
   resource.labels.bucket_name="{{user.bucket}}"
   logName="cloudsql.googleapis.com/storage/data_access"' \
  --project="$CLOUDSDK_CORE_PROJECT" \
  --format=json \
  --order-by="timestamp desc" \
  --limit=20 | jq '.[] | {
      timestamp: .timestamp,
      operation: .protoPayload.methodName,
      object: .protoPayload.resourceName,
      user: .authenticationInfo.principalEmail
    }'
```

### Data Access Review

```bash
# List recent data access events on bucket
gcloud logging read \
  'resource.type="gcs_bucket"
   logName="cloudsql.googleapis.com/storage/data_access"
   protoPayload.resourceName="projects/_/buckets/{{user.bucket}}"' \
  --project="$CLOUDSDK_CORE_PROJECT" \
  --format=json \
  --order-by="timestamp desc" \
  --limit=100 | jq '.[] | {
      timestamp: .timestamp,
      operation: .protoPayload.methodName,
      object: .protoPayload.resourceName,
      user: .authenticationInfo.principalEmail,
      ip: .protoPayload.requestMetadata.callerIp
    }'
```

## Error Handling

### Error Code Reference

| Error | Cause | Resolution |
|-------|-------|------------|
| `accessDenied` | Insufficient IAM | Grant `storage.objectViewer` role |
| `invalidSql` | Unsupported SQL syntax | Fix SQL (no JOINs/subqueries) |
| `unsupportedFormat` | Object not CSV/JSON/Parquet/Avro | Convert or use download |
| `compressedObject` | Gzip/bzip compressed | Use `--input-format` with compression |
| `quotaExceeded` | GCS Select quota exceeded | Request increase or split objects |
| `objectNotFound` | Wrong path | Verify object exists |

### Error Recovery

```bash
# Handle access denied
if echo "$ERROR" | grep -q "accessDenied"; then
  echo "HALT: User lacks GCS object access"
  echo "FIX: gcloud projects add-iam-policy-binding $CLOUDSDK_CORE_PROJECT \
    --member=user:{{user.email}} --role=roles/storage.objectViewer"
  exit 1
fi

# Handle invalid SQL
if echo "$ERROR" | grep -q "invalidSql"; then
  echo "HALT: GCS Select SQL syntax not supported"
  echo "NOTE: GCS Select does not support JOINs, subqueries in WHERE, UDFs, HAVING"
  exit 1
fi
```

## Best Practices

1. **Always estimate cost first**: Use file size × $0.0025/GB to estimate Select cost
2. **Use WHERE predicates**: Reduce scanned bytes by filtering early
3. **Project columns**: Use `SELECT col1, col2` not `SELECT *` to reduce data transfer
4. **Use LIMIT**: Prevent accidental large result sets
5. **Prefer Parquet**: Columnar format — only referenced columns scanned
6. **Use CMEK**: Encrypt sensitive data with customer-managed keys
7. **Enable audit logs**: Cloud Audit Logs for all GCS Select operations
8. **Least privilege**: IAM only grants object access to specific buckets/objects
9. **Compressed data**: GCS Select works with gzip/bzip2 compressed CSV/JSON
10. **Split large objects**: For very large datasets, split into multiple objects

## Troubleshooting

### Query Returns No Results

```bash
# Verify object has data
gsutil cat "gs://{{user.bucket}}/{{user.object_path}}" | head -5

# Check SQL WHERE clause — ensure field names match header
gsutil head -1 "gs://{{user.bucket}}/{{user.object_path}}"

# Test with simpler query
gcloud storage objects select "gs://{{user.bucket}}/{{user.object_path}}" \
  --sql="SELECT * FROM {{user.object_path}} LIMIT 5"
```

### Object Too Large for Select

```bash
# GCS Select has 10GB max scanned per query
# For larger objects, split into multiple smaller objects

# Check object size
gsutil ls -l "gs://{{user.bucket}}/{{user.object_path}}" | awk '{print $1}'

# If > 10GB, need to split or use alternative approach
echo "ERROR: Object exceeds 10GB GCS Select limit"
echo "FIX: Split object into smaller files using parallel composite uploads"
```

### SQL Syntax Not Supported

```bash
# GCS Select SQL limitations:
# - No JOINs between objects
# - No subqueries in WHERE clause
# - No HAVING, window functions, UDFs
# - LIMIT must be constant (no parameterization)

# Verify SQL is valid
gcloud storage objects select "gs://{{user.bucket}}/{{user.object_path}}" \
  --sql="SELECT COUNT(*) FROM {{user.object_path}}" 2>&1 | head -10
```

## See Also

- [GCS Core Concepts](../core-concepts.md)
- [GCS Monitoring](../monitoring.md)
- [GCS Troubleshooting](../troubleshooting.md)
- [GCS Select Documentation](https://cloud.google.com/storage/docs/querying#sql)
- [GCS IAM Permissions](https://cloud.google.com/storage/docs/access-control)
- [GCS Audit Logs](https://cloud.google.com/storage/docs/audit-logging)
