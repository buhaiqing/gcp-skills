# Private Service Connect — Google Cloud VPC

> Provides network administrators with a complete guide to implementing Private Service Connect (PSC) in Google Cloud — publishing services, consuming services, and managing endpoints across VPC boundaries.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Publishing a Service](#publishing-a-service)
5. [Consuming a Service](#consuming-a-service)
6. [Google-Provided Services](#google-provided-services)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Comparison with VPC Peering](#comparison-with-vpc-peering)
10. [See Also](#see-also)

## Overview

**Private Service Connect** enables private consumption of Google Cloud services and custom services across VPC network boundaries without requiring VPC peering, VPN, or public IP addresses.

### Key Capabilities

| Capability | Description |
|------------|-------------|
| Publish Service | Expose a service running in your VPC to consumers in other VPCs |
| Consume Service | Access published services privately via internal IP |
| Google-Provided Services | Access Google Cloud APIs (Cloud SQL, Memorystore, Pub/Sub, etc.) privately |
| No Peering Required | Traffic flows through Private Service Connect endpoints, not VPC peering |

### Use Cases

- Privately access Google Cloud managed services without public IPs
- Publish custom services to other projects/orgs
- Create a service mesh across organizational boundaries
- Avoid VPC peering CIDR overlap issues

## Architecture

```
Producer VPC (Project A)                    Consumer VPC (Project B)
┌─────────────────────────┐                ┌─────────────────────────┐
│                         │                │                         │
│  Service Attachment     │                │  Private Service        │
│  ┌───────────────────┐  │                │  Connect Endpoint       │
│  │ ILB / NEG         │  │  ─────────►   │  ┌───────────────────┐  │
│  │   (Service)       │  │   Private     │  │ 10.0.1.5 (Internal │  │
│  │                   │  │   Connection  │  │     IP Address)    │  │
│  └───────────────────┘  │                │  └───────────────────┘  │
│  └── Service Attachment  │                │                         │
│      ┌───────────────┐   │                │  VM / GKE Pod           │
│      │ Target: ILB   │   │                │  ┌───────────────────┐  │
│      │ Connection    │   │                │  │ Connects to       │  │
│      │ Limit: 100    │   │                │  │ 10.0.1.5:443      │  │
│      └───────────────┘   │                │  └───────────────────┘  │
└─────────────────────────┘                └─────────────────────────┘
```

### Data Flow

1. **Producer** creates a Service Attachment pointing to a backend service (ILB/NEG)
2. **Consumer** creates a Private Service Connect endpoint with a forwarded IP address
3. Consumer's endpoint connects to producer's Service Attachment
4. Traffic flows from consumer's internal IP to producer's backend service

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Compute API enabled | `gcloud services list --enabled --filter="name:compute.googleapis.com"` | Enabled | `gcloud services enable compute.googleapis.com` |
| IAM - Service Attachment Admin | `gcloud projects get-iam-policy` | `roles/compute.serviceAttachmentAdmin` | Grant to producer |
| IAM - Network User | `gcloud projects get-iam-policy` | `roles/compute.networkUser` | Grant to consumer |
| Project org policy | `gcloud resource-manager org-policies describe` | PSC allowed | Update org policy |

## Publishing a Service

### Step 1: Create Backend Service (Producer)

Create an Internal Load Balancer or Network Endpoint Group as the backend:

```bash
# Create instance group
gcloud compute instance-groups unmanaged create "{{user.instance_group_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --zone="{{user.zone}}"

# Create health check
gcloud compute health-checks create tcp "{{user.health_check_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --port=443

# Create backend service
gcloud compute backend-services create "{{user.backend_service_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --load-balancing-scheme=INTERNAL_MANAGED \
  --protocol=HTTP \
  --health-checks="{{user.health_check_name}}" \
  --region="{{user.region}}"

# Add instance group to backend
gcloud compute backend-services add-backend "{{user.backend_service_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --instance-group="{{user.instance_group_name}}" \
  --instance-group-zone="{{user.zone}}" \
  --region="{{user.region}}"
```

### Step 2: Create Forwarding Rule

```bash
# Reserve internal IP for the forwarding rule
gcloud compute addresses create "{{user.psc_forwarding_rule_ip}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --subnet="{{user.subnet_name}}" \
  --addresses="{{user.internal_ip}}"

# Create forwarding rule
gcloud compute forwarding-rules create "{{user.forwarding_rule_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --load-balancing-scheme=INTERNAL_MANAGED \
  --network="{{user.network_name}}" \
  --subnet="{{user.subnet_name}}" \
  --address="{{user.psc_forwarding_rule_ip}}" \
  --ports=443 \
  --backend-service="{{user.backend_service_name}}" \
  --format="json"
```

### Step 3: Create Service Attachment

```bash
# Pre-flight: Verify forwarding rule exists
gcloud compute forwarding-rules describe "{{user.forwarding_rule_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}"

# Create Service Attachment
gcloud compute service-attachments create "{{user.service_attachment_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --target-service="{{user.forwarding_rule_name}}" \
  --connection-preference=ACCEPT_AUTOMATIC \
  --nat-subnets="{{user.nat_subnet_name}}" \
  --format="json"
```

**Execution — Python SDK:**

```python
# create_service_attachment.py
from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = compute_v1.ServiceAttachmentsClient()

# Create service attachment
service_attachment = compute_v1.ServiceAttachment()
service_attachment.name = "{{user.service_attachment_name}}"
service_attachment.connection_preference = "ACCEPT_AUTOMATIC"
service_attachment.target_service = f"https://www.googleapis.com/compute/v1/projects/{project}/regions/{{user.region}}/forwardingRules/{{user.forwarding_rule_name}}"
service_attachment.nat_subnets = [
    f"https://www.googleapis.com/compute/v1/projects/{project}/regions/{{user.region}}/subnetworks/{{user.nat_subnet_name}}"
]

op = client.insert(
    project=project,
    region="{{user.region}}",
    service_attachment_resource=service_attachment
)

def wait_for_operation(operation):
    while True:
        operation.reload()
        if operation.error or operation.status == "DONE":
            break
        time.sleep(5)

wait_for_operation(op)
print(f"Service attachment {{service_attachment.name}} created")
print(f"Connection URI: projects/{project}/regions/{{user.region}}/serviceAttachments/{{user.service_attachment_name}}")
```

### Post-execution Validation

| Step | Command | Expected | On Failure |
|------|---------|----------|------------|
| Verify attachment | `gcloud compute service-attachments describe {{user.service_attachment_name}} --region={{user.region}}` | Attachment exists | HALT; creation failed |
| Check target | `jq '.targetService'` | Points to correct forwarding rule | HALT; wrong target |
| Check connection URI | `jq '.selfLink'` | Full URI for consumer to use | WARN; missing URI |

## Consuming a Service

### Step 1: Create PSC Endpoint (Consumer)

```bash
# Reserve IP address for endpoint
gcloud compute addresses create "{{user.psc_endpoint_ip_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --subnet="{{user.subnet_name}}" \
  --addresses="{{user.consumer_ip}}"

# Create PSC forwarding rule (endpoint)
gcloud compute forwarding-rules create "{{user.psc_endpoint_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --network="{{user.network_name}}" \
  --subnet="{{user.subnet_name}}" \
  --address="{{user.psc_endpoint_ip_name}}" \
  --target-service-attachment="projects/{{user.producer_project}}/regions/{{user.region}}/serviceAttachments/{{user.service_attachment_name}}" \
  --format="json"
```

**Execution — Python SDK:**

```python
# create_psc_endpoint.py
from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
fr_client = compute_v1.ForwardingRulesClient()

forwarding_rule = compute_v1.ForwardingRule()
forwarding_rule.name = "{{user.psc_endpoint_name}}"
forwarding_rule.region = f"https://www.googleapis.com/compute/v1/projects/{project}/regions/{{user.region}}"
forwarding_rule.network = f"https://www.googleapis.com/compute/v1/projects/{project}/global/networks/{{user.network_name}}"
forwarding_rule.subnetwork = f"https://www.googleapis.com/compute/v1/projects/{project}/regions/{{user.region}}/subnetworks/{{user.subnet_name}}"
forwarding_rule.IP_address = "{{user.consumer_ip}}"
forwarding_rule.target_service_attachment = f"projects/{{user.producer_project}}/regions/{{user.region}}/serviceAttachments/{{user.service_attachment_name}}"
forwarding_rule.load_balancing_scheme = ""  # PSC endpoints use empty scheme

op = fr_client.insert(
    project=project,
    region="{{user.region}}",
    forwarding_rule_resource=forwarding_rule
)

def wait_for_operation(operation):
    while True:
        operation.reload()
        if operation.error or operation.status == "DONE":
            break
        time.sleep(5)

wait_for_operation(op)
print(f"PSC endpoint {{forwarding_rule.name}} created")
print(f"Internal IP: {{user.consumer_ip}}")
```

### Step 2: Verify Connectivity

```bash
# Test connectivity from consumer VM to PSC endpoint
gcloud compute ssh "{{user.vm_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --zone="{{user.zone}}" \
  --command="curl -s -o /dev/null -w '%{http_code}' https://{{user.consumer_ip}}:443"

# Expected: 200 or appropriate service response
```

### Post-execution Validation

| Step | Command | Expected | On Failure |
|------|---------|----------|------------|
| Verify endpoint | `gcloud compute forwarding-rules describe {{user.psc_endpoint_name}} --region={{user.region}}` | Endpoint exists | HALT; creation failed |
| Check status | `jq '.pscConnectionStatus'` | `ACCEPTED` or `PENDING` | HALT; check producer acceptance |
| Connectivity test | `gcloud compute ssh {{user.vm_name}} -- curl https://{{user.consumer_ip}}:443` | Service response | HALT; check firewall/routes |

## Google-Provided Services

### Cloud SQL

```bash
# Create Private Service Connect endpoint for Cloud SQL
gcloud compute forwarding-rules create "cloudsql-psc-endpoint" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --network="{{user.network_name}}" \
  --subnet="{{user.subnet_name}}" \
  --address="{{user.cloudsql_ip}}" \
  --target-service-attachment="projects/{{user.producer_project}}/regions/{{user.region}}/serviceAttachments/cloudsql-{{user.cloudsql_instance_id}}"
```

### Memorystore (Redis)

```bash
# Create PSC endpoint for Memorystore Redis
gcloud compute forwarding-rules create "redis-psc-endpoint" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --network="{{user.network_name}}" \
  --subnet="{{user.subnet_name}}" \
  --address="{{user.redis_ip}}" \
  --target-service-attachment="projects/{{user.producer_project}}/regions/{{user.region}}/serviceAttachments/redis-{{user.redis_instance_id}}"
```

### Google APIs (Private Access)

```bash
# Enable Private Google Access
gcloud compute networks subnets update "{{user.subnet_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --enable-private-ip-google-access

# Verify
gcloud compute networks subnets describe "{{user.subnet_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --format="json" | jq '.privateIpGoogleAccess'
```

## Best Practices

### Security

| Practice | Implementation |
|----------|---------------|
| Connection preference | Use `ACCEPT_MANUAL` for explicit consumer whitelist |
| NAT subnet isolation | Dedicated /28 NAT subnet for service attachment |
| IAM least privilege | Grant `compute.serviceAttachmentUser` not admin |
| Firewall rules | Restrict access to PSC endpoint IP only |
| Audit logging | Enable `DATA_READ`/`DATA_WRITE` audit logs for PSC |

### Cost

| Resource | Cost Consideration |
|----------|-------------------|
| Service Attachment | Free (compute API costs only) |
| PSC Endpoint | Free (compute API costs only) |
| NAT Subnet IPs | IP address costs if using static IPs |
| Data Transfer | Standard egress charges apply |

### Performance

- Use PSC endpoints in the same region as the service for lowest latency
- For cross-region access, expect ~10-20ms additional latency
- NAT subnet should be /28 minimum for HA
- Monitor connection status with `gcloud compute forwarding-rules describe`

## Troubleshooting

### Issue: "PSC Connection PENDING"

**Error:**
Connection status shows `PENDING` instead of `ACCEPTED`.

**Diagnosis:**
```bash
gcloud compute forwarding-rules describe "{{user.psc_endpoint_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --format="json" | jq '.pscConnectionStatus'
```

**Solution:**
Producer must accept the connection:
```bash
gcloud compute service-attachments update "{{user.service_attachment_name}}" \
  --project="{{user.producer_project}}" \
  --region="{{user.region}}" \
  --producer-accept-list="{{user.consumer_project}}"
```

---

### Issue: "NAT subnet exhausted"

**Error:**
Cannot create more PSC endpoints due to NAT subnet IP exhaustion.

**Diagnosis:**
```bash
gcloud compute networks subnets describe "{{user.nat_subnet_name}}" \
  --region="{{user.region}}" \
  --project="{{user.producer_project}}" \
  --format="json" | jq '.ipCidrRange'
```

**Solution:**
Expand NAT subnet CIDR or create additional NAT subnets:
```bash
gcloud compute networks subnets expand-ip-cidr-range "{{user.nat_subnet_name}}" \
  --region="{{user.region}}" \
  --project="{{user.producer_project}}" \
  --prefix-length=28
```

---

### Issue: "Org policy blocks PSC"

**Error:**
`403 Forbidden` - Organization policy constraint `compute.restrictServiceAttachmentUsage` blocks PSC.

**Diagnosis:**
```bash
gcloud resource-manager org-policies describe \
  constraints/compute.restrictServiceAttachmentUsage \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

**Solution:**
Update org policy to allow PSC:
```bash
# Create policy file
cat > psc_policy.yaml <<EOF
constraint: constraints/compute.restrictServiceAttachmentUsage
listPolicy:
  allowedValues:
    - "projects/{{env.CLOUDSDK_CORE_PROJECT}}"
EOF

gcloud resource-manager org-policies set-policy psc_policy.yaml \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

---

### Error Taxonomy

| Error Code | Message | Cause | Resolution |
|------------|---------|-------|------------|
| 400 | `INVALID_FORWARDING_RULE` | Wrong forwarding rule type | Use `--load-balancing-scheme=INTERNAL_MANAGED` |
| 403 | `CONNECTION_NOT_ALLOWED` | Producer hasn't accepted | Check connection preference or update accept list |
| 404 | `SERVICE_ATTACHMENT_NOT_FOUND` | Wrong URI | Verify full URI: `projects/PROJECT/regions/REGION/serviceAttachments/NAME` |
| 409 | `ENDPOINT_ALREADY_EXISTS` | Duplicate endpoint name | Use unique name or delete existing |
| 412 | `NAT_SUBNET_INSUFFICIENT` | NAT subnet too small | Use /28 or larger for NAT subnet |

## Comparison with VPC Peering

| Feature | Private Service Connect | VPC Peering |
|---------|------------------------|-------------|
| CIDR Overlap | ✅ No overlap issues | ❌ Must be non-overlapping |
| Cross-Organization | ✅ Supported | ✅ Supported |
| Service Exposure | ✅ Granular (per-service) | ❌ Full network access |
| Routing | ✅ Consumer routes to endpoint | ❌ Full route exchange |
| IAM Control | ✅ Fine-grained (per-attachment) | ❌ Coarse (per-network) |
| Cost | Free (API costs only) | Free |
| Latency | ~1ms (same region) | ~0.5ms (direct) |
| Use Case | Service publishing/consuming | Network connectivity |

## See Also

- [Private Service Connect Documentation](https://cloud.google.com/vpc/docs/private-service-connect)
- [Service Attachment Concepts](https://cloud.google.com/vpc/docs/service-attachments)
- [Shared VPC Setup](./shared-vpc-setup.md)
- [VPC Network Peering](https://cloud.google.com/vpc/docs/vpc-peering)
- [Cloud NAT Best Practices](../monitoring.md#networking)