# gcloud — Google Cloud VPC CLI

> **Install:** See [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
> **Credentials:** Set `GOOGLE_APPLICATION_CREDENTIALS` or run `gcloud auth login`

## Conventions (agent execution)
- Always use `--format=json` for machine-parseable output
- Use `jq` for field extraction from JSON output
- Network create/delete are async — poll with `gcloud compute operations describe`
- Firewall rule create/delete are synchronous (no polling needed)

## CLI vs API Coverage Gap

| Operation (REST API) | Available via `gcloud`? | Notes |
|---------------------|------------------------|-------|
| Create Network | yes | `gcloud compute networks create` |
| Describe Network | yes | `gcloud compute networks describe` |
| Delete Network | yes | `gcloud compute networks delete` |
| List Networks | yes | `gcloud compute networks list` |
| Create Subnet | yes | `gcloud compute networks subnets create` |
| Describe Subnet | yes | `gcloud compute networks subnets describe` |
| Delete Subnet | yes | `gcloud compute networks subnets delete` |
| Expand Subnet CIDR | yes | `gcloud compute networks subnets expand-ip-range` |
| Set Private Google Access | yes | `gcloud compute networks subnets update --private-ip-google-access` |
| Enable/Disable Flow Logs | yes | `gcloud compute networks subnets update --enable-flow-logs` |
| Create Firewall Rule | yes | `gcloud compute firewall-rules create` |
| Describe Firewall Rule | yes | `gcloud compute firewall-rules describe` |
| Update Firewall Rule | yes | `gcloud compute firewall-rules update` |
| Delete Firewall Rule | yes | `gcloud compute firewall-rules delete` |
| List Firewall Rules | yes | `gcloud compute firewall-rules list` |
| Create Route | yes | `gcloud compute routes create` |
| Delete Route | yes | `gcloud compute routes delete` |
| List Routes | yes | `gcloud compute routes list` |
| Create VPN Gateway | yes | `gcloud compute vpn-gateways create` |
| Create VPN Tunnel | yes | `gcloud compute vpn-tunnels create` |
| Describe VPN Tunnel | yes | `gcloud compute vpn-tunnels describe` |
| Delete VPN Tunnel | yes | `gcloud compute vpn-tunnels delete` |
| Create Cloud NAT | yes | `gcloud compute routers nats create` |
| Update Cloud NAT | yes | `gcloud compute routers nats update` |
| Delete Cloud NAT | yes | `gcloud compute routers nats delete` |
| Create VPC Peering | yes | `gcloud compute networks peerings create` |
| List VPC Peerings | yes | `gcloud compute networks peerings list` |
| List Network Tags | yes | `gcloud compute network-tags` |
| Expand Subnet CIDR | no | SDK-only: `subnetworks.expandIpCidrRange` |
| Patch Subnet (complex) | partial | SDK recommended for complex updates |

## Command Map

| Goal | Example `gcloud` invocation |
|------|---------------------------|
| List Networks | `gcloud compute networks list --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` |
| Create Network (custom) | `gcloud compute networks create "my-network" --project={{env.CLOUDSDK_CORE_PROJECT}} --subnet-mode=custom --bgp-routing-mode=global --format=json` |
| Describe Network | `gcloud compute networks describe "my-network" --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` |
| Delete Network | `gcloud compute networks delete "my-network" --project={{env.CLOUDSDK_CORE_PROJECT}} --quiet` |
| Create Subnet | `gcloud compute networks subnets create "my-subnet" --project={{env.CLOUDSDK_CORE_PROJECT}} --network="my-network" --region=us-central1 --range=10.0.1.0/24 --format=json` |
| List Subnets | `gcloud compute networks subnets list --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` |
| Describe Subnet | `gcloud compute networks subnets describe "my-subnet" --region=us-central1 --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` |
| Delete Subnet | `gcloud compute networks subnets delete "my-subnet" --region=us-central1 --project={{env.CLOUDSDK_CORE_PROJECT}} --quiet` |
| List Firewall Rules | `gcloud compute firewall-rules list --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` |
| Create Firewall Rule | `gcloud compute firewall-rules create "allow-ssh" --project={{env.CLOUDSDK_CORE_PROJECT}} --network="my-network" --allow=tcp:22 --source-ranges=0.0.0.0/0 --format=json` |
| Describe Firewall Rule | `gcloud compute firewall-rules describe "allow-ssh" --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` |
| Delete Firewall Rule | `gcloud compute firewall-rules delete "allow-ssh" --project={{env.CLOUDSDK_CORE_PROJECT}} --quiet` |
| List Routes | `gcloud compute routes list --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` |
| Describe Route | `gcloud compute routes describe "default-route" --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` |
| Create VPN Gateway | `gcloud compute vpn-gateways create "my-gw" --project={{env.CLOUDSDK_CORE_PROJECT}} --region=us-central1 --network="my-network" --format=json` |
| Create VPN Tunnel | `gcloud compute vpn-tunnels create "my-tunnel" --project={{env.CLOUDSDK_CORE_PROJECT}} --region=us-central1 --vpn-gateway="my-gw" --peer-address=203.0.113.1 --shared-secret=SECRET --ike-version=2 --router="my-router" --format=json` |
| Create Cloud NAT | `gcloud compute routers nats create "my-nat" --project={{env.CLOUDSDK_CORE_PROJECT}} --region=us-central1 --router="my-router" --nat-all-subnet-ip-ranges --auto-allocate-nat-external-ips --format=json` |
| Create VPC Peering | `gcloud compute networks peerings create "my-peering" --project={{env.CLOUDSDK_CORE_PROJECT}} --network="my-network" --peer-project=other-project --peer-network="other-network" --export-custom-routes --import-custom-routes --format=json` |

## Operation Polling

For async operations (network/subnet create/delete, VPN gateway):

```bash
# After async operation returns operation ID
gcloud compute operations describe "operation-name" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{status, targetLink}'

# Wait loop
for i in $(seq 1 60); do
  STATUS=$(gcloud compute operations describe "op-id" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --format="json" | jq -r '.status')
  [ "$STATUS" = "DONE" ] && break
  sleep 5
done
```