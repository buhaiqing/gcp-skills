# Core Concepts — Compute Engine

## Architecture

Google Compute Engine (GCE) provides virtual machines running on Google's infrastructure. Each VM instance runs on a hypervisor and can be configured with specific machine types, boot images, persistent disks, and network interfaces.

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **VM Instance** | Virtual machine with configurable CPU, memory, and disk | Zone |
| **Persistent Disk** | Durable block storage (pd-standard/pd-balanced/pd-ssd/pd-extreme) | Zone or Region |
| **Snapshot** | Incremental backup of a disk | Region or Multi-region |
| **Machine Image** | Full instance config + disk backup | Global |
| **Instance Template** | Reusable instance config for MIGs | Global or Region |
| **Managed Instance Group** | Auto-scaled, auto-healed group of identical instances | Zone or Region |

## Quotas

Check current quotas:
```bash
gcloud compute regions describe "{{user.region}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.quotas[] | select(.metric | test("cpu|instance|disk|snapshot")) | {metric, limit, usage}'
```

## Dependencies

| Depend On | Reason |
|-----------|--------|
| VPC / Subnet | Instances require network |
| Firewall Rules | Control instance network access |
| Cloud Load Balancing | MIGs as LB backends |
| IAM | Service accounts for instance operations |
| Cloud Monitoring | Instance metrics and alerts |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Single instance fails | App unavailable | MIG auto-healing |
| Zone down | All instances in zone lost | Regional MIG multi-zone |
| Disk corruption | Data loss | Regular snapshots |
| Quota exhausted | Can't create instances | Request increase |
