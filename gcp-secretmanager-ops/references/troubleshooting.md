# Troubleshooting — Cloud Secret Manager

## Error Codes

| Code | Summary | Explanation | Remediation | Next Step |
|------|---------|-------------|-------------|-----------|
| INVALID_ARGUMENT / 400 | Invalid parameter | Bad secret ID format, payload too large | Fix parameter (≤64KB, valid name) | Retry with corrected value |
| PERMISSION_DENIED / 403 | No IAM access | SA lacks secretmanager.* role | Grant appropriate role | Check IAM bindings |
| NOT_FOUND / 404 | Resource missing | Secret or version doesn't exist | Verify resource path | List resources to confirm |
| ALREADY_EXISTS / 409 | Duplicate | Secret name in use | Use different name | Rename and retry |
| QUOTA_EXCEEDED / 429 | Rate limit hit | Exceeded requests per minute | Reduce rate or request increase | Check quotas in Console |
| FAILED_PRECONDITION / 412 | State conflict | Version is DISABLED or DESTROYED | Check version state | Enable/create version first |
| RESOURCE_EXHAUSTED / 429 | Payload too large | Version payload > 64KB | Compress or use Cloud Storage | Retry with smaller payload |
| ABORTED / 409 | Concurrency conflict | Concurrent modification | Retry | Ensure single writer |
| CANCELLED / 499 | Request cancelled | Operation timed out | Retry | Check network |
| UNAVAILABLE / 503 | Service unavailable | Backend transient failure | Retry with backoff | Wait and retry |
| INTERNAL / 500 | Internal error | GCP backend error | Retry; escalate if persistent | Report to GCP Support |
| DEADLINE_EXCEEDED / 504 | Timeout | Request exceeded deadline | Retry with longer timeout | Check network latency |

## Diagnostic Order

```
1. Auth check     → gcloud auth print-access-token
2. Project check  → gcloud config get-value project
3. API status     → gcloud services list --enabled | grep secretmanager.googleapis.com
4. Resource check → gcloud secrets list --project=PROJECT
5. Secret exists  → gcloud secrets describe SECRET --project=PROJECT
6. Version state  → gcloud secrets versions list SECRET --project=PROJECT
7. IAM check      → gcloud secrets get-iam-policy SECRET --project=PROJECT
```

## Common Issues

### "Secret not found"
```bash
gcloud secrets list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq '.[].name'
```

### "Permission denied on access"
Add IAM binding:
```bash
gcloud secrets add-iam-policy-binding "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --member="serviceAccount:SA@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### "Payload too large (>64KB)"
```bash
# Check payload size
wc -c < secret-file.txt
# If > 65536, use Cloud Storage reference instead
```

### "Access request throttled"
- Access limit: 600 requests per secret per minute
- Implement client-side caching with TTL
- Use batch operations where possible

## Error Recovery Patterns

### Retry with backoff
```bash
for i in 1 2 3; do
  gcloud secrets describe "my-secret" --format="json" && break
  echo "⚠️  Retry $i/3..."
  sleep $((2**i))
done
```

### Idempotent create
```bash
if ! gcloud secrets describe "my-secret" --quiet 2>/dev/null; then
  gcloud secrets create "my-secret" --data-file=- <<< "value"
fi
```

### Version state recovery
```bash
# Check if version is disabled
state=$(gcloud secrets versions describe "1" --secret="my-secret" --format="value(state)")
if [ "$state" = "DISABLED" ]; then
  gcloud secrets versions enable "1" --secret="my-secret"
fi
```
