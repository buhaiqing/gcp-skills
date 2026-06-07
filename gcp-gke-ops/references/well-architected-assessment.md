# Well-Architected Assessment — GKE

## §1 Security

| IAM Role | Use Case |
|----------|----------|
| roles/container.clusterAdmin | Full GKE API — production |
| roles/container.nodeServiceAccount | Default node SA |
| roles/container.viewer | Read-only cluster inspection |
| roles/iam.workloadIdentityUser | Bind GSA to KSA |

**Credentials**: Never log SA key content. Only check: `test -f "$GOOGLE_APPLICATION_CREDENTIALS"`
**Workload Identity**: Prefer over node SA access keys. Map KSA → GSA per namespace.
**Binary Authorization**: Enable in clusters that require signed container images.
**Private Clusters**: Restrict control plane to private IPs, set master authorized networks.
**Shielded GKE Nodes**: Enable Secure Boot + Integrity Monitoring on node pools.
**CMEK**: Use Customer-Managed Encryption Keys for etcd and node persistent disks.

### Security Checklist

| Check | Method | Expected |
|-------|--------|----------|
| Workload Identity | `gcloud container clusters describe C --zone=Z --format="json" \| jq '.workloadIdentityConfig'` | workloadPool set |
| Private cluster | `gcloud container clusters describe C --zone=Z --format="json" \| jq '.privateClusterConfig'` | enablePrivateNodes: true |
| Master authorized networks | `gcloud container clusters describe C --zone=Z --format="json" \| jq '.masterAuthorizedNetworksConfig'` | cidrBlocks non-empty |
| Binary Authorization | `gcloud container clusters describe C --zone=Z --format="json" \| jq '.binaryAuthorization'` | evaluationMode: PROJECT_SINGLETON |
| Shielded nodes | `gcloud container node-pools describe NP --cluster=C --zone=Z --format="json" \| jq '.config.shieldedInstanceConfig'` | enableSecureBoot: true |

## §2 Stability

| Strategy | Implementation |
|----------|---------------|
| Regional cluster | 3 control plane replicas across zones |
| Multi-zonal node pool | Node pool across 3 zones in region |
| Cluster Autoscaler | Auto-scale node count based on pod demand |
| Auto-repair | GKE automatically heals unhealthy nodes |
| Auto-upgrade | Nodes upgraded per release channel schedule |
| PodDisruptionBudget | Ensure min available pods during node drain |
| Backup for GKE | Scheduled backups to Cloud Storage |

### Backups

```bash
# Create BackupPlan for GKE
gcloud container backup-restore backup-plans create "backup-plan-{{user.cluster_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location="{{user.location}}" \
  --cluster="projects/{{env.CLOUDSDK_CORE_PROJECT}}/locations/{{user.location}}/clusters/{{user.cluster_name}}" \
  --all-namespaces \
  --include-secrets \
  --include-volume-data \
  --cron-schedule="0 2 * * *" \
  --backup-retain-days=30
```

## §3 Cost

| Model | Discount | Best For |
|-------|----------|----------|
| Autopilot | Optimized per-pod | Ops-light, variable workloads |
| Committed Use (1yr) | ~20% on compute | Steady-state node pools |
| Committed Use (3yr) | ~40% on compute | Predictable workloads |
| Spot (preemptible) node pools | 60-91% | Batch, fault-tolerant, CI/CD |
| Node auto-provisioning | Right-size per workload | Mixed workloads |

Idle detection: Alert on node CPU < 10% for 7 days → consider consolidation or spot pools.

### Cost Optimization Checklist

- [ ] Use Cluster Autoscaler to match node count to workload
- [ ] Use spot node pools for stateless workloads
- [ ] Use committed use discounts for 24/7 production pools
- [ ] Consider Autopilot for multi-tenant environments
- [ ] Set resource requests/limits on all pods
- [ ] Clean up unused images from Artifact Registry
- [ ] Use VPA in recommendation mode to optimize resource allocations

## §4 Efficiency

| Feature | Benefit |
|---------|---------|
| Release channels | Automated managed upgrades |
| Config Sync | GitOps — sync cluster state from Git repo |
| Cloud Build CI/CD | Build → test → deploy to GKE pipeline |
| Artifact Registry | Consistent image repository |
| GKE Fleet | Multi-cluster management |
| Maintenance windows | Control when auto-upgrades happen |

### Maintenance Window

```bash
gcloud container clusters update "{{user.cluster_name}}" \
  --zone="{{user.location}}" \
  --maintenance-window-start="2026-06-08T02:00:00Z" \
  --maintenance-window-end="2026-06-08T06:00:00Z" \
  --maintenance-window-recurrence="FREQ=WEEKLY;BYDAY=SU"
```

## §5 Performance

| Feature | Benefit |
|---------|---------|
| Cluster Autoscaler (CA) | Add nodes when pods unschedulable |
| Horizontal Pod Autoscaler (HPA) | Scale pods based on CPU/memory/custom metrics |
| Vertical Pod Autoscaler (VPA) | Recommend CPU/memory request adjustments |
| Node pool machine types | Right-size per workload (E2, N2, N2D, C2, C2D, TAU) |
| Local SSDs | High-throughput, low-latency scratch |
| Placement policies | Colocate pods for low-latency |

### Autoscaling Best Practices

| Component | When | Config |
|-----------|------|--------|
| Cluster Autoscaler | Always in production | min/max per node pool; enable NAP for heterogeneous |
| HPA | Stateless web workloads | targetCPUUtilizationPercentage: 60-80% |
| VPA | Stateful/legacy workloads | mode: RECOMMEND (no auto-update first) |

### Node Pool Sizing

```bash
# Fetch recommended machine types
gcloud compute machine-types list --filter="name ~ e2-.*" --format="table(name,guestCpus,memoryMb)"
```