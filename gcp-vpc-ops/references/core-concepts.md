# Core Concepts — Google Cloud VPC

> **Architecture:** GCP VPC is a global, scalable networking resource that provides connectivity for Compute Engine VMs, GKE clusters, Cloud SQL instances, and other GCP services.

## VPC Network Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Auto-mode** | Subnets created automatically in every region (one per region) with a /20 CIDR | Simple projects, prototyping |
| **Custom-mode** | User defines subnets with custom CIDR ranges per region | Production, multi-environment, strict CIDR planning |

## Resource Hierarchy

```
Organization
└── Folder(s)
    └── Project
        └── VPC Network (global)
            ├── Subnet (regional)
            ├── Firewall Rule (global)
            ├── Route (global)
            ├── VPC Peering (global)
            ├── VPN Gateway (regional)
            ├── Cloud Router (regional)
            │   └── Cloud NAT (regional)
            └── Private Service Connection (global)
```

## Key Concepts

### Subnets
- Regional resources — each subnet belongs to one region
- CIDR range must be within RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Cannot overlap with other subnets in the same network
- Primary range for VM IPs; secondary ranges for GKE pods/services
- Private Google Access and VPC Flow Logs are per-subnet settings

### Firewall Rules
- Global resources — evaluated at the network edge
- Implicit deny-all ingress and allow-all egress (cannot delete, can override)
- Stateful: return traffic is automatically allowed
- Priority 0-65535 (lower number = higher priority)
- Can target by: network tags, service accounts, or all instances

### Routes
- Global resources — define packet next-hop destinations
- Default routes: default-internet-gateway (0.0.0.0/0) and subnet routes automatically created
- Custom routes: user-defined for specific next-hops
- System-generated routes cannot be deleted

### VPC Peering
- Direct RFC 1918 connectivity between two VPC networks
- Non-transitive — peered networks cannot reach each other's peers
- Maximum 25 peerings per VPC network
- CIDR ranges must not overlap

### Cloud NAT
- Regional managed NAT gateway
- Allows private VM instances to reach the internet
- Uses Cloud Router for dynamic routing
- Supports manual and automatic NAT IP allocation

### Cloud VPN (HA VPN)
- Regional, highly available VPN gateway with two external IPs
- Supports IKEv1 and IKEv2
- 99.99% SLA for HA VPN
- Classic VPN: single-IP gateway (99.9% SLA, legacy)

## Limits and Quotas

| Resource | Default Quota | Can Be Increased? |
|----------|---------------|-------------------|
| VPC Networks per project | 5 (auto-mode) / 15 (custom-mode) | Yes |
| Subnets per VPC network | 1,000 per region | Yes |
| Firewall Rules per project | 500 (inclusive of implied rules) | Yes |
| VPC Peerings per network | 25 (custom-mode) / 10 (auto-mode) | Yes |
| Routes per project | 250 | Yes |
| VPN Tunnels per region | 15 (HA VPN) / 3 (Classic VPN) | Yes |
| Cloud NAT Gateways per region | 2 per VPC | Yes |
| Subnet CIDR max size | /8 | No |

## Dependencies

| Resource | Depends On | Notes |
|----------|-----------|-------|
| Subnet | VPC Network | Cannot create subnet without parent network |
| Firewall Rule | VPC Network | Target network must exist |
| Route | VPC Network | Parent network must exist |
| VPN Tunnel | VPN Gateway + Cloud Router | Gateway and Router must exist first |
| Cloud NAT | Cloud Router | Router must exist in the region |
| VPC Peering | VPC Networks (both sides) | Both networks must exist; CIDR overlap checked |

## SPOF Analysis

| Component | SPOF Risk | Mitigation |
|-----------|-----------|------------|
| VPC Network | Low — GCP manages global network | N/A (managed service) |
| Cloud NAT | Medium — single region | Deploy NAT in multiple regions |
| HA VPN | Low — two tunnels per gateway | AWS/on-prem uses both tunnels |
| Classic VPN | **High** — single tunnel | Migrate to HA VPN |
| VPC Peering | Low — GCP manages | CIDR planning for future expansion |