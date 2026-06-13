# Google Cloud VPC — Operational Best Practices

## Hierarchical Firewall

Use hierarchical firewall policies (at folder/organization level) for consistent rules across projects:

```bash
gcloud compute security-policies list --organization=ORG_ID
gcloud compute security-policies rules list --policy=POLICY_ID
```

## Shared VPC

Use Shared VPC for multi-project isolation with centralized network administration:

```bash
# Enable Shared VPC (host project)
gcloud compute shared-vpc enable PROJECT_ID

# Grant service project access
gcloud compute shared-vpc associated-projects add PROJECT_ID \
  --host-project=HOST_PROJECT_ID
```

## Subnet CIDR Planning

Allocate /16 for network, /20-24 per subnet; leave room for expansion:

| Network CIDR | Subnet CIDR | Capacity | Use Case |
|--------------|-------------|----------|----------|
| 10.0.0.0/16 | 10.0.1.0/24 | 254 IPs | Small workload |
| 10.0.0.0/16 | 10.0.10.0/20 | 4094 IPs | Medium workload |
| 10.1.0.0/16 | 10.1.0.0/20 | 4094 IPs | Second region |

## VPC Flow Logs

Enable for critical subnets; sample rate 1:1 for security, 1:10 for cost savings:

```bash
gcloud compute networks subnets update SUBNET_NAME \
  --region=REGION \
  --enable-flow-logs \
  --flow-sampling=0.5
```

## Private Google Access

Enable on subnets for VM-to-Google-API traffic without external IP:

```bash
gcloud compute networks subnets update SUBNET_NAME \
  --region=REGION \
  --enable-private-ip-google-access
```

## Cloud NAT

Use Cloud NAT for private VM internet access; avoid public IPs on VMs when possible:

```bash
gcloud compute routers nats create NAT_CONFIG \
  --router=ROUTER_NAME \
  --region=REGION \
  --auto-allocate-nat-external-ips \
  --subnetworks=SUBNET_SELF_LINK
```

## Peering

Never peer networks with overlapping CIDRs; use export/import custom routes selectively:

```bash
# Check for overlapping CIDRs before peering
gcloud compute networks peering list --network=NETWORK_NAME
```
