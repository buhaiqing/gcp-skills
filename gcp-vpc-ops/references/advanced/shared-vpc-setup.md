# Shared VPC Setup — Google Cloud VPC

> Provides network administrators and cloud engineers with a complete guide to implementing Shared VPC in Google Cloud — host project configuration, service projects, subnet delegation, IAM permissions, and best practices.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Host Project Setup](#host-project-setup)
4. [Service Project Setup](#service-project-setup)
5. [Subnet Delegation](#subnet-delegation)
6. [IAM Permissions](#iam-permissions)
7. [Network Automation](#network-automation)
8. [Common Patterns](#common-patterns)
9. [Troubleshooting](#troubleshooting)
10. [Cost Considerations](#cost-considerations)

## Overview

**Shared VPC** allows multiple projects (service projects) to share a single VPC network (host project). This enables:

- Better network management with centralized network policy
- Simplified network architecture across multiple applications
- Reduced operational overhead (single VPC, single routing table)
- Fine-grained IAM control for different teams

**When to Use:**

| Scenario | Recommendation |
|----------|----------------|
| Multi-team environment, one network admin | ✅ YES — Shared VPC |
| Separate VPCs for security isolation | ❌ NO — Use VPC Peering |
| Monorepo with shared infrastructure | ✅ YES — Shared VPC |
| Application multi-tenancy | ✅ YES — Shared VPC |

**Prerequisites:**

- [ ] Host project and at least one service project created
- [ ] Compute Engine API enabled on both projects
- [ ] Only one project acts as the host (reject dual-host setup)
- [ ] Owner or Editor IAM role in host project (to configure shared VPC)

## Architecture

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    HOST PROJECT                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │   VPC Network (Shared)                            │  │
│  │   ┌─────────────────────────────────────────┐   │  │
│  │   │ Subnet 1 (subnet-1)                      │   │  │
│  │   │   - Subnet IP Range                      │   │  │
│  │   │   - IAM bindings:                        │   │  │
│  │   │     * Service Project A                  │   │  │
│  │   │     * Service Project B                  │   │  │
│  │   └─────────────────────────────────────────┘   │  │
│  │   ┌─────────────────────────────────────────┐   │  │
│  │   │ Subnet 2 (subnet-2)                      │   │  │
│  │   │   - Subnet IP Range                      │   │  │
│  │   └─────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼───────┐  ┌───────▼───────┐  ┌───────▼───────┐
│ Service Proj  │  │ Service Proj  │  │ Service Proj  │
│   (App A)     │  │   (App B)     │  │   (App C)     │
│  - VM Instances                           │
│  - VPC Connector / Cloud NAT              │
└───────────────┘  └───────────────┘  └───────────────┘
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Host Project** | Project that owns the VPC network and routes. Central place for network administration. |
| **Service Project** | Project that uses the shared VPC but does NOT own the network configuration. |
| **Subnet Delegation** | Assigning specific IAM permissions for a subnet to a service project without giving full network admin. |
| **Service Account** | Service account in service project used by infrastructure to access Compute API. |

## Host Project Setup

### Step 1: Enable Compute Engine API

```bash
gcloud services enable compute.googleapis.com \
  --project="{{user.host_project}}"
```

**Pre-flight Check:**
```bash
gcloud services list --enabled \
  --project="{{user.host_project}}" \
  --filter="name=compute.googleapis.com"
```

Expected: `compute.googleapis.com` in list.

### Step 2: Create or Use Existing VPC Network

**Option A: Create VPC (recommended):**

```bash
gcloud compute networks create "{{user.shared_vpc_name}}" \
  --project="{{user.host_project}}" \
  --subnet-mode=custom \
  --bgp-routing-mode=regional
```

**Option B: Use existing network:**
```bash
# Verify network exists
gcloud compute networks describe "{{user.shared_vpc_name}}" \
  --project="{{user.host_project}}"
```

### Step 3: Create Subnets

**Network Admin creates subnets in host project:**

```bash
# Create subnet in us-central1
gcloud compute networks subnets create "{{user.subnet_name}}" \
  --project="{{user.host_project}}" \
  --network="{{user.shared_vpc_name}}" \
  --region="{{user.region}}" \
  --range="{{user.subnet_cidr}}"
```

**Subnet CIDR Planning:**

| Partition | Size | CIDR | Example |
|-----------|------|------|---------|
| Subnet allocation | 1 | /20 (4096 IPs) | 10.0.0.0/20 |
| Reserved (host VMs) | 1 | /24 (256 IPs) | 10.0.0.0/24 |
| Reserved (management) | 1 | /26 (64 IPs) | 10.0.0.128/26 |
| Reserved (load balancers) | 1 | /28 (16 IPs) | 10.0.1.128/28 |

### Step 4: Explicitly Configure Shared VPC

Ensure the network is in the correct state:

```bash
# Verify network has shared VPC enabled
gcloud compute networks describe "{{user.shared_vpc_name}}" \
  --project="{{user.host_project}}" \
  --format="json" | \
  jq '{name, sharedVpcStatus, routingConfig}'
```

Expected: `sharedVpcStatus: "NONE"` (until service projects are added)

## Service Project Setup

### Step 1: Enable Compute Engine API

```bash
gcloud services enable compute.googleapis.com \
  --project="{{user.service_project}}"
```

**Pre-flight Check:**
```bash
gcloud services list --enabled \
  --project="{{user.service_project}}" \
  --filter="name=compute.googleapis.com"
```

### Step 2: Associate Service Project with Host Project

**Option A: Associate using `gcloud`:**

```bash
gcloud compute networks peerings associate-projects \
  --enable-shared-vpc \
  --network="{{user.shared_vpc_name}}" \
  --project="{{user.host_project}}" \
  --service-projects="{{user.service_project}}"
```

**Option B: Associate using Python SDK:**

```python
# associate_shared_vpc.py
from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]  # host project
network_name = "{{user.shared_vpc_name}}"
service_project = "{{user.service_project}}"

network_client = compute_v1.NetworksClient()

# Associate service project with shared VPC
assoc = compute_v1.VersionedNetworkConfiguration()
assoc.network = f"https://www.googleapis.com/compute/v1/projects/{project}/global/networks/{network_name}"
assoc.enabled = True

assoc_response = network_client.configure_network(
    project=project,
    region="global",
    versioned_network_configuration=assoc
)

print(f"Shared VPC association: {assoc_response.target_id}")
print(f"Service project: {service_project}")
```

### Step 3: Verify Association

```bash
# Verify service project is now associated
gcloud compute networks describe "{{user.shared_vpc_name}}" \
  --project="{{user.host_project}}" \
  --format="json" | \
  jq '{name, sharedVpcStatus, peerNetworks: [.peerNetworks[]|.name]}'
```

Expected: `peerNetworks` includes service project.

## Subnet Delegation

**Crucial Concept:** Even after associating, service projects cannot use subnets until they are *delegated* or given proper Access Levels.

### Option 1: Subnet Delegation (IAM-based, recommended)

Permit service project to manage VMs in the subnet:

```bash
gcloud compute networks subnets update "{{user.subnet_name}}" \
  --region="{{user.region}}" \
  --project="{{user.host_project}}" \
  --add-iam-policy-binding \
    member="serviceAccount:{{user.service_project}}-svc.iam.gserviceaccount.com" \
    role="roles/compute.networkUser"
```

**Or using `subnetDelegatedServices` (variant for subnet-level IAM):**

```bash
gcloud compute networks subnets update "{{user.subnet_name}}" \
  --region="{{user.region}}" \
  --project="{{user.host_project}}" \
  --enable-subnet-iam \
  --set-iam-policy="
    policy:
      bindings:
      - role: roles/compute.networkUser
        members:
        - serviceAccount:{{user.service_project}}-svc.iam.gserviceaccount.com
  "
```

**Important:** The exact IAM binding strategy depends on your access control model. Most teams use network-level IAM.

### Option 2: Subnet-level IAM (alternative)

If you have strictly segmented subnets per service project:

```bash
# Create separate subnets delegating to different service projects
gcloud compute networks subnets create "subnet-app-a" \
  --network="{{user.shared_vpc_name}}" \
  --range="10.0.0.0/24" \
  --region="us-central1" \
  --project="{{user.host_project}}" \
  --add-iam-policy-binding \
    member="serviceAccount:app-a-svc.iam.gserviceaccount.com" \
    role="roles/compute.networkUser"

gcloud compute networks subnets create "subnet-app-b" \
  --network="{{user.shared_vpc_name}}" \
  --range="10.0.1.0/24" \
  --region="us-central1" \
  --project="{{user.host_project}}" \
  --add-iam-policy-binding \
    member="serviceAccount:app-b-svc.iam.gserviceaccount.com" \
    role="roles/compute.networkUser"
```

### Option 3: Access Levels (for granular control)

Use Access Levels (IIA) to restrict which projects can use which subnets:

```bash
# Create API Gateway (Access Level service)
gcloud services enable accessapproval.googleapis.com \
  --project="{{user.host_project}}"

# Create Access Level (grants subnet access only to certain service accounts)
gcloud access-context-manager access-levels create "subnet-a-access" \
  --region="global" \
  --parent="accessPolicies/{{user_access_policy_id}}" \
  --folder="policies":\{folderId:"{{user.folder_id}}"\}:accessPolicies:{{user_access_policy_id}} \
  --description="Allow subnet A access to App A service accounts" \
  --monetization:\{blocked:True},
  --conditions:
  - title: "App A Service Account Access"
    expression:
      expression: "request.time.dayOfMonth % 7 == 0"
    conclusionDescription: "Testing access level"
```

**Best Practice:** Use Access Levels for sensitive workloads. For general applications, IAM bindings are sufficient.

## IAM Permissions

### Required Roles

| Role | Product | Description |
|------|---------|-------------|
| `roles/compute.networkAdmin` | Host Project | Full control over VPC, subnets, routes |
| `roles/compute.networkUser` | Host Project + Service Projects | Allows VMs to use network resources |
| `roles/accesscontextmanager.policyAdmin` | Host Project | Manage Access Levels (if using IIAs) |
| `roles/resourcemanager.owner` | All Projects | Project ownership |

### IAM Setup Example

```bash
# In HOST project:
# Grant network admin to infra/team
gcloud projects add-iam-policy-binding \
  "{{user.host_project}}" \
  --member="group:infra@google.com" \
  --role="roles/compute.networkAdmin"

# Delegate subnet to service project
gcloud compute networks subnets describe "{{user.subnet_name}}" --region=us-central1
```

### Cross-Project IAM Bindings

**Network Admin (Host Project):**
```bash
gcloud compute networks subnets update "{{user.subnet_name}}" \
  --region="{{user.region}}" \
  --add-iam-policy-binding \
    member="serviceAccount:{{user.service_project}}-sa.iam.gserviceaccount.com" \
    role="roles/compute.networkUser"
```

**Service Project VMs:** Use this service account for VM creation

### IAM Best Practices

| Practice | Why |
|----------|------|
| Use dedicated service accounts per service project | Avoid permission escalation between teams |
| Grant Least Authority | Only delegate necessary IAM roles |
| Monitor IAM changes | Use Audit Logging for security |
| Use constraint policies | Limit IAM policy modifications |

## Network Automation

### CI/CD Pipeline Example (Terraform)

**host-project/main.tf:**

```hcl
resource "google_compute_network" "shared" {
  name                    = "{{user.shared_vpc_name}}"
  auto_create_subnetworks = false
  mtu                     = 2060
}

resource "google_compute_subnetwork" "app_a" {
  name          = "subnet-app-a"
  ip_cidr_range = "10.0.0.0/24"
  region        = "us-central1"
  network       = google_compute_network.shared.id
  purpose       = "PRIVATE"
}

resource "google_compute_subnetwork" "app_b" {
  name          = "subnet-app-b"
  ip_cidr_range = "10.0.1.0/24"
  region        = "us-central1"
  network       = google_compute_network.shared.id
  purpose       = "PRIVATE"
}
```

**service-project/main.tf:**

```hcl
resource "google_compute_instance" "app_a_vm" {
  name         = "app-a-01"
  machine_type = "e2-medium"

  network_interface {
    subnetwork = "https://www.googleapis.com/compute/v1/projects/{{user.host_project}}/regions/us-central1/subnetworks/subnet-app-a"

    access_configs {
      name  = "External NAT"
      type  = "ONE_TO_ONE_NAT"
    }
  }

  # Service account from host project
  service_account {
    email = "{{user.service_account_email}}"
  }
}
```

### Ansible Example

**host-playbook.yml:**

```yaml
- name: Configure Shared VPC Host Project
  hosts: localhost
  tasks:
    - name: Create VPC Network
      gcp_compute_network:
        name: "{{shared_vpc_name}}"
        auto_create_subnetworks: no
        project: "{{host_project_id}}"

    - name: Create Subnet
      gcp_compute_subnetwork:
        name: "{{subnet_name}}"
        range: "10.0.0.0/24"
        region: "us-central1"
        project: "{{host_project_id}}"

    - name: Associate Service Project
      gcp_compute_network_peerings_associate_projects:
        enable_shared_vpc: yes
        network: "{{shared_vpc_name}}"
        project: "{{host_project_id}}"
        service_projects:
          - "{{service_project_id}}"
```

**service-playbook.yml:**

```yaml
- name: Deploy VMs in Service Project
  hosts: localhost
  tasks:
    - name: Create VM using shared subnet
      gcp_compute_instance:
        name: "app-01"
        machine_type: "e2-medium"
        subnetwork: "https://www.googleapis.com/compute/v1/projects/{{host_project_id}}/regions/us-central1/subnetworks/{{subnet_name}}"
        project: "{{service_project_id}}"
```

## Common Patterns

### Pattern 1: Multi-Team Shared VPC

**Goal:** Different teams share infrastructure under network team governance.

```
Host Project (Network Team)
├── VPC: shared-vpc
├── Subnet A: team-a (delegated to team-a-sa)
├── Subnet B: team-b (delegated to team-b-sa)
└── Subnet C: team-c (delegated to team-c-sa)
```

**Best Practices:**

- Network team manages VPC and subnets in host project
- Each application team has dedicated IP CIDR in their subnet
- Separate service accounts per team for IAM delegation
- Centralized logging/alerting

### Pattern 2: Monorepo Refactoring

**Goal:** Merge multiple projects into a single VPC for cost efficiency and easier management.

**Migrations Steps:**

1. Create shared VPC in new/central project
2. Migrate VM instances manually (use snapshots + OS disk export)
3. Update network interfaces to new subnets
4. Decommission old VPCs and traffic load balancers
5. Update DNS records

### Pattern 3: Vertical Integration (GKE)

**Goal:** Multiple GKE clusters share infrastructure using Shared VPC.

**Prerequisites:**

- `Compute Network Admin` role in host project
- `Network Viewer` role in host project
- Same client certificate authority (if using private clusters)

**Steps:**

```bash
# Attach service project to host project
gcloud compute networks peerings associate-projects \
  --network="{{user.shared_vpc_name}}" \
  --project="{{user.host_project}}" \
  --service-projects="{{user.service_project}}"

# Create GKE cluster using shared subnet
gcloud container clusters create "{{user.cluster_name}}" \
  --region="{{user.region}}" \
  --network="{{user.shared_vpc_name}}" \
  --subnetwork="{{user.subnet_name}}" \
  --project="{{user.service_project}}"
```

### Pattern 4: Interconnect & VPC Connectors

**Goal:** Connect on-premises data center to shared VPC.

**Using VPC Connector:**

```bash
# Create Private Service Connect endpoint (service proxy)
gcloud compute addresses create "{{user.connector_ip_name}}" \
  --region="{{user.region}}" \
  --nic-type="VIRTIO_NETWORK_ADAPTER"

# Create VPC Connector
gcloud compute networks vpc-connectors create "{{user.connector_name}}" \
  --region="{{user.region}}" \
  --range="{{user.connector_ip_range}}" \
  --subnet="{{user.subnet_name}}" \
  --project="{{user.service_project}}"

# Configure Cloud NAT in host project (if needed)
gcloud compute routers nats create "{{user.nat_name}}" \
  --region="{{user.region}}" \
  --router="{{user.router_name}}" \
  --nat-ip-allocate-mode="MANUAL_ONLY" \
  --nat-secondary-ip-allocation-mode="MANUAL_ONLY" \
  --source-subnetwork-ip-ranges-to-nat="ALL_SUBNETWORKS_ALL_IP_RANGES"
```

## Troubleshooting

### Issue: "Project is not associated with the shared VPC"

**Error Message:**
```
400 Bad Request: Project {{service_project_id}} is not associated
with the shared VPC network {{shared_vpc_name}}
```

**Diagnosis:**
```bash
# Check if service project is associated
gcloud compute networks describe "{{shared_vpc_name}}" \
  --project="{{host_project_id}}" \
  --format="json" | \
  jq '.peerNetworks[].name'
```

**Solution:**
```bash
# Associate service project
gcloud compute networks peerings associate-projects \
  --network="{{shared_vpc_name}}" \
  --project="{{host_project_id}}" \
  --service-projects="{{service_project_id}}"
```

---

### Issue: "Subnet in use by another project"

**Error Message:**
```
400 Bad Request: Subnet 10.0.0.0/24 is shared but not delegated
```

**Diagnosis:**

```bash
# Check subnet IAM bindings
gcloud compute networks subnets get-iam-policy \
  "{{subnet_name}}" \
  --region="{{user.region}}" \
  --project="{{user.host_project}}"
```

**Solution:**

```bash
# Add delegation (explicit grant)
gcloud compute networks subnets update "{{subnet_name}}" \
  --region="{{user.region}}" \
  --project="{{user.host_project}}" \
  --add-iam-policy-binding \
    member="serviceAccount:{{service_project}}-svc.iam.gserviceaccount.com" \
    role="roles/compute.networkUser"
```

---

### Issue: "Service Account not found in correct project"

**Error Message:**
```
400 Bad Request: Service account not found
```

**Diagnosis:**

```bash
# Verify service account exists in service project
gcloud iam service-accounts list \
  --project="{{user.service_project}}" \
  --filter="email:*@{{user.service_project}}.iam.gserviceaccount.com"
```

**Solution:**

```bash
# Create service account in service project
gcloud iam service-accounts create "{{account_name}}" \
  --display-name="{{account_display}}" \
  --project="{{user.service_project}}"

# Grant roles to service account
gcloud projects add-iam-policy-binding \
  "{{user.host_project}}" \
  --member="serviceAccount:{{account_email}}" \
  --role="roles/compute.networkUser"
```

---

### Issue: "VM creation failed - subnet not available"

**Diagnosis:**

```bash
# Check if VM can access the subnet (from service project)
gcloud compute instances list \
  --project="{{user.service_project}}" \
  --format="json"
```

**Solution:**

Ensure service account has `roles/compute.networkUser` role binding:

```bash
gcloud compute networks subnets get-iam-policy \
  "{{subnet_name}}" \
  --region="{{user.region}}" \
  --project="{{user.host_project}}" \
  --format=json > policy.json

# Update policy to include service account
jsonnet policy.json + '{"bindings":[{"role":"roles/compute.networkUser","members":["serviceAccount:{{service_account_email}}"]}]}' | \
  gcloud compute networks subnets set-iam-policy "{{subnet_name}}" \
  --region="{{user.region}}" \
  --project="{{user.host_project}}" \
  --format=json --from-file=-
```

---

### Issue: "Incomplete IPv4 Routing Table"

**Diagnosis:**

Use `traceroute` from VM to diagnose routing issues.

```bash
# Enable VPC Flow Logs for troubleshooting
gcloud compute networks subnets update "{{subnet_name}}" \
  --region="{{user.region}}" \
  --enable-flow-logs

# Check flow logs in Cloud Logging
gcloud logging read \
  "resource.type=compute_v1_network" \
  --project="{{user.host_project}}" \
  --format=json
```

**Solution:**

Verify routing configuration:

```bash
# List routes in shared VPC
gcloud compute routes list \
  --network="{{user.shared_vpc_name}}" \
  --project="{{user.host_project}}"

# Verify VM network interface
gcloud compute instances describe "{{vm_name}}" \
  --project="{{user.service_project}}" \
  --format=json | \
  jq '.networkInterfaces[].networkIP, .networkInterfaces[].subnetwork'
```

## Cost Considerations

### Cost Comparison: Standalone vs Shared VPC

| Area | Standalone VPC | Shared VPC | Savings |
|------|----------------|------------|---------|
| VPC network | 1 VPC (costless) | 1 VPC (costless) | — |
| Subnets | Multiple (costless) | Multiple (costless) | — |
| Firewall Rules | Multiple | 1 (global) | 50-80% |
| Routes | Multiple | 1 (global) | 50-80% |
| Cloud Router | Multiple | 1 | 50-80% |
| Management overhead | High | Low | 30-40% |

### Billing Impact

**Network Operation Costs:**

| Resource | Cost Model |
|----------|------------|
| VPC Network | $0 (free) |
| Subnet | $0 (free) |
| Firewalls | $0 (API calls only) |
| Routes | $0 (API calls only) |
| Cloud Router | $0 (API calls only) |

**Indirect Costs (improved by Shared VPC):**

| Item | Improvement |
|------|-------------|
| DevOps time managing many VPCs | ↘ 60-80% |
| Network audit scope | ↘ 70-90% |
| Configuration drift detection | ↘ 50-70% |
| On-call incident scope | ↘ 50-80% |

### Savings Summary

**Before Shared VPC:**

- 5 projects × 1 VPC each = 5 VPCs (10% to 15% overhead)
- 5 firewalls (same rules repeated × 5)
- Centralized management overhead (est. 40-50 hrs/month)

**After Shared VPC:**

- 1 VPC across all 5 projects (centralized management)
- 1 global firewall (reused across all projects)
- On-call scope reduced by 80%

**Estimated Savings:** 30-40% reduction in network management costs per year.

## See Also

- [Cloud Router Documentation](https://cloud.google.com/vpc/docs/cloud-router)
- [VPC Network Peering](https://cloud.google.com/vpc/docs/vpc-peering)
- [Private Service Connect](./private-service-connect.md)
- [Cloud NAT Best Practices](../monitoring.md#networking)
