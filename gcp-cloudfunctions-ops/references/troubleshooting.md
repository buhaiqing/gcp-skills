# Troubleshooting — Cloud Functions

## Error Taxonomy (15 Codes)

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| `invalidArgument` | 400 | Invalid function configuration | Fix params per REST API; check runtime, memory, timeout values |
| `permissionDenied` | 403 | Insufficient IAM permissions | HALT — grant roles/cloudfunctions.admin (or specific role needed) |
| `notFound` | 404 | Function does not exist | Verify function name, region, project; use list to find |
| `alreadyExists` | 409 | Function name already exists | Use update flow (deploy existing name updates) |
| `failedPrecondition` | 412 | Function in invalid state for operation | HALT — wait for function to reach ACTIVE state |
| `resourceExhausted` | 429 | Quota exceeded (functions, memory, executions) | HALT — check quotas; request increase or reduce resource usage |
| `aborted` | 409 | Concurrent modification conflict | Retry 3x with exponential backoff (1s, 2s, 4s) |
| `deadlineExceeded` | 504 | Deployment timeout | Retry; check network, build time, source size |
| `internal` | 500 | Server-side error | Retry 3x with 2s/4s/8s backoff; then HALT |
| `unavailable` | 503 | Cloud Functions temporarily unavailable | Retry 3x with exponential backoff |
| `functionFailed` | 400 | Function execution error (runtime error) | Check logs; fix function code; redeploy |
| `sourceUploadError` | 400 | Source code upload failed | HALT — verify source dir, size (<500MB), permissions |
| `buildFailed` | 400 | Buildpack build failed | HALT — check runtime compatibility, dependencies, syntax |
| `imagePullError` | 400 | Container image pull failed | HALT — verify image path, registry permissions |
| `deploymentFailed` | 400 | General deployment failure | Check build logs; verify all config parameters |

## Diagnostic Decision Tree

```
Function issue detected
├── Deployment failure
│   ├── Check build logs → buildFailed → Fix source/runtime
│   ├── Check source upload → sourceUploadError → Verify source dir/size
│   ├── Check IAM → permissionDenied → Grant required role
│   ├── Check quotas → resourceExhausted → Request quota increase
│   └── Check network → deadlineExceeded → Retry or check connectivity
├── Runtime failure (function runs but errors)
│   ├── Check function logs → functionFailed → Fix code
│   ├── Check memory → Out of memory → Increase memory allocation
│   ├── Check timeout → Timeout → Increase timeout or optimize code
│   ├── Check permissions → Service account IAM → Grant required roles
│   └── Check dependencies → Missing package → Add to requirements
├── Invocation failure (cannot call function)
│   ├── Check URL → notFound → Verify function name/region
│   ├── Check auth → permissionDenied → Grant invoker role or make public
│   ├── Check trigger type → Wrong trigger → HTTP functions only for call
│   └── Check network → Firewall/ingress → Adjust ingress settings
├── Event trigger failure
│   ├── Check event source → notFound → Create bucket/topic
│   ├── Check Eventarc → permissionDenied → Grant eventarc.admin
│   ├── Check event filter → invalidArgument → Fix filter syntax
│   └── Check service account → permissionDenied → Grant event receiver role
└── Scaling issue
    ├── Check min-instances → Cold starts → Set min-instances > 0
    ├── Check max-instances → Throttling → Increase max-instances
    ├── Check concurrency → Low throughput → Increase concurrency
    └── Check memory → OOM → Increase memory allocation
```

## Common Failure Patterns

### Cold Start Issues

**Symptoms**: First invocation takes 2-10+ seconds.

**Diagnosis**:
```bash
# Check if min-instances is 0
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq '.serviceConfig.minInstanceCount'

# Check cold start duration from logs
gcloud functions logs read NAME --gen2 --region=REGION --limit=50 --format=json | jq '[.[] | select(.textPayload | contains("cold start"))]'
```

**Resolution**:
- Set `--min-instances=1` (or higher) for critical functions
- Allocate more CPU (reduces cold start time)
- Reduce deployment package size
- Use provisioned concurrency (min-instances)

### Timeout Issues

**Symptoms**: Function fails with 504 or deadline exceeded.

**Diagnosis**:
```bash
# Check current timeout
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq '.serviceConfig.timeoutSeconds'

# Check function execution time from logs
gcloud functions logs read NAME --gen2 --region=REGION --min-log-level=error --limit=20
```

**Resolution**:
- Increase `--timeout` (max 3600s for gen2)
- Optimize function code for faster execution
- Use async processing for long tasks
- Split function into smaller units

### Memory Issues

**Symptoms**: Function fails with Out of Memory (OOM) error.

**Diagnosis**:
```bash
# Check current memory
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq '.serviceConfig.availableMemory'

# Check memory usage from Cloud Monitoring
gcloud monitoring metrics list --filter='metric.type="cloudfunctions.googleapis.com/function/memory_usage"'
```

**Resolution**:
- Increase `--memory` allocation (128Mi to 32Gi for gen2)
- Optimize memory usage in function code
- Use streaming for large data processing
- Check for memory leaks in long-running instances

### Build Failures

**Symptoms**: Deployment fails with buildFailed error.

**Diagnosis**:
```bash
# Check build logs
gcloud functions logs read NAME --gen2 --region=REGION --limit=50 --format=json | jq '[.[] | select(.textPayload | contains("build"))]'

# Check runtime compatibility
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq '.buildConfig.runtime'
```

