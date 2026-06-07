# Troubleshooting — Cloud KMS

## Error Codes

| Code | Summary | Explanation | Remediation | Next Step |
|------|---------|-------------|-------------|-----------|
| INVALID_ARGUMENT / 400 | Invalid parameter | Bad key name, location, algorithm | Fix parameter | Retry with corrected value |
| PERMISSION_DENIED / 403 | No IAM access | SA lacks cloudkms.* role | Grant cloudkms role on key/keyring | Check IAM bindings |
| NOT_FOUND / 404 | Resource missing | Key ring, key, or version doesn't exist | Verify resource path and location | List resources to confirm |
| ALREADY_EXISTS / 409 | Duplicate | Key ring or key name in use | Use different name | Rename and retry |
| QUOTA_EXCEEDED / 429 | Rate limit hit | Exceeded requests per minute | Reduce rate or request increase | Check quotas in Console |
| FAILED_PRECONDITION / 400 | State conflict | Version is DESTROYED or not in correct state | Check version state | Enable/restore version first |
| ABORTED / 409 | Concurrency conflict | Concurrent modification | Retry | Ensure single writer |
| CANCELLED / 499 | Request cancelled | Operation timed out or cancelled | Retry | Check network |
| UNAVAILABLE / 503 | Service unavailable | KMS backend transient failure | Retry with backoff | Wait and retry |
| INTERNAL / 500 | Internal error | GCP backend error | Retry; escalate if persistent | Report to GCP Support |
| KEY_DISABLED | Key disabled | Attempting crypt op with DISABLED key | Enable key version | Enable and retry |
| KEY_DESTROYED | Key destroyed | Attempting decrypt with DESTROYED key | Key is gone; use backup | Restore from backup key |
| EXTERNAL_KEY_UNAVAILABLE | External key down | External key manager unreachable | Check external KMS connectivity | Contact key provider |

## Diagnostic Order

```
1. Auth check     → gcloud auth print-access-token
2. Project check  → gcloud config get-value project
3. API status     → gcloud services list --enabled | grep cloudkms.googleapis.com
4. Resource check → gcloud kms keyrings list --location=LOC
5. Key exists     → gcloud kms keys describe KEY --keyring=KR --location=LOC
6. Version state  → gcloud kms keys versions list --key=KEY --keyring=KR --location=LOC
7. IAM check      → gcloud kms keys get-iam-policy KEY --keyring=KR --location=LOC
```

## Common Issues

### "Key not found"
```bash
# Verify full resource name
gcloud kms keys list --keyring="{{user.keyring_name}}" --location="{{user.location}}" --format="json"
```

### "Permission denied on encrypt/decrypt"
Add IAM binding with the encrypt/decrypt role:
```bash
gcloud kms keys add-iam-policy-binding "{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --member="serviceAccount:SA@project.iam.gserviceaccount.com" \
  --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"
```

### "Destroy scheduled key version needs restore"
```bash
# Check version state
gcloud kms keys versions describe "{{user.key_version}}" \
  --key="{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location}}" \
  --format="json" | jq '{name,state,destroyEvent.destroyScheduledTime}'

# Restore within 24 hours
gcloud kms keys versions restore "{{user.key_version}}" \
  --key="{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location}}" \
  --format="json"
```

### "Encrypt request throttled"
```bash
# Check current rate limits
# Software keys: 6,000 requests/min
# HSM keys: 600 requests/min
# Reduce call rate or request quota increase
```

## Error Recovery Patterns

### Retry with backoff
```bash
for i in 1 2 3; do
  gcloud kms keys describe "my-key" --keyring="my-keyring" --location=global --format="json" && break
  echo "⚠️  Retry $i/3..."
  sleep $((2**i))
done
```

### Idempotent create
```bash
if ! gcloud kms keyrings describe "my-keyring" --location=global --quiet 2>/dev/null; then
  gcloud kms keyrings create "my-keyring" --location=global
fi
```