# Troubleshooting — Memorystore for Redis

## Error Codes

| Code | Summary | Explanation | Remediation | Next Step |
|------|---------|-------------|-------------|-----------|
| INVALID_ARGUMENT / 400 | Invalid parameter | Memory size, version, or config invalid | Fix parameter from error | Retry with corrected value |
| PERMISSION_DENIED / 403 | No IAM access | SA lacks redis.* role | Grant roles/redis.admin | Check IAM bindings |
| NOT_FOUND / 404 | Resource missing | Instance or region doesn't exist | Verify name and region | List instances to confirm |
| ALREADY_EXISTS / 409 | Duplicate name | Instance name in use in region | Use different name | Rename and retry |
| QUOTA_EXCEEDED / 429 | Quota exhausted | Exceeded max instances or total memory | Request quota increase or delete unused | Check quotas in Console |
| FAILED_PRECONDITION / 400 | Precondition failed | VPC not configured, private service access not set up | Enable Service Networking API | Set up VPC peering |
| RESOURCE_EXHAUSTED / 429 | Resource pool empty | Region capacity insufficient for Redis | Try another region | Retry in different region |
| UNAVAILABLE / 503 | Service unavailable | Redis backend transient failure | Retry with backoff | Wait and retry |
| INTERNAL / 500 | Internal error | GCP backend error | Retry; escalate if persistent | Report to GCP Support |
| OUT_OF_MEMORY | Memory full | Redis max memory reached, evictions started | Increase memory or optimize data | Scale up instance |
| CONNECTION_REFUSED | Redis unreachable | Instance not in READY state, network issue | Check instance state and network | Verify VPC connectivity |
| AUTH_FAILED | Wrong auth string | Redis AUTH password incorrect | Reset or provide correct auth string | Check auth config |

## Diagnostic Order

```
1. Auth check     → gcloud auth print-access-token
2. Project check  → gcloud config get-value project
3. API status     → gcloud services list --enabled | grep redis.googleapis.com
4. SA networking  → gcloud services list --enabled | grep servicenetworking.googleapis.com
5. Instance state → gcloud redis instances describe NAME --region=REGION | jq .state
6. Connectivity   → gcloud redis instances describe NAME --region=REGION | jq '{host,port}'
7. VPC network    → gcloud compute networks list --format=json
```

## Common Issues

### "Cannot create Redis instance — VPC not configured"
```bash
# Enable Service Networking API
gcloud services enable servicenetworking.googleapis.com

# Allocate IP range for Redis
gcloud compute addresses create redis-range \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network=default

# Create VPC peering
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=redis-range \
  --network=default
```

### "Redis instance connection refused"
```bash
# Check instance state
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region}}" --format="json" | jq '.state'

# Check authorized network
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region}}" --format="json" | jq '.authorizedNetwork'
```

### "Redis memory usage high"
```bash
# Monitor memory metrics in Cloud Monitoring
# Metric: redis.googleapis.com/instance/memory_usage_ratio
# Action: Scale up or set maxmemory-policy

# Update maxmemory-policy
gcloud redis instances update "{{user.instance_name}}" \
  --region="{{user.region}}" \
  --redis-config="maxmemory-policy=allkeys-lru"
```

### "Export to GCS fails"
```bash
# Grant Storage Object Admin to Redis SA
PROJECT_NUM=$(gcloud projects describe $CLOUDSDK_CORE_PROJECT --format='value(projectNumber)')
gcloud storage buckets add-iam-policy-binding "{{user.export_gcs_uri%%/*}}" \
  --member="serviceAccount:service-$PROJECT_NUM@cloud-redis.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

## Error Recovery Patterns

### Retry with backoff (long-running operation)
```bash
for i in 1 2 3; do
  gcloud redis instances describe "my-instance" --region=us-central1 --format="json" | jq -r '.state' | grep READY && break
  echo "⚠️  Waiting... ($i/3)"
  sleep 30
done
```

### Idempotent create
```bash
if ! gcloud redis instances describe "my-instance" --region=us-central1 --quiet 2>/dev/null; then
  gcloud redis instances create "my-instance" --region=us-central1 --memory-size=1GB
fi
```