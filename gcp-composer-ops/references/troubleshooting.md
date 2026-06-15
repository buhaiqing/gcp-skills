# Troubleshooting — Google Cloud Composer

## Common API Error Codes

| gRPC Code / HTTP | Meaning | Agent Action |
|-------------------|---------|--------------|
| `INVALID_ARGUMENT` / 400 | Invalid request body or parameters | Align with REST API reference |
| `UNAUTHENTICATED` / 401 | Authentication failed | Check credentials; refresh token |
| `PERMISSION_DENIED` / 403 | Insufficient IAM permissions | Grant `roles/composer.admin` |
| `NOT_FOUND` / 404 | Environment does not exist | Verify environment name and region |
| `ALREADY_EXISTS` / 409 | Duplicate environment | Use different name or update existing |
| `RESOURCE_EXHAUSTED` / 429 | Rate limit exceeded | Implement exponential backoff |
| `FAILED_PRECONDITION` / 400 | Resource not in valid state | Wait for pending operations to complete |
| `ABORTED` / 409 | Operation conflict | Retry after current operation completes |
| `INTERNAL` / 500 | Server-side error | Retry with backoff; then HALT |
| `UNAVAILABLE` / 503 | Service temporarily unavailable | Retry with exponential backoff |
| `DATA_LOSS` / 15 | Unrecoverable data loss | HALT; escalate to support |

## Diagnostic Order

1. Describe environment by name and region
2. Check environment state and pending operations
3. Verify GKE cluster health
4. Check Cloud SQL connectivity
5. Verify Cloud Storage access
6. Check Cloud Logging for detailed error messages
7. Verify gcloud metadata coverage: `gcloud composer --help`

## Common Issues

| Issue | Symptoms | Resolution |
|-------|----------|------------|
| Environment stuck in CREATING | Long creation time | Check GKE cluster provisioning; verify quotas |
| DAGs not appearing | DAGs not in Airflow UI | Check Cloud Storage import; verify DAG syntax |
| Workers not starting | Tasks not executing | Check GKE node pools; verify worker configuration |
| Webserver not accessible | Cannot access Airflow UI | Check firewall rules; verify web server status |
| High latency | Slow task execution | Increase environment size; optimize DAGs |
| Package installation failed | PyPI packages not available | Check network access; verify package versions |
