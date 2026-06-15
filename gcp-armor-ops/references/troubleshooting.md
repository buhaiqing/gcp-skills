# Troubleshooting — Google Cloud Armor

## Common API Error Codes

| gRPC Code / HTTP | Meaning | Agent Action |
|-------------------|---------|--------------|
| `INVALID_ARGUMENT` / 400 | Invalid request body or parameters | Align with REST API reference; check expression syntax |
| `UNAUTHENTICATED` / 401 | Authentication failed | Check credentials; refresh token |
| `PERMISSION_DENIED` / 403 | Insufficient IAM permissions | Grant `roles/compute.securityAdmin` |
| `NOT_FOUND` / 404 | Resource does not exist | Verify policy/rule name |
| `ALREADY_EXISTS` / 409 | Duplicate resource | Use different name or update existing |
| `RESOURCE_EXHAUSTED` / 429 | Rate limit exceeded | Implement exponential backoff |
| `FAILED_PRECONDITION` / 400 | Resource not in valid state | Wait for pending operations to complete |
| `ABORTED` / 409 | Operation conflict | Retry after current operation completes |
| `INTERNAL` / 500 | Server-side error | Retry with backoff; then HALT |
| `UNAVAILABLE` / 503 | Service temporarily unavailable | Retry with exponential backoff |
| `DATA_LOSS` / 15 | Unrecoverable data loss | HALT; escalate to support |

## Diagnostic Order

1. Describe security policy by name
2. List all rules in the policy
3. Check rule expressions for syntax errors
4. Verify no conflicting rules exist
5. Check Cloud Logging for detailed error messages
6. Verify gcloud metadata coverage: `gcloud compute security-policies --help`

## Common Issues

| Issue | Symptoms | Resolution |
|-------|----------|------------|
| Rule not matching | Requests not blocked | Check expression syntax; verify priority order |
| Rate limit not working | Requests not throttled | Verify throttle action parameters |
| WAF blocking legitimate traffic | 403 errors for valid requests | Adjust rule expression or priority |
| Policy not attached | Armor not protecting backend | Attach policy to backend service via LB |
