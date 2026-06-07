# API & SDK — Google Cloud VPC

> **REST API:** `https://compute.googleapis.com/compute/v1/`
> **Discovery doc:** `https://compute.googleapis.com/$discovery/rest?version=v1`
> **Go SDK:** `cloud.google.com/go/compute/apiv1`
> **Python SDK:** `google-cloud-compute`

## SDK Operations Map

| Goal | REST Method & Path | gcloud Command | Go SDK Method |
|------|-------------------|---------------|---------------|
| Create Network | `POST /v1/projects/{project}/global/networks` | `gcloud compute networks create` | `networks.Insert` |
| Describe Network | `GET /v1/projects/{project}/global/networks/{network}` | `gcloud compute networks describe` | `networks.Get` |
| Delete Network | `DELETE /v1/projects/{project}/global/networks/{network}` | `gcloud compute networks delete` | `networks.Delete` |
| List Networks | `GET /v1/projects/{project}/global/networks` | `gcloud compute networks list` | `networks.List` |
| Create Subnet | `POST /v1/projects/{project}/regions/{region}/subnetworks` | `gcloud compute networks subnets create` | `subnetworks.Insert` |
| Describe Subnet | `GET .../regions/{region}/subnetworks/{subnet}` | `gcloud compute networks subnets describe` | `subnetworks.Get` |
| Delete Subnet | `DELETE .../regions/{region}/subnetworks/{subnet}` | `gcloud compute networks subnets delete` | `subnetworks.Delete` |
| List Subnets | `GET .../regions/{region}/subnetworks` | `gcloud compute networks subnets list` | `subnetworks.List` |
| Create Firewall Rule | `POST /v1/projects/{project}/global/firewalls` | `gcloud compute firewall-rules create` | `firewalls.Insert` |
| Describe Firewall Rule | `GET /v1/projects/{project}/global/firewalls/{rule}` | `gcloud compute firewall-rules describe` | `firewalls.Get` |
| Update Firewall Rule | `PUT /v1/projects/{project}/global/firewalls/{rule}` | `gcloud compute firewall-rules update` | `firewalls.Update` |
| Delete Firewall Rule | `DELETE /v1/projects/{project}/global/firewalls/{rule}` | `gcloud compute firewall-rules delete` | `firewalls.Delete` |
| Create Route | `POST /v1/projects/{project}/global/routes` | `gcloud compute routes create` | `routes.Insert` |
| Delete Route | `DELETE /v1/projects/{project}/global/routes/{route}` | `gcloud compute routes delete` | `routes.Delete` |
| Create VPN Gateway | `POST .../regions/{region}/vpnGateways` | `gcloud compute vpn-gateways create` | `vpnGateways.Insert` |
| Create VPN Tunnel | `POST .../regions/{region}/vpnTunnels` | `gcloud compute vpn-tunnels create` | `vpnTunnels.Insert` |
| Create Cloud NAT | `POST .../regions/{region}/routers/{router}` (PATCH) | `gcloud compute routers nats create` | `routers.Patch` (NAT sub-resource) |
| Create VPC Peering | `POST .../global/networks/{network}/addPeering` | `gcloud compute networks peerings create` | `networks.AddPeering` |

## Request / Response Notes

### Pagination
- All list operations use `pageToken` / `maxResults` / `nextPageToken`
- Default `maxResults`: 500

### Long-Running Operations
- Create/Delete network, subnet, VPN gateway/tunnel are async
- Returns `operation` object with `{name, status, targetLink, error}`
- Poll via `GET .../global/operations/{opId}` or `GET .../regions/{region}/operations/{opId}`
- Firewall rules are synchronous (no operation tracking)

### Required Fields (Create)

| Resource | Required Fields |
|----------|----------------|
| Network | `name` |
| Subnet | `name`, `network`, `ipCidrRange`, `region` |
| Firewall Rule | `name`, `network`, `direction`, `allowed` or `denied` |
| Route | `name`, `network`, `destRange`, `nextHop*` |
| VPN Tunnel | `name`, `targetVpnGateway`, `peerIp`, `sharedSecret` |
| VPC Peering | `name`, `network`, `peerNetwork` |

### Key Enum Values

| Field | Values |
|-------|--------|
| Network `routingMode` | `REGIONAL`, `GLOBAL` |
| Subnet `privateIpGoogleAccess` | `true`, `false` |
| Subnet `enableFlowLogs` | `true`, `false` |
| Firewall `direction` | `INGRESS`, `EGRESS` |
| Firewall `allowed[].IPProtocol` | `tcp`, `udp`, `icmp`, `esp`, `ah`, `sctp`, or number |
| Firewall action | Allowed (implicit from `allowed[]` field) vs `denied[]` |
| Firewall `priority` | 0-65535 |
| Route `nextHop*` | `nextHopGateway`, `nextHopInstance`, `nextHopIp`, `nextHopVpnTunnel` |
| VPN `ikeVersion` | 1, 2 |