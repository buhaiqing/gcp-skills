# Core Concepts — Filestore

## Architecture

Filestore is a fully managed NFS file server service on Google Cloud. Instances provide shared file systems accessible from Compute Engine VMs, GKE clusters, Cloud Run services, and on-premises clients via VPN/Interconnect.

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **Instance** | Managed NFS file server | Zonal or Regional |
| **File Share** | NFS export path on the instance | Instance-level |
| **Backup** | Point-in-time backup of an instance | Regional |
| **Snapshot** | Point-in-time snapshot of instance data | Instance-level |
| **Replication** | Async replication to standby instance | Cross-region |

### Service Tiers

| Tier | Capacity | Performance | Availability | Use Case |
|------|----------|-------------|-------------|----------|
| **BASIC_HDD** | 1 TiB – 63.9 TiB | Standard fixed | Zonal | Basic file sharing, dev/test |
| **BASIC_SSD** | 2.5 TiB – 63.9 TiB | Premium fixed | Zonal | High performance dev/test |
| **HIGH_SCALE_SSD** (Zonal) | 10 TiB – 100 TiB | Configurable | Zonal | HPC, batch compute |
| **Zonal** | 1 TiB – 9.75 TiB / 10 TiB – 100 TiB | Configurable | Zonal | HPC, localized workloads |
| **Regional** | 100 GiB – 9.75 TiB / 10 TiB – 100 TiB | Configurable | Regional | Mission-critical, zone failover |
| **ENTERPRISE** (Multishares for GKE) | 1 TiB – 10 TiB | Scales with capacity | Regional | GKE workloads, high availability |

### Protocol Support

| Protocol | Supported Tiers | Highlights |
|----------|-------------------|-----------|
| **NFSv3** | All tiers | Bidirectional communication, VPC peering, private services access |
| **NFSv4.1** | Zonal, Regional, Enterprise | Client/server auth, message integrity, in-transit encryption (krb5p) |

## Quotas

Check current quotas:

```bash
gcloud filestore instances list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq 'length'
```

### Default Quotas

| Resource | Default Limit | Request Increase |
|----------|---------------|-----------------|
| Storage quota per project/region | Varies by region | Cloud Console |
| Instances per project | Limited by storage quota | Cloud Console |
| Backups per project | 50 per region | Cloud Console |
| Snapshots per instance | 240 (Zonal/Regional/Enterprise) | N/A |
| Client connections (Zonal 1TiB) | 2,000 | Scales with capacity |

Check quota in Cloud Console: [Quotas & Limits](https://console.cloud.google.com/iam-admin/quotas)

## Dependencies

| Depends On | Reason |
|------------|--------|
| VPC Network | Instance must be in a VPC subnet |
| Cloud Monitoring | Instance metrics and alerts |
| Cloud IAM | Service account for API access |
| Cloud KMS | CMEK encryption key management |
| Compute Engine | Mounting clients (VMs) |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Zone failure (Zonal tier) | Instance unavailable | Use Regional tier for HA |
| Region failure (Regional tier) | Transparent failover | Instance replication to another region |
| Storage full | Writes rejected | Monitor free space, auto-scale capacity |
| Quota exhausted | Can't create instances | Request increase |
| Network partition | Clients can't mount | VPC redundancy, Private Service Connect |

## Prerequisites

> **Self-Healing:** Installation flows include multi-path recovery. Each step has ≥3 error-handling strategies.

### 1. Install gcloud CLI

```bash
if ! command -v gcloud &> /dev/null; then
    curl https://sdk.cloud.google.com | bash 2>/dev/null \
    || (sudo apt-get update && sudo apt-get install -y google-cloud-sdk) \
    || (wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
        && tar -xf google-cloud-cli-*.tar.gz && ./google-cloud-sdk/install.sh --quiet)
    exec -l $SHELL
    gcloud init
fi
```

### 2. Configure Credentials

```bash
export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" 2>/dev/null \
|| gcloud auth login --quiet
gcloud config set project "$CLOUDSDK_CORE_PROJECT"
```

### 3. Enable Filestore API

```bash
gcloud services enable file.googleapis.com --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 4. Verify Configuration

```bash
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
gcloud filestore instances list --limit=1 --format="json" &>/dev/null && echo "✅ Filestore API OK"
```

> **Security**: Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.
