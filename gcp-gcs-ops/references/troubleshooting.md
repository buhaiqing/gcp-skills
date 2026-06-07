# Troubleshooting — Cloud Storage

## Error Codes

| HTTP | gRPC | Meaning | Agent Action |
|------|------|---------|--------------|
| 400 | INVALID_ARGUMENT | Request validation failed | Fix parameter per API reference |
| 403 | PERMISSION_DENIED | Insufficient IAM | Grant storage.objectAdmin or storage.admin |
| 404 | NOT_FOUND | Bucket or object not found | Verify bucket name and object path |
| 409 | ALREADY_EXISTS | Bucket name already taken | Choose globally unique name |
| 412 | FAILED_PRECONDITION | Generation/metageneration mismatch | Retry with fresh generation number |
| 429 | QUOTA_EXCEEDED | Rate limit or bucket quota exceeded | Implement backoff; request increase |
| 500 | INTERNAL | Server error | Retry with backoff; then escalate |
| 503 | UNAVAILABLE | Service unavailable | Retry with exponential backoff |
| — | BILLING_NOT_ENABLED | Billing not active | Enable in Cloud Console |
| — | BUCKET_NOT_EMPTY | Delete attempted on non-empty bucket | Verify empty or force empty with rm -r |
| — | RETENTION_POLICY_LOCKED | Cannot modify locked retention | Only extension (lengthening) is allowed |
| — | OBJECT_NOT_FOUND | Object does not exist at path | Check object path and bucket name |
| — | SIGNED_URL_EXPIRED | Signed URL has expired | Generate new signed URL |
| — | CORS_MISMATCH | Origin not allowed by CORS policy | Update CORS configuration |
| — | SOFT_DELETED_BUCKET | Bucket was recently deleted | Recover within soft-delete window |
| — | SOFT_DELETED_OBJECT | Object was soft-deleted | Recover with gcloud storage objects restore |
| — | INVALID_ENCRYPTION_KEY | CSEK key is invalid or wrong | Verify base64-encoded key |
| — | KMS_KEY_PERMISSION | SA lacks permission on KMS key | Grant cloudkms.cryptoKeyEncrypterDecrypter |
| — | VPC_SERVICE_CONTROLS | Access blocked by perimeter | Check VPC SC policy |
| — | PUBLIC_ACCESS_PREVENTION | Blocked by PAP policy | Disable public access prevention if appropriate |

## Diagnostic Order

1. Check bucket exists: `gcloud storage buckets describe gs://B --format=json`
2. Check object exists: `gsutil stat gs://B/O`
3. Check permissions: `gcloud storage buckets get-iam-policy gs://B --format=json`
4. Check bucket config: `gcloud storage buckets describe gs://B --format=json | jq '{versioning, encryption, retentionPolicy, lifecycle}'`
5. Check rate limits: Implement exponential backoff on 429 responses
6. Check Cloud Logging: resource.type="gcs_bucket"
7. Check VPC Service Controls if applicable

## Common Issues

### Bucket Won't Create
- Name not globally unique: ALREADY_EXISTS → try a more specific name
- Project quota exhausted: request increase
- Incompatible location/storage class: verify location supports the storage class
- Soft-deleted bucket: wait for soft-delete expiration or use different name

### Upload Fails
- Invalid encryption key: CSEK must be base64-encoded 256-bit AES key
- CORS preflight failure: configure CORS on bucket
- Object too large: use parallel composite uploads or gsutil cp with -o GSUtil:parallel_composite_upload_threshold
- Quota exceeded: reduce concurrency, implement backoff

### Download Fails
- Version not found: specify correct generation/version ID
- Signed URL expired: regenerate with appropriate duration
- Permission denied: check IAM roles

### Retention Policy Issues
- Cannot delete object under retention: wait for retention period to expire
- Cannot modify locked policy: only lengthening allowed
- Cannot remove retention: lock is permanent — see SKILL.md extreme safety gate

### Object Listing Slow
- Too many objects: use prefix/delimiter for paginated listing
- Too many versions: add --all-versions only when needed

### Soft-Deleted Bucket or Object Recovery

**Bucket (within soft-delete window, default 7 days):**
```bash
# List soft-deleted buckets
gcloud storage buckets list --soft-deleted --format="json"

# Restore a soft-deleted bucket
gcloud storage buckets restore "gs://{{user.bucket_name}}" --format="json"

# Create with same name by overriding soft-delete
gcloud storage buckets create "gs://{{user.bucket_name}}" --soft-delete-duration=0 --format="json"
```

**Object (within soft-delete window):**
```bash
# List soft-deleted objects
gcloud storage objects list "gs://{{user.bucket_name}}" --soft-deleted --format="json"

# Restore a soft-deleted object
gcloud storage objects restore "gs://{{user.bucket_name}}/{{user.object_name}}" --format="json"
```

### Lifecycle Rules Not Applying
- Rules evaluated once per day: be patient
- Storage class conflict: Autoclass and manual lifecycle may conflict
- Condition not met: verify condition format (age, createdBefore, matchesStorageClass, numNewerVersions)