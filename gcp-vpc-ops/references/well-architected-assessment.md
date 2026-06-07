# Well-Architected Assessment — Google Cloud VPC

> **Purpose:** Maps VPC skill operations to the Google Cloud Architecture Framework five pillars.

## 2.1 Security Pillar (安全)

### Required IAM Roles

| API Operation | Required IAM Role |
|---------------|------------------|
| Create/Delete VPC Network | `roles/compute.networkAdmin` |
| Create/Describe/Delete Subnet | `roles/compute.networkAdmin` |
| Create/Update/Delete Firewall Rules | `roles/compute.securityAdmin` |
| Create/Delete Routes | `roles/compute.networkAdmin` |
| Create/Delete VPN Tunnels | `roles/compute.networkAdmin` |
| Create/Delete Cloud NAT | `roles/compute.networkAdmin` |
| Read-only operations (describe/list) | `roles/compute.viewer` |

### Credential Safety
- Never log `sharedSecret` values from VPN tunnel describe output
- Shared secrets in VPN tunnel creation MUST be passed via env var or securely generated
- Service account keys must use `roles/compute.networkAdmin` not `roles/owner`

### Network Security

| Feature | Recommendation |
|---------|---------------|
| Firewall rules | Use tag-based and service-account-based rules instead of CIDR-only |
| Private Google Access | Enable on all subnets for secure API access |
| VPC Service Controls | Use for sensitive data perimeters |
| Cloud IAP | Use for SSH/RDP access instead of public IP + firewall |
| SSL/VPN | Use HA VPN with IKEv2 for on-prem connectivity |

## 2.2 Stability Pillar (稳定)

### Backup & Recovery

| Component | Backup Strategy | Recovery |
|-----------|----------------|----------|
| VPC Network config | IaC (Terraform/Deployment Manager) | Re-deploy from config |
| Firewall rules | Export as YAML/JSON | Re-apply from export |
| Cloud Router config | Document BGP settings | Reconfigure via gcloud |
| VPN config | Document peer IPs, shared secrets, IKE versions | Recreate tunnels |

### Multi-Region / High Availability

| Component | HA Strategy |
|-----------|-------------|
| HA VPN | Two tunnels per gateway; active-active across regions |
| Cloud NAT | Deploy NAT gateways in at least 2 zones per region |
| VPC Network | Global network inherently HA; subnets per region for regional isolation |

## 2.3 Cost Pillar (成本)

| Resource | Pricing Model | Optimization |
|----------|--------------|--------------|
| VPC Networks | Free (no charge for networks themselves) | Use custom-mode to avoid auto-created unused subnets |
| VPN Tunnels | Per-hour per tunnel | Use HA VPN (same cost as classic but HA) |
| Cloud NAT | Per gateway hour + data processing | Use automatic NAT IP allocation; prune idle NAT IPs |
| VPC Flow Logs | Per GB ingested | Lower sampling rate (0.25-0.5) for non-critical subnets |
| External IPs | Per hour per static IP | Release unused static IPs |

## 2.4 Efficiency Pillar (效率)

### Automation Patterns

```bash
# Export all firewall rules as JSON for auditing
gcloud compute firewall-rules list --format="json" > firewall_rules_backup.json

# Batch create firewall rules from config file
for rule in $(cat rules.json | jq -c '.[]'); do
  echo "$rule" | gcloud compute firewall-rules create --project="{{env.CLOUDSDK_CORE_PROJECT}}" ...
done

# Use tags for consistent firewall rule targeting
gcloud compute instances add-tags "{{user.instance_name}}" \
  --tags=web-server,prod \
  --zone="{{user.zone}}"
```

## 2.5 Performance Pillar (性能)

### Key Metrics & Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| NAT connections used | > 80% of limit | Add more NAT IPs or deploy additional NAT gateways |
| VPN tunnel packet loss | > 1% for 5min | Check connectivity; verify HA tunnel failover |
| Subnet IP utilization | > 90% | Expand subnet CIDR or create new subnet |
| Firewall rule count | > 400 | Consolidate rules; use hierarchical firewall policies |
| VPC Flow Logs volume | > 1TB/day | Reduce sampling rate or aggregation interval |

### Performance Optimization

- Use global routing mode for VPC peering with multiple regions
- Prefer subnet CIDR /16-20 for production to leave growth room
- Enable VPC Flow Logs only on critical subnets (not all)
- Use Cloud Router with BGP for dynamic routing instead of static routes