# Monitoring — GKE

## Key Metrics

| Metric | Type | Threshold |
|--------|------|-----------|
| kubernetes.io/container/cpu/core_usage_time | Counter | Baseline |
| kubernetes.io/container/memory/bytes_used | Gauge | > 80% of request → alert |
| kubernetes.io/container/disk/bytes_used | Gauge | > 85% → alert |
| kubernetes.io/pod/volume/total_bytes | Gauge | Watch PV usage |
| container.googleapis.com/cluster/cpu/utilization | Gauge | > 75% for 10min → suggest scaling |
| container.googleapis.com/cluster/memory/utilization | Gauge | > 80% for 10min → suggest scaling |
| container.googleapis.com/cluster/disk/bytes_used | Gauge | > 85% → alert |
| container.googleapis.com/node/cpu/utilization | Gauge | > 80% for 5min → scale node pool |
| container.googleapis.com/node/memory/bytes_used | Gauge | > 85% → scale up |
| container.googleapis.com/node/disk/bytes_used | Gauge | > 80% → consider larger boot disk |
| container.googleapis.com/pod/unschedulable | Delta | > 0 → pod can't schedule |
| kubernetes.io/node/accelerator/memory_total | Gauge | GPU memory |

## Dashboard Example

```bash
# GKE built-in dashboards (Cloud Console): Monitoring > Dashboards > GKE
# Custom dashboard via gcloud (requires monitoring API)
gcloud alpha monitoring dashboards create \
  --config-from-file=gke-dashboard.yaml
```

## Alert Policy Example

```bash
gcloud alpha monitoring policies create \
  --display-name="GKE-High-CPU-Utilization" \
  --condition-filter='metric.type="container.googleapis.com/cluster/cpu/utilization"' \
  --condition-threshold-value=0.8 \
  --condition-duration=600s \
  --notification-channels="projects/{{env.CLOUDSDK_CORE_PROJECT}}/notificationChannels/N"
```

## Anomaly Patterns

| Pattern | Likely Cause |
|---------|--------------|
| CPU spike then pod crash loop | OOMKilled — increase memory limit |
| Node NotReady for >5min | Auto-repair triggered; check node health |
| Unschedulable pods > 0 | Node pool at capacity; scale up |
| Memory rising daily | Memory leak in container |
| Disk filling on node | Container logs or images not cleaned up |
| Network error rate > 1% | Service mesh or CNI issue |
| API Server 5xx errors | Control plane under load — check API server metrics |
| Pods stuck in Pending | No node matches tolerations or resource requests |