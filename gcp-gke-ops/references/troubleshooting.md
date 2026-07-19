# Troubleshooting — GKE

> 错误码遵循 docs/error-taxonomy.md — product-specific codes MUST map to a root-cause dimension above.

## Error Codes

| gRPC/HTTP | Meaning | Agent Action |
|-----------|---------|--------------|
| INVALID_ARGUMENT / 400 | Request validation failed | Fix parameter per API reference |
| PERMISSION_DENIED / 403 | Insufficient IAM | Grant container.clusterAdmin |
| NOT_FOUND / 404 | Resource not found | Verify cluster name, zone, project |
| ALREADY_EXISTS / 409 | Duplicate name | Choose unique cluster/node pool name |
| QUOTA_EXCEEDED / 429 | Quota limit (CPU, CIDR, IP) | Request increase via Cloud Console |
| INTERNAL / 500 | Server error | Retry, then escalate |
| UNAVAILABLE / 503 | Service unavailable | Retry with backoff |
| RESOURCE_EXHAUSTED | Zone capacity exhausted | Try another zone/region |
| FAILED_PRECONDITION | Wrong cluster state | Wait for RUNNING state |
| ABORTED | Operation conflict | Retry after pending operation completes |

## GKE-Specific Error Codes

| Error Code | Meaning | Diagnosis | Recovery |
|-----------|---------|-----------|----------|
| QUOTA_EXCEEDED | CPU/disk/IP quota insufficient | `gcloud compute regions describe R --format="json" \| jq '.quotas[]'` | Request quota increase; use different region |
| INSUFFICIENT_CIDR | VPC-native IP ranges too small | `gcloud container clusters describe C --zone=Z --format="json" \| jq '{clusterIpv4Cidr, servicesIpv4Cidr}'` | Increase pod/service CIDR; request larger secondary range |
| VERSION_NOT_AVAILABLE | Requested version not in channel | `gcloud container get-server-config --zone=Z --format="json" \| jq '.channels[] \| {channel, validVersions}'` | Pick a valid version for the channel |
| RESOURCE_EXHAUSTED | Zone out of GKE capacity | `gcloud compute zones list --format="json" \| jq '.[].name'` | Use different zone or region |
| KUBECONFIG_EXPIRED | Credentials stale | `gcloud container clusters get-credentials C --zone=Z` | Refresh kubeconfig |
| PRIVATE_CLUSTER_ENDPOINT | Private cluster accessed from outside VPC | Verify source IP in VPC / Cloud VPN / Cloud Interconnect | Use `--internal-ip` flag or bastion host |
| POD_RESOURCE_INSUFFICIENT | Node has insufficient resources | `kubectl describe node N \| grep -A5 "Allocated resources"` | Scale node pool; reduce pod requests |
| TAINT_TOLERATION_MISMATCH | No node tolerates pod taints | `kubectl describe pod P \| grep -A5 "Tolerations"` | Add toleration to pod spec or remove taint from node |
| AUTOSCALER_CONSTRAINTS | min > max nodes conflict | `gcloud container node-pools describe NP --cluster=C --zone=Z --format="json" \| jq '.autoscaling'` | Fix min/max node constraints |
| BACKUP_FAILED | Backup for GKE permission error | Check IAM: roles/backupdr.admin on backup project | Grant backup admin role to cluster SA |
| CLUSTER_DELETE_FAILED | Cluster has protected resources | `gcloud container clusters describe C --zone=Z --format="json" \| jq '.conditions[]'` | Remove finalizers; delete node pools first |
| WORKLOAD_IDENTITY_FAILED | GSA → KSA binding missing | `gcloud iam service-accounts get-iam-policy GSA@PROJECT.iam.gserviceaccount.com` | Add `roles/iam.workloadIdentityUser` binding |

## Diagnostic Order

1. Describe cluster: `gcloud container clusters describe NAME --zone=Z --format=json | jq '{name, status, conditions}'`
2. Check operations: `gcloud container operations list --zone=Z --format=json | jq '.[0:5]'`
3. Describe node pool: `gcloud container node-pools describe NP --cluster=C --zone=Z --format=json`
4. Check node pool status: Verify `status: RUNNING`, check `conditions[]`
5. Check quotas: `gcloud compute regions describe R --format=json | jq '.quotas[] | select(.metric | test("cpu|instance|in_use_addresses"))'`
6. Get credentials: `gcloud container clusters get-credentials NAME --zone=Z`
7. Check node status via kubectl: `kubectl get nodes -o wide`
8. Check pod status: `kubectl get pods --all-namespaces | grep -v Running`
9. Check events: `kubectl get events --all-namespaces --sort-by='.lastTimestamp' | tail -20`
10. Check Cloud Logging: resource.type="k8s_cluster"

## Common Issues

### Cluster Won't Create (QUOTA_EXCEEDED)
```bash
gcloud compute regions describe us-central1 --format="json" | jq '.quotas[] | select(.metric | test("cpu|instance|in_use_addresses"))'
# Request quota increase or use region with more capacity
```

### Cluster Won't Create (INSUFFICIENT_CIDR)
```bash
# VPC-native: verify secondary ranges
gcloud compute networks subnets describe SUBNET --region=R --format="json" | jq '.secondaryIpRanges'
# Increase CIDR masks or add larger secondary range
```

### Credentials Expired
```bash
gcloud container clusters get-credentials CLUSTER --zone=Z
kubectl cluster-info
```

### Private Cluster Access Denied
```bash
# From within VPC:
gcloud container clusters get-credentials CLUSTER --zone=Z --internal-ip
# From bastion:
gcloud compute ssh BASTION --zone=Z --command="gcloud container clusters get-credentials CLUSTER --zone=Z --internal-ip && kubectl cluster-info"
```

### Nodes Unschedulable
```bash
kubectl get nodes | grep "NotReady"
kubectl describe node NODE | grep -A10 "Conditions"
# Check if auto-repair is running
gcloud container node-pools describe NP --cluster=C --zone=Z --format="json" | jq '.management'
```

### Node Pool Can't Scale
- Autoscaler constraints: verify `minNodeCount <= maxNodeCount`
- Quota insufficient: request CPU/IP increase
- Zone exhausted: update node pool locations
- Cluster in RECONCILING state: wait for completion