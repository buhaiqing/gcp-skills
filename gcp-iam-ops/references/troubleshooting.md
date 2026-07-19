# Troubleshooting — Cloud IAM

> 错误码遵循 docs/error-taxonomy.md — product-specific codes MUST map to a root-cause dimension above.

## Error Codes

| gRPC/HTTP | Meaning | Agent Action |
|-----------|---------|--------------|
| INVALID_ARGUMENT / 400 | Request validation failed | Fix parameter per API reference |
| PERMISSION_DENIED / 403 | Insufficient IAM | Grant iam.securityAdmin or appropriate role |
| NOT_FOUND / 404 | Resource not found | Verify resource name, project, and location |
| ALREADY_EXISTS / 409 | Resource already exists | Choose unique name (role ID, SA name, key ID) |
| ABORTED / 409 | Etag conflict or concurrent modification | Re-fetch policy and retry with fresh etag |
| QUOTA_EXCEEDED / 429 | Quota limit exceeded | Request increase or clean up unused resources |
| FAILED_PRECONDITION / 400 | Wrong state for operation | Enable SA before key ops; delete keys before SA |
| INTERNAL / 500 | Server error | Retry, then escalate |
| UNAVAILABLE / 503 | Service unavailable | Retry with backoff |
| RESOURCE_EXHAUSTED / 429 | Too many concurrent requests | Reduce concurrency; wait before retrying |
| `CONDITION_NOT_SUPPORTED` | Policy version too low for conditions | Set policy version to 3 |
| `POLICY_SIZE_EXCEEDED` | Policy JSON exceeds 250KB limit | Remove unnecessary bindings |
| `ROLE_NOT_FOUND` | Role does not exist | Verify role name and project |
| `STAGE_NOT_ALLOWED` | Role stage does not allow operation | Use GA stage for production |
| `SA_DISABLED` | Service account is disabled | Enable the SA first |
| `KEY_NOT_FOUND` | Key ID does not exist | Verify key ID in key list |
| `MAX_KEYS_EXCEEDED` | Too many keys per SA (max 10) | Delete unused keys first |
| `BILLING_NOT_ENABLED` | Billing inactive | Enable in Cloud Console |

## Diagnostic Order

1. **Describe resource**: `gcloud iam service-accounts describe SA_EMAIL --format=json`
2. **List permissions**: `gcloud iam test-iam-permissions RESOURCE --permissions=PERMS --format=json`
3. **Check policy**: `gcloud projects get-iam-policy PROJECT --format=json`
4. **Check quotas**: `gcloud projects describe PROJECT --format=json`
5. **Check audit logs**: `gcloud logging read 'protoPayload.methodName="SetIamPolicy"' --limit=10`
6. **Check API enablement**: `gcloud services list --enabled | grep iam.googleapis.com`

## Common Issues

### Permission Denied (403)

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `PERMISSION_DENIED` on `setIamPolicy` | SA lacks `iam.policies.set` | Grant `roles/iam.securityAdmin` |
| `PERMISSION_DENIED` on role operations | SA lacks `iam.roles.*` | Grant `roles/iam.roleAdmin` |
| `PERMISSION_DENIED` on SA operations | SA lacks `iam.serviceAccounts.*` | Grant `roles/iam.serviceAccountAdmin` |
| `PERMISSION_DENIED` on asset analysis | Cloud Asset API not enabled | Enable `cloudasset.googleapis.com` |
| `PERMISSION_DENIED` on deny policies | SA lacks `iam.denyPolicies.*` | Grant `roles/iam.denyAdmin` |

### Etag Conflict

```bash
# Re-fetch the policy to get a fresh etag
gcloud projects get-iam-policy "{{user.project}}" --format=json > /tmp/fresh-policy.json
# Then modify and set
gcloud projects set-iam-policy "{{user.project}}" /tmp/fresh-policy.json --format=json
```

### Service Account Key Issues

```bash
# Key not found — list all keys first
gcloud iam service-accounts keys list --iam-account="{{user.service_account_email}}" --managed-by="user"

# Key expired — create a new key
gcloud iam service-accounts keys create /tmp/new-key.json --iam-account="{{user.service_account_email}}"

# Too many keys (max 10) — delete unused ones
gcloud iam service-accounts keys list --iam-account="{{user.service_account_email}}" --managed-by="user" --format="json" | jq -r '.keys[].name'
```

### SA Deletion Fails

```bash
# Check if SA still has dependent resources
# 1. Check keys
gcloud iam service-accounts keys list --iam-account="{{user.service_account_email}}" --managed-by="user"
# 2. Check IAM bindings for the SA itself
gcloud iam service-accounts get-iam-policy "{{user.service_account_email}}"
# SA must be disabled before deletion (gcloud handles this automatically)
```

### IAM Deny Policy Issues

```bash
# Check deny policy syntax
gcloud iam deny-policies describe "{{user.deny_policy_id}}" --format=json

# Verify deny policy is affecting expected principals
gcloud asset analyze-iam-policy --scope="projects/{{user.project}}" --principal="user:{{user.member}}" --format=json
```