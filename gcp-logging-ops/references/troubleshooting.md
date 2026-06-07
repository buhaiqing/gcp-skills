# Troubleshooting — Cloud Logging

## Error Codes

| Code | Summary | Explanation | Remediation | Next Step |
|------|---------|-------------|-------------|-----------|
| INVALID_ARGUMENT / 400 | Invalid parameter | Filter syntax error, invalid retention, malformed destination URL | Fix parameter from error message | Retry with corrected params |
| PERMISSION_DENIED / 403 | No access | SA lacks logging.* IAM role | Grant roles/logging.admin or roles/logging.viewer | Check IAM bindings |
| NOT_FOUND / 404 | Resource missing | Bucket, sink, or metric doesn't exist | Verify resource name and location | List resources to confirm |
| ALREADY_EXISTS / 409 | Duplicate name | Resource with same name exists | Use a different name | Rename and retry |
| QUOTA_EXCEEDED / 429 | Quota exhausted | Exceeded bucket/sink/metric quota or ingestion rate | Request quota increase or reduce resources | Check quotas in Console |
| FAILED_PRECONDITION / 400 | Precondition failed | CMEK key inaccessible, bucket locked, or destination unreachable | Check dependencies | Resolve precondition |
| ABORTED / 409 | Operation aborted | Conflict due to concurrent modification | Retry | Ensure no concurrent updates |
| RESOURCE_EXHAUSTED / 429 | Resource pool empty | Region capacity insufficient | Try another location | Retry in different region |
| DEADLINE_EXCEEDED / 504 | Operation timeout | Query or operation took too long | Narrow time range or reduce complexity | Reduce filter scope |
| UNAVAILABLE / 503 | Service unavailable | Logging backend transient failure | Retry with backoff | Wait and retry |
| INTERNAL / 500 | Internal error | GCP backend error | Retry; escalate if persistent | Report to GCP Support |
| CMEK_KEY_INACCESSIBLE | CMEK key revoked | Cloud KMS key for bucket is inaccessible | Restore key or grant decrypt permission | Check KMS key state |
| BUCKET_LOCKED | Bucket locked | Attempt to modify a locked bucket | Cannot modify; consider new bucket | Create new bucket |
| SINK_DESTINATION_INACCESSIBLE | Destination unreachable | BigQuery dataset / PubSub topic / GCS bucket inaccessible | Check destination IAM and existence | Verify destination |

## Diagnostic Order

```
1. Auth check     → gcloud auth print-access-token
2. Project check  → gcloud config get-value project
3. API status     → gcloud services list --enabled | grep logging.googleapis.com
4. Quota check    → gcloud logging quotas list
5. Resource check → gcloud logging sinks list / buckets list ...
6. IAM check      → gcloud projects get-iam-policy <project>
7. Destination    → gcloud logging sinks describe <name> | jq .writerIdentity
```

## Common Issues

### "Logs not appearing"

| Cause | Check | Fix |
|-------|-------|-----|
| Ingestion latency | Wait 1-2 minutes | Normal delay |
| Exclusion filter | `gcloud logging exclusions list` | Remove/modify exclusion |
| Wrong filter | Simplify filter expression | Test with `severity>=DEFAULT` |
| Bucket retention expired | `gcloud logging buckets describe` | Increase retention_days |
| _Default bucket deleted | Check bucket status | Create new _Default bucket |
| Logging agent stopped (GCE) | `gcloud compute ssh VM -- check google-cloud-ops-agent` | Restart ops agent |

### "Sink not delivering"

```bash
# Check sink writer identity
gcloud logging sinks describe "{{user.sink_name}}" \
  --format="json" | jq -r '.writerIdentity'

# Verify destination IAM has the writer identity granted
# For BigQuery: roles/bigquery.dataEditor
# For Pub/Sub: roles/pubsub.publisher
# For GCS: roles/storage.objectCreator
```

### "Permission denied reading logs"

| Role | Grants |
|------|--------|
| `roles/logging.viewer` | Read log entries, view bucket contents |
| `roles/logging.privateLogViewer` | Read private (_Required) log entries |
| `roles/logging.admin` | Full management (create/delete sinks, buckets, metrics) |
| `roles/logging.logWriter` | Write log entries only |

### "Can't create log bucket with CMEK"

```bash
# Verify CMEK key state
gcloud kms keys versions list --keyring=KEYRING --key=KEY --location=LOC

# Grant EncrypterDecrypter to Logging SA
gcloud kms keys add-iam-policy-binding KEY \
  --keyring=KEYRING --location=LOC \
  --member="serviceAccount:cloud-logs@system.gserviceaccount.com" \
  --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"
```

### "Log ingestion rate exceeded"

```bash
# Check current ingestion rate (Cloud Monitoring)
# Metric: logging.googleapis.com/log_entry_count
# Action: Create exclusion rules to reduce volume
gcloud logging exclusions create "high-volume-logs" \
  --log-filter="resource.type=k8s_container AND jsonPayload.level=debug" \
  --description="Exclude verbose k8s debug logs"
```

## Error Recovery Patterns

### Retry with backoff
```bash
for i in 1 2 3; do
  gcloud logging sinks describe "my-sink" --format="json" && break
  echo "⚠️  Retry $i/3..."
  sleep $((2**i))
done
```

### Idempotent create
```bash
if ! gcloud logging metrics describe "my-metric" --quiet 2>/dev/null; then
  gcloud logging metrics create "my-metric" \
    --description="Error tracking" \
    --log-filter="severity>=ERROR"
fi
```