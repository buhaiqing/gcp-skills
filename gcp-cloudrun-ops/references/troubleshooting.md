# Troubleshooting — Cloud Run

## Error Taxonomy (13+ Codes)

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| invalidArgument | 400 | Invalid deployment configuration | Fix params; check CPU/memory/timeout limits |
| permissionDenied | 403 | Insufficient IAM (needs roles/run.admin) | HALT — grant IAM role |
| notFound | 404 | Service or revision does not exist | HALT — verify name + region |
| alreadyExists | 409 | Service name already exists | Rename service |
| failedPrecondition | 412 | Service in invalid state for operation | Wait for Ready; retry |
| resourceExhausted | 429 | Quota exceeded (max services, CPU, memory) | HALT — increase quota |
| aborted | 409 | Concurrent modification conflict | Retry 3x with backoff |
| deadlineExceeded | 504 | Deployment timeout | Retry; check container startup time |
| internal | 500 | Server-side error | Retry 3x; then HALT |
| unavailable | 503 | Cloud Run temporarily unavailable | Retry 3x with backoff |
| revisionFailed | 400 | Container pull failed or startup probe failed | HALT — check image + logs |
| imagePullError | 400 | Registry access denied or image not found | HALT — check SA perms + image path |
| containerHealthCheckFailed | 503 | Container failed health check | HALT — check port + startup logic |

## Diagnostic Order

1. **Describe service** to check current state and conditions:
   ```bash
   gcloud run services describe NAME --region=REGION --format=json | jq '.status.conditions'
   ```

2. **Check revision status** for the failing revision:
   ```bash
   gcloud run revisions list --service=NAME --region=REGION --format=json | jq '.[] | {name: .metadata.name, conditions: .status.conditions}'
   ```

3. **Check Cloud Run logs**:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=NAME" --limit=50 --format=json
   ```

4. **Verify region/project consistency**:
   ```bash
   gcloud config get-value project
   gcloud config get-value run/region
   ```

5. **Check IAM permissions**:
   ```bash
   gcloud projects get-iam-policy PROJECT --flatten="bindings[].members" --format="table(bindings.role)" | grep run
   ```

6. **Check quotas**:
   ```bash
   gcloud services quotas list --service=run.googleapis.com --format=json
   ```

## Common Scenarios

### Revision Failed to Start

**Symptoms**: Service created but URL returns 503, `.status.conditions[].type=Ready` is False.

**Root causes**:
1. Container image not pullable (imagePullError)
2. Container does not listen on configured port (healthCheckFailed)
3. Container crashes on startup (revisionFailed)

**Resolution**:
```bash
# Check revision conditions
gcloud run revisions describe REVISION --region=REGION --format=json | jq '.status.conditions[] | select(.status=="False")'

# Check logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.revision_name=REVISION" --limit=20 --format=json | jq -r '.[].textPayload'

# Verify image accessibility
gcloud artifacts docker images list LOCATION-docker.pkg.dev/PROJECT/REPO --format=json
```

### Cold Start Latency

**Symptoms**: First request after idle period takes 5-15 seconds.

**Resolution**:
```bash
# Set min-instances > 0 to avoid cold starts (cost tradeoff)
gcloud run services deploy NAME --min-instances=1 --region=REGION --project=PROJECT
```

### Traffic Split Not Working

**Symptoms**: Traffic percentages don't match expected distribution.

**Resolution**:
```bash
# Check current traffic
gcloud run services describe NAME --region=REGION --format=json | jq '.status.traffic'

# Verify revisions are Ready
gcloud run revisions list --service=NAME --region=REGION --format=json | jq '.[] | {name: .metadata.name, ready: (.status.conditions[] | select(.type=="Ready") | .status)}'

# Re-apply traffic split
gcloud run services update-traffic NAME --to-revisions=REV1=50,REV2=50 --region=REGION --project=PROJECT
```

### Permission Denied on Deploy

**Symptoms**: 403 error on create/deploy.

**Resolution**:
```bash
# Check current roles
gcloud projects get-iam-policy PROJECT --format=json | jq '.bindings[] | select(.role | test("run"))'

# Grant admin role
gcloud projects add-iam-policy-binding PROJECT \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/run.admin"
```

### VPC Connector Connection Failed

**Symptoms**: Service deployed but cannot reach VPC resources.

**Resolution**:
```bash
# Verify connector exists and is Ready
gcloud compute networks vpc-access connectors describe CONNECTOR --region=REGION --format=json

# Verify service has connector attached
gcloud run services describe NAME --region=REGION --format=json | jq '.spec.template.spec.vpcAccess'

# Check VPC Serverless Access role
gcloud projects get-iam-policy PROJECT --format=json | jq '.bindings[] | select(.role | test("vpcaccess"))'
```

### Quota Exceeded

**Symptoms**: 429 error on create.

**Resolution**:
```bash
# Check current quota usage
gcloud services quotas list --service=run.googleapis.com --format=json | jq '.[] | {name: .name, value: .value, usage: .usage}'

# Request quota increase via Cloud Console or:
gcloud support cases create --classification="Technical" --component="Cloud Run API" --description="Quota increase request"
```
