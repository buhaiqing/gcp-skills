# Workload Identity Federation — Deep Dive

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Workload Identity Setup](#workload-identity-setup)
- [IAM Bindings](#iam-bindings)
- [Kubernetes Service Account Mapping](#kubernetes-service-account-mapping)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)
- [Migration from Key-based Auth](#migration-from-key-based-auth)

---

## Overview

Workload Identity Federation allows Kubernetes workloads to authenticate as IAM service accounts without storing long-lived credentials. This guide covers advanced configuration, IAM bindings, and troubleshooting.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│            Workload Identity Federation Architecture            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐         ┌─────────────┐                      │
│  │  GKE        │         │  Workload   │                      │
│  │  Cluster    │────────►│  Identity   │                      │
│  └─────────────┘         │  Pools      │                      │
│                          └──────┬──────┘                      │
│                                 │                              │
│                                 ▼                              │
│  ┌─────────────┐         ┌─────────────┐                      │
│  │  K8s        │         │  IAM        │                      │
│  │  Service    │────────►│  Service    │                      │
│  │  Account    │         │  Account    │                      │
│  └─────────────┘         └─────────────┘                      │
│                                 │                              │
│                                 ▼                              │
│  ┌─────────────┐         ┌─────────────┐                      │
│  │  GCP        │         │  Google     │                      │
│  │  APIs       │◄────────│  OAuth      │                      │
│  └─────────────┘         │  Token      │                      │
│                          └─────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# Enable required APIs
gcloud services enable iam.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable sts.googleapis.com

# Required IAM roles
# - roles/iam.workloadIdentityPoolAdmin (manage pools)
# - roles/iam.workloadIdentityPoolProviderAdmin (manage providers)
# - roles/iam.serviceAccountTokenCreator (create tokens)
```

## Workload Identity Setup

### Create Workload Identity Pool

```bash
# Create a workload identity pool
gcloud iam workload-identity-pools create POOL_ID \
  --display-name="GKE Pool" \
  --description="Workload Identity Pool for GKE clusters"

# Describe the pool
gcloud iam workload-identity-pools describe POOL_ID
```

### Create Workload Identity Provider

```bash
# Create provider for GKE
gcloud iam workload-identity-pools providers create-google PROVIDER_ID \
  --workload-identity-pool=POOL_ID \
  --attribute-mapping="google.subject=assertion.subject,attribute.project=assertion.project" \
  --attribute-condition="assertion.project_id == 'PROJECT_ID'"
```

## IAM Bindings

### Bind KSA to GSA

```bash
# Bind Kubernetes service account to Google service account
gcloud iam service-accounts add-iam-policy-binding GSA_NAME@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/KSA_NAME]"

# Example: Bind default SA in production namespace
gcloud iam service-accounts add-iam-policy-binding my-app@my-project.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:my-project.svc.id.goog[production/my-app-sa]"
```

### Verify IAM Bindings

```bash
# Check IAM policy on service account
gcloud iam service-accounts get-iam-policy GSA_NAME@PROJECT_ID.iam.gserviceaccount.com

# Check workload identity pool
gcloud iam workload-identity-pools describe POOL_ID
```

## Kubernetes Service Account Mapping

### Annotate KSA

```bash
# Annotate Kubernetes service account
kubectl annotate serviceaccount KSA_NAME \
  --namespace=NAMESPACE \
  iam.gke.io/gcp-service-account=GSA_NAME@PROJECT_ID.iam.gserviceaccount.com

# Example: Annotate default SA
kubectl annotate serviceaccount my-app-sa \
  --namespace=production \
  iam.gke.io/gcp-service-account=my-app@my-project.iam.gserviceaccount.com
```

### Verify Annotation

```bash
# Check KSA annotation
kubectl get serviceaccount KSA_NAME -n NAMESPACE -o yaml

# Expected output:
# apiVersion: v1
# kind: ServiceAccount
# metadata:
#   annotations:
#     iam.gke.io/gcp-service-account: GSA_NAME@PROJECT_ID.iam.gserviceaccount.com
```

### Create Workload with Bound SA

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: my-app-sa  # KSA with Workload Identity annotation
      containers:
      - name: app
        image: gcr.io/PROJECT_ID/my-app:latest
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Token request fails | KSA not annotated | Verify annotation: `kubectl get sa -n NAMESPACE -o yaml` |
| Permission denied | IAM binding missing | Check: `gcloud iam service-accounts get-iam-policy GSA` |
| Wrong project | Provider attribute condition | Verify: `gcloud iam workload-identity-pools providers describe` |
| Audience mismatch | Token audience mismatch | Ensure pod uses correct audience |

### Debug Token Exchange

```bash
# Test token exchange from pod
gcloud auth print-identity-token --audience=https://example.com

# Check if workload identity is configured
kubectl exec -it POD_NAME -- env | grep GOOGLE
```

### Verify Workload Identity Configuration

```bash
# List workload identity pools
gcloud iam workload-identity-pools list

# List providers
gcloud iam workload-identity-pools providers list --workload-identity-pool=POOL_ID

# Check provider attributes
gcloud iam workload-identity-pools providers describe PROVIDER_ID \
  --workload-identity-pool=POOL_ID
```

### Check Kubernetes Event Logs

```bash
# Check pod events for errors
kubectl describe pod POD_NAME -n NAMESPACE

# Look for workload identity related events
kubectl get events -n NAMESPACE --field-selector reason=WorkloadIdentity
```

## Security Best Practices

1. **Least Privilege**: Grant only required roles to service accounts
2. **Attribute Conditions**: Use attribute conditions in providers to restrict access
3. **Audience Validation**: Always specify audiences for token requests
4. **Regular Audits**: Audit IAM bindings and KSA annotations regularly
5. **Pool Isolation**: Use separate pools for different environments
6. **Disable Key Export**: Disable key creation on GSA: `gcloud iam service-accounts update GSA --disable-key-creation`

## Migration from Key-based Auth

### Step 1: Create Workload Identity Pool

```bash
gcloud iam workload-identity-pools create gke-pool \
  --display-name="GKE Migration Pool"
```

### Step 2: Create Provider

```bash
gcloud iam workload-identity-pools providers create-google gke-provider \
  --workload-identity-pool=gke-pool \
  --attribute-mapping="google.subject=assertion.subject,attribute.project=assertion.project"
```

### Step 3: Bind Service Accounts

```bash
gcloud iam service-accounts add-iam-policy-binding GSA_NAME@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/KSA_NAME]"
```

### Step 4: Annotate Kubernetes SA

```bash
kubectl annotate serviceaccount KSA_NAME \
  --namespace=NAMESPACE \
  iam.gke.io/gcp-service-account=GSA_NAME@PROJECT_ID.iam.gserviceaccount.com \
  --overwrite
```

### Step 5: Remove Key Files

```bash
# Delete key file from secrets
kubectl delete secret SECRET_NAME -n NAMESPACE

# Update deployment to remove env GOOGLE_APPLICATION_CREDENTIALS
kubectl set env deployment/DEPLOYMENT_NAME GOOGLE_APPLICATION_CREDENTIALS-
```

## See Also

- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GKE Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
