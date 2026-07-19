# GKE Advanced Monitoring & AIOps

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Cluster Health Monitoring](#cluster-health-monitoring)
- [Node Pool Anomaly Detection](#node-pool-anomaly-detection)
- [Workload Performance Anomalies](#workload-performance-anomalies)
- [Cost Anomaly Detection](#cost-anomaly-detection)
- [Alert Configuration](#alert-configuration)
- [Automated Remediation](#automated-remediation)
- [Best Practices](#best-practices)

---

## Overview

This guide covers advanced AIOps patterns for GKE clusters including anomaly detection for cluster health, node pools, workloads, and costs using Cloud Monitoring, Cloud Logging, and automated remediation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GKE AIOps Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  GKE        │    │  Cloud      │    │  Cloud      │        │
│  │  Metrics    │───►│  Monitoring │───►│  Logging    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Node       │    │  Workload   │    │  Cost       │        │
│  │  Anomaly    │    │  Anomaly    │    │  Anomaly    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                │
│                            ▼                                   │
│                   ┌─────────────┐                              │
│                   │  Alerting   │                              │
│                   │  + Auto-    │                              │
│                   │  Remediate  │                              │
│                   └─────────────┘                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# Enable required APIs
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable container.googleapis.com

# Required IAM roles
# - roles/monitoring.editor (create alerting policies)
# - roles/logging.viewer (query logs)
# - roles/container.viewer (read cluster metadata)
```

## Cluster Health Monitoring

### Query Cluster Metrics

```bash
# CPU utilization across cluster
gcloud monitoring time-series list \
  --filter='metric.type="kubernetes.io/container/cpu/core_usage_time" AND resource.type="k8s_container"' \
  --interval-start-time=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --interval-end-time=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --format="value(sum)"

# Memory utilization
gcloud monitoring time-series list \
  --filter='metric.type="kubernetes.io/container/memory/used_bytes" AND resource.type="k8s_container"' \
  --interval-start-time=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --interval-end-time=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

### Detect Cluster Anomalies

```python
# Python SDK for anomaly detection
from google.cloud import monitoring_v3
from datetime import datetime, timedelta

def detect_cluster_anomalies(project_id, cluster_name):
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"
    
    interval = monitoring_v3.TimeInterval({
        "end_time": {"seconds": int(datetime.utcnow().timestamp())},
        "start_time": {"seconds": int((datetime.utcnow() - timedelta(hours=1)).timestamp())}
    })
    
    results = client.list_time_series(
        request={
            "name": project_name,
            "filter": f'resource.type="k8s_cluster" AND metric.type="kubernetes.io/container/cpu/core_usage_time"',
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
        }
    )
    
    for result in results:
        # Calculate mean and detect anomalies
        values = [point.value.double_value for point in result.points]
        mean = sum(values) / len(values)
        anomalies = [v for v in values if v > mean * 1.5]
        
        if anomalies:
            print(f"Anomaly detected: {result.metric.labels}")
```
→ routes to Playbook 1 (Node NotReady) / Playbook 2 (Node Pool Scale-Up Failed) when sustained node-level pressure is confirmed.

## Node Pool Anomaly Detection

### Monitor Node Health

```bash
# Check node readiness
kubectl get nodes -o wide

# Check node conditions
kubectl describe nodes | grep -A 5 "Conditions:"

# Query node metrics
gcloud monitoring time-series list \
  --filter='metric.type="kubernetes.io/node/cpu/allocatable_utilization" AND resource.type="k8s_node"' \
  --interval-start-time=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --interval-end-time=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

### Detect Node Anomalies

```bash
# Detect nodes with high CPU
kubectl top nodes | awk '$3 > 80 {print $1, $3}'

# Detect nodes with high memory
kubectl top nodes | awk '$5 > 80 {print $1, $5}'

# Detect nodes with disk pressure
kubectl get nodes -o json | jq -r '.items[] | select(.status.conditions[] | select(.type=="DiskPressure" and .status=="True")) | .metadata.name'
```
→ routes to Playbook 1 (Node NotReady) for NotReady/DiskPressure conditions; Playbook 2 (Node Pool Scale-Up Failed) for autoscaler-stuck signals.

## Workload Performance Anomalies

### Monitor Pod Performance

```bash
# Detect pods with high CPU
kubectl top pods --all-namespaces | awk '$3 > 100m {print $1, $2, $3}'

# Detect pods with high memory
kubectl top pods --all-namespaces | awk '$4 > 256Mi {print $1, $2, $4}'

# Detect pods in CrashLoopBackOff
kubectl get pods --all-namespaces | grep -i crashloop
```
→ routes to Playbook 3 (Workload CrashLoopBackOff) for restart/CrashLoopBackOff signals; Playbook 4 (HPA Hit Max Replicas) for scaling-limited signals.

### Detect Workload Anomalies

```bash
# Pods with restartCount > 5 (abnormal restart loop)
kubectl get pods --all-namespaces -o json | jq -r '.items[] | .metadata.namespace as $ns | .metadata.name as $pod | .status.containerStatuses[]? | select(.restartCount > 5) | "\($ns)/\($pod) restartCount=\(.restartCount) reason=\(.lastState.terminated.reason // "n/a")"'
```

## Cost Anomaly Detection

> **Cost waste detection, idle-node detection, rightsizing, and CUD recommendations are covered by [`finops-gke-cost.md`](finops-gke-cost.md).** This AIOps runbook does NOT re-narrate those — route cost-optimization signals there.

### Monitor Budget (minimal)

```bash
# List configured budgets and their cap (units = currency amount)
gcloud billing budgets list \
  --billing-account=ACCOUNT_ID \
  --format="table(name,budgetAmount.units)"
```

### Detect Cost Anomalies (Cloud Billing SDK)

```python
# Detect budgets where actual spend exceeds 1.2x the cap.
# Defensive: guard against missing fields so a partial budget object never raises.
def detect_cost_anomalies(billing_account_id):
    from google.cloud import billing_v1

    client = billing_v1.BudgetServiceClient()
    parent = f"billingAccounts/{billing_account_id}"

    anomalies = []
    for budget in client.list_budgets(request={"parent": parent}):
        actual = getattr(getattr(budget.amount, "specified_amount", None), "units", None)
        cap = getattr(budget.budget_amount, "units", None)
        if actual is None or cap is None:
            continue  # skip budgets without comparable amount fields
        if float(actual) > float(cap) * 1.2:
            anomalies.append({
                "budget": budget.display_name,
                "actual": actual,
                "budgeted": cap,
            })

    return anomalies
```

## Alert Configuration

### Create Alerting Policy

```bash
# Create alert for high CPU
gcloud monitoring policies create \
  --display-name="GKE High CPU Alert" \
  --condition-display-name="CPU > 80%" \
  --condition-filter='metric.type="kubernetes.io/container/cpu/core_usage_time" AND resource.type="k8s_container"' \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s \
  --notification-channels=CHANNEL_ID
```

### Alert on Anomalies

```bash
# Create alert for node anomalies
gcloud monitoring policies create \
  --display-name="GKE Node Anomaly" \
  --condition-display-name="Node CPU > 90%" \
  --condition-filter='metric.type="kubernetes.io/node/cpu/allocatable_utilization" AND resource.type="k8s_node"' \
  --condition-threshold-value=0.9 \
  --condition-threshold-duration=600s
```

## Automated Remediation

### Auto-heal Nodes

```bash
# Auto-repair unhealthy nodes
gcloud container node-pools update NODE_POOL_NAME \
  --cluster=CLUSTER_NAME \
  --location=LOCATION \
  --enable-autorepair

# Force node replacement
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data
kubectl delete node NODE_NAME
```

### Auto-scale Workloads

```bash
# Enable Horizontal Pod Autoscaler
kubectl autoscale deployment DEPLOYMENT_NAME \
  --min=2 --max=10 --cpu-percent=80

# Enable Vertical Pod Autoscaler
kubectl patch deployment DEPLOYMENT_NAME -p '{"spec":{"template":{"spec":{"containers":[{"name":"CONTAINER_NAME","resources":{"requests":{"cpu":"100m","memory":"128Mi"}}}]}}}}'
```

## Self-Healing Playbook

> **Scope**: This section defines the closed-loop self-healing contract for GKE AIOps. Every remediation path follows **detection → DRY-RUN preview → gate → idempotent apply**. Destructive or irreversible actions (node pool deletion, version upgrade rollback) are marked **HALT** and require explicit human confirmation — they are NOT auto-applied.
>
> **Credential Masking**: Per `AGENTS.md §0.1`, never log `GOOGLE_APPLICATION_CREDENTIALS` content or SA key values. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.
>
> **Error taxonomy**: Map each failure to `docs/error-taxonomy.md`.
> **Blast radius**: Cross-skill impact and rollback boundaries follow `AGENTS.md §5` (Cross-Skill Composition) and `AGENTS.md §7` (Security Constraints).
> **Closed-loop feedback**: After each apply, emit a feedback record via `gcp-gcl-runner-ops/trace_feedback.py` (see [Closed-Loop Feedback](#closed-loop-feedback)).

### Self-Healing Contract (mandatory per path)

| Phase | Action | Gate |
|-------|--------|------|
| 1. Detection | Identify anomaly via metric/log query | Per-playbook threshold met (see each Playbook) |
| 2. DRY-RUN preview | Print the exact `gcloud`/`kubectl` command that *would* run, with target resource | Human/Agent reviews preview |
| 3. Gate | Check risk class (safe-apply vs HALT) + blast radius | HALT → stop and request confirmation |
| 4. Idempotent apply | Execute only if not already in desired state | Re-validate post-state |
| 5. Post-apply re-check | Re-run the detection query; if anomaly persists, ESCALATE to HALT | Persists → request human intervention (no silent loop) |

**Idempotency rule**: Probe desired state first; skip apply if already satisfied. Never run a delete/rollback without a prior DRY-RUN and explicit confirmation.

**Fail-escalation (Phase 5)**: After apply, re-run the Playbook's Detection query. If the anomaly is still present (threshold still met), do NOT retry the apply silently — emit a HALT and request human intervention with the DRY-RUN preview and re-check output attached. This prevents infinite self-heal loops on unresolvable conditions (e.g. a node that keeps going NotReady due to underlying hardware fault).

---

### Playbook 1 — Node NotReady

#### Detection
```bash
kubectl get nodes -o json | jq -r '.items[] | select(.status.conditions[] | select(.type=="Ready" and .status!="True")) | .metadata.name'
```
**Threshold**: trigger if node `Ready=Unknown/False` sustained **> 5m** (not transient — ignore < 5m flaps from rolling upgrades).

#### DRY-RUN Preview
```bash
# Would enable autorepair and (if still NotReady after grace) cordon+drain
echo "DRY-RUN: gcloud container node-pools update {{user.node_pool_name}} --cluster={{user.cluster_name}} --location={{user.location}} --enable-autorepair"
echo "DRY-RUN: kubectl cordon NODE_NAME && kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data"
```

**Gate**: Safe-apply (autorepair enable). Drain is safe-apply only if workloads are replicated; single-replica workloads → HALT.

#### Idempotent Apply
```bash
# Probe: already autorepairing?
if ! gcloud container node-pools describe "{{user.node_pool_name}}" --cluster="{{user.cluster_name}}" --location="{{user.location}}" --format="value(management.autoRepair)" | grep -q "true"; then
  gcloud container node-pools update "{{user.node_pool_name}}" --cluster="{{user.cluster_name}}" --location="{{user.location}}" --enable-autorepair
fi
```

---

### Playbook 2 — Node Pool Scale-Up Failed

#### Detection
```bash
gcloud container operations list --filter="operationType=UPGRADE_NODE_POOL OR operationType=REPAIR_CLUSTER" --format="json" | jq -r '.[] | select(.status=="FAILED") | .name'
# Or autoscaler stuck:
kubectl get events --field-selector reason=FailedScheduling -A
```
**Threshold**: trigger if a scale-up operation stays `FAILED` **> 10m**, or `FailedScheduling` events persist **> 10m** (transient scheduling delays excluded).

#### DRY-RUN Preview
```bash
echo "DRY-RUN: gcloud container clusters resize {{user.cluster_name}} --node-pool={{user.node_pool_name}} --num-nodes=TARGET --zone={{user.location}}"
```

**Gate**: Safe-apply if target ≤ max-nodes of autoscaling config. Exceeds max-nodes → HALT (raises quota/cost; needs human raise of `--max-nodes`).

#### Idempotent Apply
```bash
CURRENT=$(gcloud container node-pools describe "{{user.node_pool_name}}" --cluster="{{user.cluster_name}}" --location="{{user.location}}" --format="value(currentNodeCount)")
if [ "$CURRENT" -lt "$TARGET" ]; then
  gcloud container clusters resize "{{user.cluster_name}}" --node-pool="{{user.node_pool_name}}" --num-nodes="$TARGET" --zone="{{user.location}}" --format="json"
fi
```

---

### Playbook 3 — Workload CrashLoopBackOff

#### Detection
```bash
kubectl get pods --all-namespaces -o json | jq -r '.items[] | select(.status.phase!="Running") | .metadata.namespace + "/" + .metadata.name'
kubectl get pods --all-namespaces | grep -i crashloop
```
**Threshold**: trigger if `restartCount > 5` within **10m**, or pod stuck in `CrashLoopBackOff`/`Error` phase **> 5m** (ignore one-off OOM during deploy).

#### DRY-RUN Preview
```bash
echo "DRY-RUN: kubectl rollout restart deployment/DEPLOYMENT -n NAMESPACE"
echo "DRY-RUN: kubectl describe pod POD -n NAMESPACE   # inspect lastState.terminated.reason"
```

**Gate**: Safe-apply (rollout restart) for stateless deployments. StatefulSet with volume-bound single replica → HALT (risk data loss / disruption).

#### Idempotent Apply
```bash
# Only restart if not already progressing
if ! kubectl rollout status deployment/DEPLOYMENT -n NAMESPACE --timeout=5s >/dev/null 2>&1; then
  kubectl rollout restart deployment/DEPLOYMENT -n NAMESPACE
fi
```

---

### Playbook 4 — HPA Hit Max Replicas

#### Detection
```bash
# Scaling limited at max: ScalingLimited=MaxReplicasReached is True, OR desired already at/above max
kubectl get hpa --all-namespaces -o json | jq -r '.items[] | select((.status.conditions[] | select(.type=="ScalingLimited" and .reason=="MaxReplicasReached" and .status=="True")) or (.status.desiredReplicas >= .spec.maxReplicas)) | .metadata.namespace + "/" + .metadata.name'
```
**Threshold**: trigger if `ScalingLimited=MaxReplicasReached` is `True` sustained **> 10m** (brief spikes during rollout excluded).

#### DRY-RUN Preview
```bash
echo "DRY-RUN: kubectl patch hpa HPA -n NAMESPACE --patch '{\"spec\":{\"maxReplicas\":NEW_MAX}}'"
```

**Gate**: Safe-apply if NEW_MAX within quota budget. Exceeds project quota or cost guardrail → HALT (request human quota/cost approval).

#### Idempotent Apply
```bash
CUR_MAX=$(kubectl get hpa HPA -n NAMESPACE -o jsonpath='{.spec.maxReplicas}')
if [ "$CUR_MAX" -lt "$NEW_MAX" ]; then
  kubectl patch hpa HPA -n NAMESPACE --patch "{\"spec\":{\"maxReplicas\":$NEW_MAX}}"
fi
```

---

### HALT Paths (never auto-applied)

| Path | Why HALT | Required action |
|------|----------|-----------------|
| Node pool deletion | Irreversible, disrupts workloads | Explicit human confirmation with exact pool name |
| Node pool version upgrade rollback | Can cause version skew / data-plane disruption | Human approval + DRY-RUN of downgrade command |
| Any delete of PV/PVC | Data loss | HALT — backup first |

---

### Closed-Loop Feedback

After each apply (or HALT), emit a feedback record so the GCL Critic can audit factual accuracy and traceability:

```bash
# Requires being run from within the repo (resolves repo root via git).
python3 "$(git rev-parse --show-toplevel)/gcp-gcl-runner-ops/trace_feedback.py" \
  --skill gcp-gke-ops \
  --playbook "node-notready" \
  --action "enable-autorepair" \
  --result "applied" \
  --resource "{{user.node_pool_name}}"
```

The feedback record feeds the Generator-Critic-Loop (`AGENTS.md §12`): Critic verifies the applied state matches the DRY-RUN preview and that no HALT path was bypassed.

## Best Practices

1. **Baseline Metrics**: Establish baselines for normal behavior before setting thresholds
2. **Multi-metric Alerts**: Combine CPU, memory, and restart metrics for comprehensive detection
3. **Gradual Thresholds**: Use warning (80%) and critical (95%) thresholds
4. **Cost Controls**: Set up budget alerts to prevent cost overruns
5. **Log Aggregation**: Centralize logs for pattern analysis
6. **Regular Reviews**: Review anomalies weekly to refine detection rules
7. **Documentation**: Document known anomalies vs. real issues

## See Also

- [GKE Monitoring](https://cloud.google.com/kubernetes-engine/docs/monitoring)
- [Cloud Monitoring API](https://cloud.google.com/monitoring/api/ref_v3/rest)
