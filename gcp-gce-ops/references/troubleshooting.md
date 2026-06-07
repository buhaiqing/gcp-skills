# Troubleshooting — Compute Engine

## Error Codes

| gRPC/HTTP | Meaning | Agent Action |
|-----------|---------|--------------|
| INVALID_ARGUMENT / 400 | Request validation failed | Fix parameter per API |
| PERMISSION_DENIED / 403 | Insufficient IAM | Grant compute.instanceAdmin |
| NOT_FOUND / 404 | Resource not found | Verify name and zone |
| ALREADY_EXISTS / 409 | Duplicate name | Choose unique name |
| QUOTA_EXCEEDED / 429 | Quota limit | Request increase |
| INTERNAL / 500 | Server error | Retry, then escalate |
| UNAVAILABLE / 503 | Service unavailable | Retry with backoff |
| ZONE_RESOURCE_POOL_EXHAUSTED | Zone out of capacity | Try another zone |
| BILLING_NOT_ENABLED | Billing inactive | Enable in Cloud Console |
| FAILED_PRECONDITION | Wrong instance state | Wait for TERMINATED/RUNNING |
| ABORTED | Operation conflict | Retry after completion |
| RESOURCE_EXHAUSTED | Too many ops | Reduce concurrency |

## Diagnostic Order

1. Describe instance: gcloud compute instances describe NAME --zone=Z --format=json
2. Check serial console: gcloud compute instances get-serial-port-output NAME --zone=Z
3. Check disk status: gcloud compute disks describe DISK --zone=Z --format=json
4. Check quotas: gcloud compute regions describe R --format=json | jq '.quotas[]'
5. Check MIG status (if applicable)
6. Check Cloud Logging: resource.type="gce_instance"

## Common Issues

### SSH Failed
- Firewall: allow tcp:22 from 130.211.0.0/22, 35.191.0.0/16
- OS Login: enable or add SSH keys
- Instance not running: start it

### Instance Won't Start
- Disk corrupted: snapshot + restore to new instance
- Zone exhausted: try another zone
- Quota exceeded: request increase

### Disk Full
```bash
gcloud compute ssh NAME --command="df -h"
gcloud compute disks resize D --size=N --zone=Z
gcloud compute ssh NAME --command="sudo resize2fs /dev/sda1"
```

### MIG Can't Scale
- Template missing: verify with describe
- Quota insufficient: request increase
- Zone exhausted: update distribution policy
