# Idempotency Checklist — Cloud IAM

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Custom Role | role_id (project-unique) | ALREADY_EXISTS / 409 — duplicate |
| Service Account | account_id (project-unique) | ALREADY_EXISTS / 409 — duplicate |
| SA Key | Key ID (SA-unique) | ALREADY_EXISTS if same key uploaded |
| Workload Identity Pool | pool_id (project-unique) | ALREADY_EXISTS / 409 |
| Workload Provider | provider_id (pool-unique) | ALREADY_EXISTS / 409 |

## Update

| Operation | Idempotent? |
|-----------|-------------|
| Set IAM policy with same etag | Yes (same policy = no-op) |
| Add IAM binding (same member + role) | Yes (binding deduplication) |
| Remove IAM binding (non-existent binding) | Yes (no-op) |
| Update custom role (same permissions) | Yes (same content = no-op) |
| Add permission to role (already included) | Yes (no-op) |
| Remove permission from role (not present) | Yes (no-op) |

## Delete

| Resource | Retry Safe? |
|----------|-------------|
| Custom Role | Safe — deleted role shows DISABLED stage on second attempt |
| Service Account | Safe — NOT_FOUND on second attempt |
| SA Key | Safe — NOT_FOUND on second attempt |
| Deny Policy | Safe — NOT_FOUND on second attempt |
| Workload Identity Pool | Safe — NOT_FOUND on second attempt |

## Safe Retry Pattern

### Custom Role Create
```bash
if ! gcloud iam roles describe "{{user.role_id}}" --project="{{user.project}}" --quiet 2>/dev/null; then
    gcloud iam roles create "{{user.role_id}}" \
      --project="{{user.project}}" \
      --title="{{user.role_title}}" \
      --permissions="{{user.permissions}}" \
      --stage="GA"
else
    echo "Custom role already exists — no action needed"
fi
```

### Service Account Create
```bash
SA_EMAIL="{{user.sa_name}}@{{env.CLOUDSDK_CORE_PROJECT}}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SA_EMAIL" --quiet 2>/dev/null; then
    gcloud iam service-accounts create "{{user.sa_name}}" \
      --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
      --display-name="{{user.sa_display_name}}"
else
    echo "Service account already exists — no action needed"
fi
```

### IAM Policy Set (Idempotent)
```bash
# Get current policy, modify, set — same policy = no-op
gcloud projects get-iam-policy "{{user.project}}" --format=json > /tmp/policy.json
# (modify policy.json)
gcloud projects set-iam-policy "{{user.project}}" /tmp/policy.json --format=json
```

## Label and Description De-Duplication

```bash
# For idempotent SA creation with consistent metadata
gcloud iam service-accounts create "{{user.sa_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --display-name="Managed by gcp-skills ({{user.purpose}})"
```