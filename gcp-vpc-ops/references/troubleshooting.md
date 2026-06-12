# Troubleshooting — Google Cloud VPC

## Common API Error Codes

| gRPC Code / HTTP | Meaning | Agent Action |
|-------------|---------|--------------|
| `INVALID_ARGUMENT` / 400 | Invalid CIDR, firewall rule, or resource config | Check param values against REST API reference |
| `PERMISSION_DENIED` / 403 | Insufficient IAM permissions | Grant `roles/compute.networkAdmin` |
| `NOT_FOUND` / 404 | Network/subnet/firewall rule does not exist | Verify resource name and region |
| `ALREADY_EXISTS` / 409 | Resource with this name already exists | Use a different name or describe existing |
| `QUOTA_EXCEEDED` / 429 | Network/subnet/firewall quota hit | Delete unused resources or request increase |
| `RESOURCE_IN_USE` / 400 | Network/subnet has dependent resources | Delete dependent resources first |
| `INTERNAL` / 500 | Server-side error | Retry with backoff; then HALT |
| `UNAVAILABLE` / 503 | Service temporarily unavailable | Retry with exponential backoff (max 3) |
| `ABORTED` / 409 | Operation conflict | Wait for conflicting operation to finish |
| `RATE_LIMIT_EXCEEDED` / 429 | API rate limit hit (distinct from quota) | Back off and retry; reduce request frequency |
| `PRECONDITION_FAILED` / 412 | Resource state changed since last read | Re-read resource and retry with fresh fingerprint |

## Diagnostic Order (Connectivity Issues)

### 1. Identify the affected resources
```bash
# Check if instance exists and has network interface
gcloud compute instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" --format="json" | jq '.networkInterfaces[] | {network, networkIP, natIP}'
```

### 2. Verify subnet and firewall rules
```bash
# Check subnet configuration
gcloud compute networks subnets describe "{{user.subnet_name}}" \
  --region="{{user.region}}" --format="json"

# Verify firewall rules affecting the instance
gcloud compute firewall-rules list \
  --filter="network:{{user.network_name}}" \
  --format="json" | jq '.[] | {name, direction, sourceRanges, allowed, targetTags}'
```

### 3. Check routes
```bash
gcloud compute routes list \
  --filter="network:{{user.network_name}}" \
  --format="json"
```

### 4. Test connectivity
```bash
# Use gcloud compute ssh to run connectivity test
gcloud compute ssh "{{user.instance_name}}" \
  --zone="{{user.zone}}" \
  --command="ping -c 3 {{user.target_ip}}" 2>/dev/null

# If Cloud NAT issue, verify NAT config
gcloud compute routers nats list \
  --region="{{user.region}}" \
  --router="{{user.router_name}}" \
  --format="json"
```

### 5. Check VPC Flow Logs (if enabled)
```bash
gcloud logging read 'resource.type="gce_subnetwork" AND logName:"compute.googleapis.com/vpc_flows"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=10 \
  --format="json"
```

## Product-Specific Error Patterns

### Network Delete Fails
| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| `ERROR: (gcloud.compute.networks.delete) Resource in use` | VMs, subnets, or firewall rules still attached | List all dependent resources and delete them first |
| `ERROR: (gcloud.compute.networks.delete) Could not fetch resource` | Network has auto-mode default subnets | Delete all subnets in all regions before network |
| `ERROR: (gcloud.compute.networks.delete) Peerings still active` | VPC peering active | Delete peering on both sides first |

### Firewall Rule Issues
| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| Instances unreachable | Firewall rule missing or incorrect | Verify direction, sourceRanges, targetTags match instance tags |
| Instances reachable when shouldn't be | Lower-priority rule allowing traffic | Check priority values (lower number = evaluated first) |
| Tag-based rule not applying | Instance missing network tag | Add tag: `gcloud compute instances add-tags` |

### Subnet Issues
| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| CIDR overlap error | Subnet range overlaps with existing subnet | Choose non-overlapping CIDR |
| Private Google Access not working | Not enabled on subnet | `gcloud compute networks subnets update --private-ip-google-access` |
| Cannot expand subnet CIDR | Expansion would overlap with other subnet | Choose non-overlapping expanded range |

### VPC Peering Issues
| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| Routing not working | Custom routes not exported/imported | Check `--export-custom-routes` and `--import-custom-routes` flags |
| Peering creation fails | CIDR overlap | Verify no overlapping CIDRs between networks |
| Cannot delete VPC network | Peering active | Delete peering on both sides; `gcloud compute networks peerings delete` |

### VPN Tunnel Issues
| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| Tunnel status not ESTABLISHED | IKE config mismatch, firewall blocking port 500/4500 | Verify IKE version, shared secret, peer IP, and firewall rules on both sides |
| Intermittent connectivity | Tunnel flapping | Check Cloud Router BGP session status; verify HA VPN both tunnels active |
| Traffic not routing | Route missing for remote CIDR | Create route with `--next-hop-vpn-tunnel` pointing to the tunnel |

## Diagnostic Commands

```bash
# VPC network connectivity test
gcloud compute networks subnets list-usable \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Check firewall rule effective for an instance
gcloud compute firewall-rules list \
  --filter="network:{{user.network_name}} AND direction=INGRESS" \
  --format="json" | jq '.[] | select(.targetTags == null or .targetTags[] == "{{user.tag}}")'

# Cloud NAT diagnostics
gcloud compute routers describe "{{user.router_name}}" \
  --region="{{user.region}}" \
  --format="json" | jq '.nats[] | {name, natIpAllocateOption, sourceSubnetworkIpRangesToNat, natIps}'

# Verify VPC peering status
gcloud compute networks peerings list \
  --network="{{user.network_name}}" \
  --format="json" | jq '.[] | {name, peerNetwork, state, exportCustomRoutes, importCustomRoutes}'
```