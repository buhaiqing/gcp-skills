# Core Concepts — Google Kubernetes Engine (GKE)

## Architecture

Google Kubernetes Engine (GKE) provides a managed Kubernetes service on Google Cloud. Each cluster consists of a managed control plane and one or more node pools.

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **Control Plane** | Managed Kubernetes API server, scheduler, controller-manager, etcd | Region (regional) or Zone (zonal) |
| **Node Pool** | Group of VMs running identical Kubernetes node configuration | Zone(s) |
| **Node** | Compute Engine VM running kubelet, kube-proxy, container runtime | Zone |
| **Pod** | Smallest deployable unit — one or more containers with shared storage/network | Node |
| **Service** | Stable network endpoint for a set of pods | Cluster |
| **Namespace** | Virtual cluster for resource isolation | Cluster |
| **PersistentVolume** | Storage provisioned via CSI driver (Compute Engine disks) | Zone or Region |

### Cluster Types

| Type | Control Plane | Nodes | Use Case |
|------|--------------|-------|----------|
| **Zonal** | Single zone | Single zone | Dev/test, cost-sensitive |
| **Regional** | Replicated across 3 zones in region | Multi-zone (3 zones) | Production HA |
| **Autopilot** | Regional, fully managed | Auto-provisioned in region | Ops-light, cost-optimized |

### Node Pool Features

| Feature | Description |
|---------|-------------|
| **Auto-repair** | GKE automatically repairs unhealthy nodes |
| **Auto-upgrade** | Nodes automatically upgraded per release channel |
| **Cluster Autoscaler** | Automatically scales node count based on pod resource requests |
| **Node Auto-Provisioning** | Automatically creates new node pools for unscheduled pods |
| **Spot Nodes** | Preemptible/spot VMs with 60-91% discount |
| **GPUs** | Attach NVIDIA GPUs for ML workloads |
| **Local SSD** | Ephemeral local SSD for high-throughput workloads |

## Release Channels

| Channel | Version Cadence | Quality | Use Case |
|---------|----------------|---------|----------|
| **Rapid** | Latest K8s patch within ~1 week | Bleeding edge | Testing, dev clusters |
| **Regular** | Latest K8s patch within ~1 month | Stable | Production (default) |
| **Stable** | Latest K8s patch within ~2-3 months | Most stable | Compliance, risk-averse |

Fetch available versions:
```bash
gcloud container get-server-config --zone="{{user.zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.channels[] | {channel, validVersions: [.validVersions[]]}'
```

## Autopilot vs Standard

| Feature | Autopilot | Standard |
|---------|-----------|----------|
| Node management | Fully managed | User manages node pools |
| Resource requests | Required | Not required for scheduling |
| Node visibility | Abstracted | Full visibility |
| Cost model | Pay-per-pod-resource | Pay-per-node |
| Committed use | Available | Available |
| GPU support | Yes | Yes |
| Cluster Autoscaler | Built-in | Optional |
| Node pool customization | Limited | Full |

## VPC-Native (IP Alias)

GKE clusters use VPC-native networking by default since GKE 1.21. This uses **alias IP ranges** on Compute Engine VMs.

| Range | Purpose | Typical Size |
|-------|---------|--------------|
| Pod CIDR | IPs assigned to pods | /14 (65,534 pods) |
| Service CIDR | IPs assigned to services | /20 (4,094 services) |
| Node CIDR | IPs for node VMs | /22 (1,024 nodes) |

Formula: `max_pods_per_node = f(pod_cidr_mask - node_cidr_mask)`.

## Workload Identity

GKE's recommended method for pod-level IAM. Maps Kubernetes service accounts to Google service accounts.

| Component | Function |
|-----------|----------|
| GKE Metadata Server | Serves OAuth2 tokens to pods |
| Workload Identity Pool | `PROJECT.svc.id.goog` |
| IAM Binding | `roles/iam.workloadIdentityUser` on GSA → KSA |

## Quotas

Check current quotas:
```bash
gcloud compute regions describe "{{user.region}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.quotas[] | select(.metric | test("cpu|instance|in_use_addresses|firewall")) | {metric, limit, usage}'
```

Key quota limits:
| Resource | Default Quota | Scope |
|----------|--------------|-------|
| CPUs | 24-100 per region | Region |
| Persistent Disk | 10TB per region | Region |
| GKE Clusters | 100 per project | Global |
| In-use IPs | 8 per region | Region |

## Prerequisites Installation

### Install gcloud CLI

```bash
# Primary: official installer
if ! command -v gcloud &> /dev/null; then
    curl https://sdk.cloud.google.com | bash 2>/dev/null \
    || (echo "⚠️ Installer failed, trying apt..." \
        && sudo apt-get update && sudo apt-get install -y google-cloud-sdk) \
    || (echo "⚠️ apt failed, trying manual..." \
        && wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
        && tar -xf google-cloud-cli-*.tar.gz && ./google-cloud-sdk/install.sh --quiet)
    exec -l $SHELL
    gcloud init
fi
```

### Install kubectl

```bash
if ! command -v kubectl &> /dev/null; then
    gcloud components install kubectl --quiet 2>/dev/null \
    || curl -LO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && chmod +x kubectl && sudo mv kubectl /usr/local/bin/
fi
```

### Bootstrap Go Runtime

```bash
if ! command -v go &> /dev/null; then
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH="amd64"; [ "$ARCH" = "aarch64" ] && ARCH="arm64"
    mkdir -p /tmp/go-runtime
    curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime 2>/dev/null \
    || curl -fsSL "https://go.dev/dl/go1.24.0.linux-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
    if [ -f /tmp/go-runtime/go/bin/go ]; then
        export PATH="/tmp/go-runtime/go/bin:$PATH"
    else
        echo "Go download failed. Using Python SDK as fallback."
        pip install --quiet --user google-cloud-container
    fi
fi
```

### Configure Credentials

```bash
export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" 2>/dev/null \
|| gcloud auth login --quiet
gcloud config set project "$CLOUDSDK_CORE_PROJECT"
```

### Verify Configuration

```bash
gcloud config list
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
gcloud container clusters list --limit=1 --format="json" &>/dev/null && echo "✅ GKE API OK"
```

## Dependencies

| Depend On | Reason |
|-----------|--------|
| Compute Engine | Node pools run on GCE VMs |
| VPC / Subnet | Cluster networking (VPC-native required) |
| Secondary IP Ranges | Pod and Service CIDR ranges |
| IAM | Service accounts for nodes and Workload Identity |
| Cloud Load Balancing | Kubernetes Services of type LoadBalancer |
| Cloud Monitoring | Cluster metrics and alerts |
| Artifact Registry / Container Registry | Container image storage |
| Cloud DNS | Internal DNS for services |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Single zone control plane fails | API server unavailable (zonal) | Use regional cluster (3 replicas) |
| Single zone node pool fails | Pods in that zone lost | Multi-zonal node pool |
| Node pool exhausted | Pods unschedulable | Cluster Autoscaler + node auto-provisioning |
| Quota exhausted | Can't scale or create new nodes | Request increase / use committed use |
| Release channel bug | Cluster instability | Use maintenance windows + exclusions; pin to specific version if needed |
| etcd backup missing | Cluster state unrecoverable | Backup for GKE — schedule backups