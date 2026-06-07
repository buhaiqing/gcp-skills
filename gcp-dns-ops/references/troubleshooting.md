# Troubleshooting — Cloud DNS

## Error Code Taxonomy (12+ Codes)

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| `invalidName` | 400 | Invalid DNS name format | HALT; validate DNS name format |
| `invalidChange` | 400 | Invalid DNS change request | HALT; verify record name, type, data |
| `insufficientPermissions` | 403 | Missing IAM permissions | HALT; grant roles/dns.admin |
| `forbidden` | 403 | Insufficient permissions | HALT; check IAM bindings |
| `notFound` | 404 | Zone or record-set does not exist | HALT; verify resource name |
| `badZoneState` | 412 | Zone in invalid state | HALT; wait for operations to complete |
| `alreadyExists` | 409 | Record-set already exists | HALT; use update or remove first |
| `operationAborted` | 409 | Concurrent modification conflict | Retry 3x with exponential backoff |
| `quotaExceeded` | 429 | DNS quota limit reached | HALT; request quota increase |
| `rateLimited` | 429 | API rate limit exceeded | Retry with backoff; respect Retry-After |
| `serverFailure` | 500 | Server-side DNS failure | Retry 3x with backoff |
| `serviceNotReady` | 503 | DNS service temporarily unavailable | Retry 3x with exponential backoff |

## Diagnostic Order

1. **Describe zone** by name to verify existence and state:
   ```bash
   gcloud dns managed-zones describe "{{user.zone_name}}" \
     --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
   ```

2. **List zones** if name unknown or verifying project context:
   ```bash
   gcloud dns managed-zones list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
   ```

3. **Check zone operations** for pending/conflicting operations:
   ```bash
   gcloud dns managed-zone operations list --zone="{{user.zone_name}}" \
     --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
   ```

4. **Verify credentials and permissions**:
   ```bash
   gcloud auth describe --format=json
   gcloud projects get-iam-policy "{{env.CLOUDSDK_CORE_PROJECT}}" \
     --flatten="bindings[].members" --format="table(bindings.role)" \
     --filter="bindings.members:serviceAccount"
   ```

5. **Check DNS resolution** (post-change verification):
   ```bash
   # Query specific name server
   dig @{{output.name_servers[0]}} "{{user.record_name}}" "{{user.record_type}}"
   
   # Query with trace
   dig +trace "{{user.record_name}}" "{{user.record_type}}"
   ```

## Common Issues and Fixes

### Zone Creation Fails

| Symptom | Cause | Fix |
|---------|-------|-----|
| `invalidName / 400` | DNS name missing trailing dot or invalid format | Use valid domain name (e.g., `example.com.`) |
| `alreadyExists / 409` | Zone name or DNS name already in use | Use different zone name or describe existing zone |
| `quotaExceeded / 429` | Max zones reached for project | Delete unused zones or request quota increase |
| `forbidden / 403` | Missing DNS Admin role | Grant `roles/dns.admin` to service account |

### Record-Set Changes Fail

| Symptom | Cause | Fix |
|---------|-------|-----|
| `invalidChange / 400` | Malformed record data for type | Validate data format (e.g., valid IP for A records) |
| `alreadyExists / 409` | Record already exists | Use `transaction remove` then `transaction add` for update |
| `operationAborted / 409` | Concurrent zone modification | Retry with backoff |
| `notFound / 404` | Zone does not exist | Verify zone name with `managed-zones list` |

### DNS Resolution Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Records not resolving | NS delegation not configured at registrar | Add Google name servers to registrar |
| Stale records | High TTL or downstream caching | Lower TTL before changes; wait for propagation |
| Private zone not resolving | VPC not bound to zone | Add VPC network to zone's privateVisibilityConfig |
| NXDOMAIN for valid record | Record does not exist in zone | Verify with `record-sets list` |

### DNSSEC Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| DNSSEC validation fails | DS record not published at registrar | Add DS record from DNS key to registrar |
| Zone stuck in `transfer` state | DNSSEC state change in progress | Wait for completion; check operations |

## Structured Diagnostic Log Format

All CLI and SDK scripts use structured logging:

```
[HH:MM:SS] [DIAG] check_dns_name=valid zone=example-zone
[HH:MM:SS] [EXEC] gcloud dns managed-zones create example-zone
[HH:MM:SS] [RESULT] zone_created=true name_servers=4
[HH:MM:SS] [ERROR] TYPE=invalidName FIX=validate_dns_name_format
[HH:MM:SS] [SUMMARY] operation=create_zone status=success duration=3.2s
```

## Escalation

If issues persist after following diagnostic steps:

1. Collect operation ID from `managed-zone operations list`
2. Capture full error response with `--format=json`
3. File support case with operation ID, project ID, and error details