**Resolution**:
- Verify runtime version matches source code
- Check dependency files (requirements.txt, package.json, go.mod, etc.)
- Ensure entry point name matches function name in code
- Check for syntax errors in source code
- Verify source directory contains all required files

### VPC Connector Issues

**Symptoms**: Function cannot access private resources.

**Diagnosis**:
```bash
# Check VPC connector configuration
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq '.serviceConfig.vpcConnector'

# Verify connector exists and is active
gcloud compute networks vpc-access connectors describe CONNECTOR --region=REGION --format=json
```

**Resolution**:
- Verify VPC connector exists and is in READY state
- Ensure function SA has roles/vpcaccess.user role
- Check VPC egress settings (all-traffic vs private-ranges-only)
- Verify firewall rules allow function egress
- Delegate to `gcp-vpc-ops` for connector setup

### Secret Manager Issues

**Symptoms**: Function fails to access mounted secrets.

**Diagnosis**:
```bash
# Check secret configuration
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq '.serviceConfig.secretEnvironmentVariables'

# Verify secret exists
gcloud secrets describe SECRET_NAME --format=json
```

**Resolution**:
- Verify secret exists and has active versions
- Ensure function SA has roles/secretmanager.secretAccessor role
- Check secret version (use "latest" or specific version)
- Verify secret name format in `--set-secrets` flag
- Delegate to `gcp-secretmanager-ops` for secret management

### Event Trigger Issues

**Symptoms**: Event-triggered function not receiving events.

**Diagnosis**:
```bash
# Check event trigger configuration
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq '.eventTrigger'

# Check Eventarc triggers
gcloud eventarc triggers list --location=REGION --format=json | jq '[.[] | {name: .name, eventFilters: .eventFilters}]'

# Check event source exists
gcloud storage buckets describe gs://BUCKET_NAME 2>&1
```

**Resolution**:
- Verify event source (bucket, topic, etc.) exists
- Check event filter syntax (type=...,bucket=...,topic=...)
- Ensure function SA has roles/eventarc.eventReceiver role
- Verify Eventarc API is enabled
- Check Cloud Audit Logs for event delivery failures

### Concurrent Instance Limit

**Symptoms**: Function invocations are throttled or queued.

**Diagnosis**:
```bash
# Check current max-instances
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq '.serviceConfig.maxInstanceCount'

# Check active instances
gcloud functions logs read NAME --gen2 --region=REGION --limit=10 --format=json | jq '[.[] | select(.textPayload | contains("instance"))]'
```

**Resolution**:
- Increase `--max-instances` (max 1000 for HTTP, 10000 for events)
- Tune concurrency (higher = fewer instances needed)
- Check project-level concurrency quotas
- Implement request queuing or backpressure

## Debugging Checklist

```
☐ 1. gcloud version: gcloud version
☐ 2. Auth status: gcloud auth list
☐ 3. Project set: gcloud config get-value project
☐ 4. API enabled: gcloud services list --filter="cloudfunctions.googleapis.com"
☐ 5. Build API enabled: gcloud services list --filter="cloudbuild.googleapis.com"
☐ 6. Function exists: gcloud functions describe NAME --gen2 --region=REGION
☐ 7. Function state: .state == "ACTIVE"
☐ 8. Function URL: .serviceConfig.uri is populated
☐ 9. Function logs: gcloud functions logs read NAME --gen2 --region=REGION --limit=20
☐ 10. IAM policy: gcloud functions get-iam-policy NAME --gen2 --region=REGION
☐ 11. Quotas: gcloud services quotas list --service=cloudfunctions.googleapis.com
☐ 12. Network: Verify VPC connector (if used) and ingress settings
```

## Recovery Procedures

### Function Stuck in DEPLOYING State

```bash
# 1. Check function state
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq '{state: .state, updateTime: .updateTime}'

# 2. If stuck > 10 minutes, check Cloud Build
gcloud builds list --filter="status=WORKING" --limit=5 --format=json

# 3. Cancel stuck build (if found)
gcloud builds cancel BUILD_ID

# 4. Retry deployment
gcloud functions deploy NAME --gen2 --runtime=RUNTIME --trigger-http --entry-point=EP --source=DIR --region=REGION
```

### Function in FAILED State

```bash
# 1. Get failure details
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq '{state: .state, serviceConfig: .serviceConfig.status}'

# 2. Check logs for error
gcloud functions logs read NAME --gen2 --region=REGION --min-log-level=error --limit=20

# 3. Fix identified issue and redeploy
gcloud functions deploy NAME --gen2 --runtime=RUNTIME --trigger-http --entry-point=EP --source=DIR --region=REGION
```

### Accidental Deletion Recovery

> **Warning**: Cloud Functions deletion is irreversible. There is no built-in undo.

**Prevention**:
- Always obtain explicit confirmation before delete
- Document function configuration before delete:
  ```bash
  gcloud functions describe NAME --gen2 --region=REGION --format=json > function-backup-$(date +%Y%m%d).json
  ```
- Use source control for function code
- Consider `--min-instances=0` + disabling instead of delete:
  ```bash
  # Alternative to delete: scale to 0 and remove IAM
  gcloud functions deploy NAME --gen2 --runtime=RUNTIME --entry-point=EP --source=DIR --region=REGION --min-instances=0
  gcloud functions remove-iam-policy-binding NAME --gen2 --region=REGION --member="allUsers" --role="roles/cloudfunctions.invoker"
  ```

**Recovery**: Redeploy from source using documented configuration.
