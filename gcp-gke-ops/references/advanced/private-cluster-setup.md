# GKE Private Cluster Setup Guide

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [VPC and Subnet Setup](#vpc-and-subnet-setup)
- [Private Cluster Creation](#private-cluster-creation)
- [Networking Configuration](#networking-configuration)
- [Security Configuration](#security-configuration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

Private GKE clusters have nodes with only internal IP addresses, providing enhanced security by isolating the control plane and worker nodes from the public internet. This guide covers the complete setup process.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│               GKE Private Cluster Architecture                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Google Cloud VPC                     │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │              Private Subnet (10.0.0.0/20)       │   │   │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐        │   │   │
│  │  │  │  Node   │  │  Node   │  │  Node   │        │   │   │
│  │  │  │  10.0.  │  │  10.0.  │  │  10.0.  │        │   │   │
│  │  │  │  0.5    │  │  0.6    │  │  0.7    │        │   │   │
│  │  │  └─────────┘  └─────────┘  └─────────┘        │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                          │                              │   │
│  │                          ▼                              │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │              Master Subnet (172.16.0.0/28)      │   │   │
│  │  │  ┌─────────────────────────────────────────┐   │   │   │
│  │  │  │           GKE Master (Private)          │   │   │   │
│  │  │  └─────────────────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────┐                                              │
│  │  Bastion    │  (Optional) for admin access                  │
│  │  Host       │                                              │
│  └─────────────┘                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable iap.googleapis.com  # For IAP-based access

# Required IAM roles
# - roles/compute.admin (VPC/subnet management)
# - roles/container.admin (GKE cluster management)
# - roles/iam.securityAdmin (firewall rules)
```

## VPC and Subnet Setup

### Create VPC

```bash
# Create VPC
gcloud compute networks create gke-vpc \
  --subnet-mode=custom

# Create node subnet
gcloud compute networks subnets create gke-nodes \
  --network=gke-vpc \
  --region=us-central1 \
  --range=10.0.0.0/20 \
  --secondary-range=pods=10.4.0.0/14,services=10.8.0.0/20

# Create master subnet
gcloud compute networks subnets create gke-masters \
  --network=gke-vpc \
  --region=us-central1 \
  --range=172.16.0.0/28
```

### Create Firewall Rules

```bash
# Allow master to node communication
gcloud compute firewall-rules create gke-master-to-nodes \
  --network=gke-vpc \
  --allow=tcp:443,tcp:10250 \
  --source-ranges=172.16.0.0/28 \
  --target-tags=gke-cluster-CLUSTER_NAME

# Allow node to master communication
gcloud compute firewall-rules create gke-nodes-to-master \
  --network=gke-vpc \
  --allow=tcp:443,tcp:10250 \
  --source-tags=gke-cluster-CLUSTER_NAME \
  --target-ranges=172.16.0.0/28

# Allow internal communication between nodes
gcloud compute firewall-rules create gke-nodes-internal \
  --network=gke-vpc \
  --allow=tcp:0-65535,udp:0-65535,icmp \
  --source-ranges=10.0.0.0/8
```

## Private Cluster Creation

### Create Private Cluster

```bash
# Create private cluster
gcloud container clusters create PRIVATE_CLUSTER_NAME \
  --region=us-central1 \
  --network=gke-vpc \
  --subnetwork=gke-nodes \
  --cluster-secondary-range-name=pods \
  --services-secondary-range-name=services \
  --master-ipv4-cidr=172.16.0.0/28 \
  --enable-private-nodes \
  --enable-private-endpoint \
  --master-authorized-networks=10.0.0.0/8 \
  --no-enable-basic-auth \
  --no-issue-client-certificate \
  --enable-ip-alias \
  --enable-network-policy
```

### Create Node Pool

```bash
# Create node pool for private cluster
gcloud container node-pools create default-pool \
  --cluster=PRIVATE_CLUSTER_NAME \
  --region=us-central1 \
  --num-nodes=3 \
  --machine-type=e2-medium \
  --disk-type=pd-balanced \
  --disk-size=100 \
  --enable-autorepair \
  --enable-autoupgrade \
  --node-tags=gke-PRIVATE_CLUSTER_NAME
```

## Networking Configuration

### Configure Master Authorized Networks

```bash
# Add authorized network for master access
gcloud container clusters update PRIVATE_CLUSTER_NAME \
  --region=us-central1 \
  --enable-master-authorized-networks \
  --master-authorized-networks=10.0.0.0/8,172.16.0.0/28

# Remove authorized network
gcloud container clusters update PRIVATE_CLUSTER_NAME \
  --region=us-central1 \
  --no-enable-master-authorized-networks
```

### Configure Private Endpoint Access

```bash
# Enable private endpoint
gcloud container clusters update PRIVATE_CLUSTER_NAME \
  --region=us-central1 \
  --enable-private-endpoint

# Disable private endpoint
gcloud container clusters update PRIVATE_CLUSTER_NAME \
  --region=us-central1 \
  --no-enable-private-endpoint
```

### Configure NAT for Outbound Traffic

```bash
# Create Cloud NAT
gcloud compute routers create gke-router \
  --network=gke-vpc \
  --region=us-central1

# Create NAT
gcloud compute routers nats create gke-nat \
  --router=gke-router \
  --region=us-central1 \
  --auto-allocate-nat-external-ips \
  --nat-all-subnet-ip-ranges
```

## Security Configuration

### Configure Network Policy

```bash
# Enable network policy
gcloud container clusters update PRIVATE_CLUSTER_NAME \
  --region=us-central1 \
  --enable-network-policy

# Install Calico for network policy enforcement
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml
```

### Configure Pod Security

```yaml
# pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  supplementalGroups:
    rule: 'RunAsAny'
```

### Configure Workload Identity

```bash
# Enable Workload Identity
gcloud container clusters update PRIVATE_CLUSTER_NAME \
  --region=us-central1 \
  --workload-pool=PROJECT_ID.svc.id.goog

# Update node pool to use Workload Identity
gcloud container node-pools update default-pool \
  --cluster=PRIVATE_CLUSTER_NAME \
  --region=us-central1 \
  --workload-metadata=GKE_METADATA
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Cannot reach master | Master not authorized | Add your IP to master authorized networks |
| Pods cannot pull images | No outbound internet | Configure Cloud NAT |
| Nodes not ready | Firewall rules missing | Verify node-to-master firewall rules |
| DNS resolution fails | Private DNS not configured | Use Cloud DNS or configure DNS forwarding |

### Verify Cluster Configuration

```bash
# Check cluster status
gcloud container clusters describe PRIVATE_CLUSTER_NAME \
  --region=us-central1

# Check node status
gcloud container clusters describe PRIVATE_CLUSTER_NAME \
  --region=us-central1 \
  --format="value(nodeConfig.networkConfig)"

# Verify firewall rules
gcloud compute firewall-rules list --filter="network:gke-vpc"
```

### Access Cluster from Bastion

```bash
# SSH to bastion host
gcloud compute ssh BASTION_NAME --zone=us-central1-a

# From bastion, access cluster
gcloud container clusters get-credentials PRIVATE_CLUSTER_NAME \
  --region=us-central1 \
  --internal-ip

# Verify kubectl access
kubectl get nodes
```

## Best Practices

1. **Network Isolation**: Use separate subnets for nodes, masters, and pods
2. **Firewall Rules**: Implement least-privilege firewall rules
3. **Master Access**: Restrict master authorized networks to trusted IPs
4. **Outbound Traffic**: Use Cloud NAT for controlled outbound access
5. **DNS**: Configure private DNS for internal service discovery
6. **Monitoring**: Enable VPC Flow Logs for network monitoring
7. **Encryption**: Use Customer-Managed Encryption Keys (CMEK) for data at rest
8. **Audit Logging**: Enable Kubernetes audit logs and export to Cloud Logging

## See Also

- [Private GKE Clusters](https://cloud.google.com/kubernetes-engine/docs/how-to/private-clusters)
- [VPC-native Clusters](https://cloud.google.com/kubernetes-engine/docs/how-to/alias-ip)
