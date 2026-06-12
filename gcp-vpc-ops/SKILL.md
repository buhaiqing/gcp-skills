---
name: gcp-vpc-ops
description: >-
  Use when the user needs to create, configure, manage, or troubleshoot Google
  Cloud VPC — networks, subnets, firewall rules, routes, VPC peering, Cloud NAT,
  VPN tunnels, and Private Service Connect. User mentions VPC, network, subnet,
  firewall rule, route, peering, Cloud NAT, VPN, Private Google Access, or
  describes networking scenarios (e.g., "instances can't connect", "open a port",
  "set up VPN", "create a network") even without naming the product directly.
  Not for Cloud Load Balancing, Cloud DNS, or CDN that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Compute Network
  Admin IAM role, network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.1.0"
  last_updated: "2026-06-12"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://compute.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: "gcloud compute --help confirms subcommands: networks, networks subnets, firewall-rules, routes, network-endpoint-groups, vpn-tunnels, target-vpn-gateways, routers. See https://cloud.google.com/sdk/gcloud/reference/compute"
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud VPC Operations Skill

## Overview

Google Cloud Virtual Private Cloud (VPC) provides networking for cloud resources — networks, subnets, firewall rules, routes, VPN, Cloud NAT, and VPC peering. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` supports VPC operations via `gcloud compute networks`, `gcloud compute firewall-rules`, etc. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step. Coverage gaps (SDK-only operations) are listed in `references/gcloud-usage.md`.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (VPC) with clear delegation to related networking skills (LB, DNS, CDN) |

Refer to the [meta-skill](../gcp-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions of each standard.

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | Firewall rules, IAP, VPC Service Controls, Private Google Access, firewall insights | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Multi-region network design, VPN HA, peering redundancy, connectivity testing | `references/well-architected-assessment.md` §2.2 |
| **Cost** | VPC pricing (no charge for networks/subnets), VPN tunnel costs, NAT gateway pricing | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Shared VPC, network tags, hierarchical firewall, automated subnet creation | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Subnet CIDR planning, MTU, network throughput, latency optimization | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "VPC", "network", "subnet", "subnetwork", "firewall rule", "route", "VPN", "Cloud NAT", "peering", "Private Service Connect"
- Task involves creating, describing, modifying, or deleting VPC networks and subnets
- Task involves managing firewall rules (ingress/egress, allow/deny, tag-based, service-account-based)
- Task involves VPC peering, Cloud NAT configuration, VPN tunnels (HA VPN or classic)
- Task involves Private Google Access, Private Service Connect, VPC Flow Logs
- User describes connectivity issues (instances can't reach each other, can't reach internet, can't reach on-prem)

### SHOULD NOT Use This Skill When

- Task is purely about Cloud Load Balancing (global/L7, regional, internal) → delegate to: `gcp-lb-ops`
- Task is purely about Cloud DNS (zones, records, policies) → delegate to: `gcp-dns-ops`
- Task is purely about Cloud CDN → delegate to: `gcp-cdn-ops`
- Task is purely about instance-level firewall (OS-level iptables/nftables) → delegate to: `gcp-gce-ops`
- Task is purely about IAM / permissions → delegate to: `gcp-iam-ops`
- Task is purely about billing / cost → delegate to: `gcp-billing-ops`

### Delegation Rules

| Resource | Delegated Skill | Flow |
|----------|----------------|------|
| VM network interface | `gcp-gce-ops` | VPC creates network → GCE attaches instance to subnet |
| Internal Load Balancer | `gcp-lb-ops` | VPC subnet exists → LB uses subnet for backend |
| Private DNS zone | `gcp-dns-ops` | VPC network created → DNS associates with network |
| GKE cluster network | `gcp-gke-ops` | VPC network/subnet created → GKE uses it for cluster |
| Cloud SQL private IP | `gcp-cloudsql-ops` | VPC subnet exists → Cloud SQL uses Private Services Access |

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.region}}` | User-supplied region | Ask once; reuse |
| `{{user.network_name}}` | VPC network name | Ask once; reuse |
| `{{user.subnet_name}}` | Subnet name | Ask once; reuse |
| `{{user.subnet_cidr}}` | Subnet CIDR range (e.g., 10.0.0.0/24) | Ask once; reuse |
| `{{user.firewall_rule_name}}` | Firewall rule name | Ask once; reuse |
| `{{user.route_name}}` | Route name | Ask once; reuse |
| `{{user.vpn_tunnel_name}}` | VPN tunnel name | Ask once; reuse |
| `{{user.nat_gateway_name}}` | Cloud NAT gateway name | Ask once; reuse |
| `{{user.peering_name}}` | VPC peering name | Ask once; reuse |
| `{{output.network_self_link}}` | Created network self-link | Parse from API response |
| `{{output.subnet_self_link}}` | Created subnet self-link | Parse from API response |
| `{{output.firewall_self_link}}` | Created firewall rule self-link | Parse from API response |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** NEVER log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value.

| Context | What to Mask | Masking Method |
|---------|-------------|----------------|
| Console output | SA key content, access tokens, shared secrets | Replace with `****` |
| Error messages | Credential paths, token values | Log existence only, not value |
| Log files | All `GOOGLE_APPLICATION_CREDENTIALS` values | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA key file exists"` |
| Verification | Token/credential values | Check existence: `gcloud auth print-access-token --quiet &>/dev/null && echo "✅ Auth OK"` |
| JIT Go SDK | `config` structs, `fmt.Println(config)` | Prohibit such output — can leak credentials |
| Debug/verbose | Full API responses with auth headers | Strip `Authorization: Bearer ...` before logging |

## API and Response Conventions (Agent-Readable)

- **REST API is canonical:** `https://compute.googleapis.com/compute/v1/`
- **Resources are scoped:** Global (networks, firewall-rules, routes) or Regional (subnets, routers) or Zonal
- **Operations are async:** Create/Delete return an Operation ID; poll via `gcloud compute operations describe`
- **Pagination:** `pageToken` in request, `nextPageToken` in response
- **Firewall direction:** `INGRESS` (inbound) or `EGRESS` (outbound); default action `ALLOW` or `DENY`

### Common JSON Paths

```json
// ── VPC Network ──
// $.id                   -> network numeric ID
// $.name                 -> network name
// $.selfLink             -> full resource URL
// $.autoCreateSubnetworks -> true (auto-mode) / false (custom-mode)
// $.routingConfig.routingMode -> REGIONAL / GLOBAL
//
// ── Subnet ──
// $.id                   -> subnet numeric ID
// $.name                 -> subnet name
// $.ipCidrRange          -> CIDR range (e.g., 10.0.1.0/24)
// $.region               -> region URL
// $.network              -> parent network selfLink
// $.gatewayAddress       -> subnet gateway
// $.privateIpGoogleAccess -> true/false
// $.enableFlowLogs       -> true/false
// $.logConfig            -> flow log config
//
// ── Firewall Rule ──
// $.name                 -> rule name
// $.network              -> target network selfLink
// $.direction            -> INGRESS / EGRESS
// $.priority             -> 0-65535 (lower = higher priority)
// $.sourceRanges[]       -> source CIDRs (ingress)
// $.destinationRanges[]  -> dest CIDRs (egress)
// $.allowed[].IPProtocol  -> tcp, udp, icmp, all, or protocol number
// $.allowed[].ports[]    -> port ranges
// $.denied[]             -> same structure as allowed
// $.targetTags[]         -> target network tags
// $.targetServiceAccounts[] -> target SA
//
// ── Route ──
// $.name                 -> route name
// $.network              -> target network selfLink
// $.destRange            -> destination CIDR
// $.nextHopGateway       -> "default-internet-gateway"
// $.nextHopInstance      -> instance URL
// $.nextHopIp            -> next hop IP
// $.priority             -> route priority
// $.tags[]               -> route tags
//
// ── VPN Tunnel ──
// $.name                 -> tunnel name
// $.targetVpnGateway     -> gateway URL
// $.peerIp               -> peer (on-prem) gateway IP
// $.ikeVersion           -> 1 or 2
// $.sharedSecret         -> pre-shared key (masked in output)
// $.status               -> ESTABLISHED / etc.
//
// ── Cloud NAT ──
// $.name                 -> NAT gateway name
// $.region               -> region
// $.router               -> Cloud Router URL
// $.natIpAllocateOption  -> AUTO_ONLY / MANUAL_ONLY
// $.sourceSubnetworkIpRangesToNat -> ALL_SUBNETWORKS_ALL_IP_RANGES / ...
```

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create Network | — | exists | 5s | 120s |
| Create Subnet | — | exists (READY) | 5s | 120s |
| Create Firewall Rule | — | exists (no async) | — | 30s |
| Delete Network | exists | absent | 5s | 300s |
| Delete Subnet | exists | absent | 5s | 300s |
| Delete Firewall Rule | exists | absent (no async) | — | 30s |
| Create VPN Tunnel | — | exists | 5s | 120s |
| Create NAT | — | exists | 5s | 120s |

## Quick Start

### What This Skill Does
This skill enables you to create and manage VPC networks, subnets, firewall rules, routes, VPN tunnels, Cloud NAT, and VPC peering on Google Cloud.

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`
- [ ] IAM role: `roles/compute.networkAdmin` or equivalent

### Verify Setup
```bash
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
gcloud compute networks list --format="json" | jq 'length' && echo "✅ Compute API reachable"
```

### Your First Command
```bash
# List all VPC networks in the project
gcloud compute networks list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Understand VPC architecture
- [Common Operations](#execution-flows) — Create networks, subnets, firewall rules
- [Troubleshooting](references/troubleshooting.md) — Fix connectivity issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Create/Describe/Delete VPC Network | VPC network lifecycle | Medium | **High** — delete removes all resources |
| Create/Describe/Delete Subnet | Subnet lifecycle | Medium | **High** — delete breaks VMs |
| Create/Describe/Update/Delete Firewall Rules | Firewall rule CRUD | Low | **Medium** — misconfig opens/closes access |
| List/Describe/Modify/Delete Routes | Route table management | Medium | **Medium** — route misconfig breaks connectivity |
| Create/Describe/Delete VPN Tunnel | VPN tunnel lifecycle | High | Low — managed connectivity |
| Create/Describe/Delete Cloud NAT | NAT gateway lifecycle | Medium | Low |
| Create/Describe/Delete VPC Peering | Network peering lifecycle | Medium | **Medium** — CIDR overlap risk |
| Enable/Disable VPC Flow Logs | Flow log management | Low | Low |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-06-12 | Added Describe/List operations, Delete Subnet safety gate, Smart Defaults, Python SDK fallback, credential masking table, See Also, self-healing install; removed duplicate Changelog |
| 1.0.0 | 2026-06-07 | Initial VPC skill with networks, subnets, firewall rules, routes, VPN, NAT, peering |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud and SDK/API) → Validate → Recover**. Do not skip phases.

### Pre-flight Checks (Common to all VPC operations)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI | `gcloud version` | Exit code 0 | Install gcloud (see Prerequisites) |
| Credentials | `gcloud auth print-access-token --quiet` | Non-empty token | HALT; authenticate SA |
| Project | `gcloud config get-value project` or env var | Set and valid | HALT; set `CLOUDSDK_CORE_PROJECT` |
| Compute API | `gcloud services list --enabled --filter="config:compute.googleapis.com"` | enabled | HALT; run `gcloud services enable compute.googleapis.com` |
| IAM role | `gcloud projects get-iam-policy "{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq '.bindings[] | select(.role=="roles/compute.networkAdmin")'` | Has role | Warn user; may fail on operations |

### Operation: Describe / List VPC Networks

**List all networks:**
```bash
gcloud compute networks list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Describe a specific network:**
```bash
gcloud compute networks describe "{{user.network_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, selfLink, autoCreateSubnetworks, routingConfig, subnetworks}'
```

### Operation: Create VPC Network

#### Smart Defaults

| Parameter | Default | When to Override |
|-----------|---------|------------------|
| `--subnet-mode` | `custom` | Use `auto` only for prototyping/simple projects |
| `--bgp-routing-mode` | `regional` | Use `global` for multi-region VPC peering |
| `--mtu` | `1460` | Use `8896` for jumbo frames (compatibility required) |

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Network name uniqueness | `gcloud compute networks describe "{{user.network_name}}" --format="json"` | NOT_FOUND | HALT; name already exists |
| CIDR plan (custom-mode) | User provides subnet CIDR ranges | Non-overlapping valid CIDR | HALT; correct before proceeding |

#### Execution — CLI (`gcloud`)

**Create auto-mode VPC network:**
```bash
gcloud compute networks create "{{user.network_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --subnet-mode=auto \
  --bgp-routing-mode=regional \
  --format="json"
```

**Create custom-mode VPC network:**
```bash
gcloud compute networks create "{{user.network_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --subnet-mode=custom \
  --bgp-routing-mode=global \
  --format="json"
```

#### Execution — Python SDK (Primary Fallback)

Full script at [references/api-sdk-usage.md](references/api-sdk-usage.md)

```python
# create_network.py — run: python3 create_network.py
from google.cloud import compute_v1
from google.cloud.compute_v1 import types

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = compute_v1.NetworksClient()

network = compute_v1.Network()
network.name = "{{user.network_name}}"
network.auto_create_subnetworks = False  # custom-mode
network.routing_config = compute_v1.NetworkRoutingConfig()
network.routing_config.routing_mode = "GLOBAL"

op = client.insert(project=project, network_resource=network)
# Wait for async operation
op.result()  # blocks until done
# $.selfLink -> network self-link
```

#### Execution — JIT Go SDK (Secondary Fallback)

```go
// create_network.go
package main

import (
	"context"
	"fmt"
	"os"

	compute "cloud.google.com/go/compute/apiv1"
	"cloud.google.com/go/compute/apiv1/computepb"
	"google.golang.org/api/option"
	"google.golang.org/protobuf/proto"
)

func main() {
	ctx := context.Background()
	client, err := compute.NewNetworksRESTClient(ctx,
		option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
	if err != nil {
		panic(err)
	}
	defer client.Close()

	project := os.Getenv("CLOUDSDK_CORE_PROJECT")
	req := &computepb.InsertNetworkRequest{
		Project: project,
		NetworkResource: &computepb.Network{
			Name:                  proto.String("{{user.network_name}}"),
			AutoCreateSubnetworks: proto.Bool(false), // custom-mode
			RoutingConfig: &computepb.NetworkRoutingConfig{
				RoutingMode: proto.String("GLOBAL"),
			},
		},
	}
	op, err := client.Insert(ctx, req)
	if err != nil {
		panic(err)
	}
	// Wait for operation
	if err := op.Wait(ctx); err != nil {
		panic(err)
	}
	// $.selfLink -> network self-link
	fmt.Printf("Created: %s\n", op.Proto().GetTargetLink())
}
```

#### Post-execution Validation

```bash
gcloud compute networks describe "{{user.network_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, selfLink, subnetMode, routingConfig}'
```

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|---------------|-------------|--------------|-------------|
| `ALREADY_EXISTS` / 409 | 0 | HALT | `[ERROR] ALREADY_EXISTS: Network "{{user.network_name}}" already exists. Use a different name.` |
| `INVALID_ARGUMENT` / 400 | 0 | HALT | `[ERROR] INVALID_ARGUMENT: Invalid network configuration. Check subnet-mode and routing-mode values.` |
| `QUOTA_EXCEEDED` / 429 | 0 | HALT | `[ERROR] QUOTA_EXCEEDED: VPC network quota reached. Delete unused networks or request increase.` |
| `PERMISSION_DENIED` / 403 | 0 | HALT | `[ERROR] PERMISSION_DENIED: Missing compute.networks.create permission.` |
| `INTERNAL` / 500 | 3 (2s, 4s, 8s) | Retry; then HALT | `[ERROR] INTERNAL: Server error. Retry or create support case.` |

### Operation: Delete VPC Network (Safety Gate: HIGH)

> **WARNING:** Deleting a VPC network is irreversible and will fail if any resources still exist (subnets, VMs, firewall rules, routes, etc.).

#### Pre-flight (Safety Gate) — MANDATORY

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Dependent resources | `gcloud compute instances list --filter="networkInterfaces[].network:{{user.network_name}}" --format="json"` | Empty list | HALT — cannot delete network with running VMs |
| Firewall rules | `gcloud compute firewall-rules list --filter="network:{{user.network_name}}" --format="json"` | Empty list | HALT — delete firewall rules first |
| Subnets | `gcloud compute networks subnets list --network="{{user.network_name}}" --format="json"` | Empty list | HALT — delete subnets first |
| Routes | `gcloud compute routes list --filter="network:{{user.network_name}}" --format="json"` | Only default routes | Warn user; default routes auto-deleted |
| **User confirmation** | User must type the exact network name | Exact match | HALT — confirmation required |

```text
🔴 WARNING: This will irreversibly DELETE VPC network "my-vpc-network".

Prerequisites that MUST be resolved before deletion:
  - All running VMs attached to this network must be deleted
  - All subnets, firewall rules, routes (non-default) must be deleted
  - All VPN tunnels and VPC peering must be removed

To proceed, type the network name: _______________
```

#### Execution — CLI (`gcloud`)

```bash
gcloud compute networks delete "{{user.network_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet
```

#### Post-execution Validation

```bash
# Verify network no longer exists
gcloud compute networks describe "{{user.network_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" 2>&1 || echo "✅ Network deleted successfully"
```

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|---------------|-------------|--------------|-------------|
| `IN_USE_BY_RESOURCE` / 400 | 0 | HALT | `[ERROR] Network is in use. Delete all dependent resources first. Check: VMs, subnets, firewall rules, routes, VPN tunnels, peering.` |
| `NOT_FOUND` / 404 | 0 | Report success | Network already deleted. |
| `PERMISSION_DENIED` / 403 | 0 | HALT | `[ERROR] PERMISSION_DENIED: Missing compute.networks.delete permission.` |

### Operation: Delete Subnet (Safety Gate)

> **WARNING:** Deleting a subnet will disconnect all VMs and resources using it.

#### Pre-flight (Safety Gate) — MANDATORY

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| No VMs using subnet | `gcloud compute instances list --filter="networkInterfaces[].subnetwork:{{user.subnet_name}}" --format="json"` | Empty list | HALT — delete or migrate VMs first |
| No GKE secondary ranges | `gcloud compute networks subnets describe "{{user.subnet_name}}" --region="{{user.region}}" --format="json" | jq '.secondaryIpRanges'` | Empty or user-acknowledged | Warn user; GKE cluster may be affected |
| **User confirmation** | User must type the exact subnet name + region | Exact match | HALT — confirmation required |

```text
🔴 WARNING: This will irreversibly DELETE subnet "{{user.subnet_name}}" in region {{user.region}}.
All VMs and resources using this subnet will lose connectivity.

To proceed, type the subnet name: _______________
```

#### Execution — CLI (`gcloud`)

```bash
gcloud compute networks subnets delete "{{user.subnet_name}}" \
  --region="{{user.region}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet
```

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|---------------|-------------|--------------|-------------|
| `RESOURCE_IN_USE` / 400 | 0 | HALT | `[ERROR] Subnet is in use by VMs. Delete or migrate VMs first.` |
| `NOT_FOUND` / 404 | 0 | Report success | Subnet already deleted. |
| `PERMISSION_DENIED` / 403 | 0 | HALT | `[ERROR] PERMISSION_DENIED: Missing compute.subnetworks.delete permission.` |

### Operation: Describe / List Subnets

**List all subnets in a network:**
```bash
gcloud compute networks subnets list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --network="{{user.network_name}}" \
  --format="json"
```

**Describe a specific subnet:**
```bash
gcloud compute networks subnets describe "{{user.subnet_name}}" \
  --region="{{user.region}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, ipCidrRange, gatewayAddress, network, privateIpGoogleAccess, enableFlowLogs}'
```

### Operation: Create Subnet

#### Smart Defaults

| Parameter | Default | When to Override |
|-----------|---------|------------------|
| `--range` | — (required) | Always specify; use /24 for small, /20 for large subnets |
| `--private-ip-google-access` | enabled | Disable only for isolated networks |
| `--enable-flow-logs` | enabled | Disable for cost savings on non-critical subnets |
| `--flow-sampling` | `0.5` | Use `1.0` for security-critical, `0.1` for cost savings |

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Parent network exists | `gcloud compute networks describe "{{user.network_name}}"` | exists | HALT; create network first |
| CIDR overlap | Check existing subnets in region | Non-overlapping | HALT; choose non-conflicting CIDR |
| Subnet name uniqueness | `gcloud compute networks subnets describe "{{user.subnet_name}}" --region="{{user.region}}"` | NOT_FOUND | HALT; name already exists |

#### Execution — CLI (`gcloud`)

```bash
gcloud compute networks subnets create "{{user.subnet_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --network="{{user.network_name}}" \
  --region="{{user.region}}" \
  --range="{{user.subnet_cidr}}" \
  --private-ip-google-access \
  --enable-flow-logs \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud compute networks subnets describe "{{user.subnet_name}}" \
  --region="{{user.region}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, ipCidrRange, gatewayAddress, privateIpGoogleAccess, enableFlowLogs}'
```

### Operation: Create Firewall Rule

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Target network exists | `gcloud compute networks describe "{{user.network_name}}"` | exists | HALT; create network first |
| Rule name uniqueness | `gcloud compute firewall-rules describe "{{user.firewall_rule_name}}"` | NOT_FOUND | HALT; name already exists |
| Rule validation | Check priority (0-65535), source CIDR validity | Valid | HALT; fix invalid params |

#### Execution — CLI (`gcloud`)

```bash
# Allow SSH (port 22) from specific CIDR
gcloud compute firewall-rules create "{{user.firewall_rule_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --network="{{user.network_name}}" \
  --direction=INGRESS \
  --priority=1000 \
  --source-ranges="{{user.source_cidr}}" \
  --target-tags=ssh-allowed \
  --allow=tcp:22 \
  --format="json"
```

**More examples:**
```bash
# Allow HTTP/HTTPS from anywhere
gcloud compute firewall-rules create "allow-web" \
  --network="default" \
  --direction=INGRESS \
  --priority=1000 \
  --source-ranges=0.0.0.0/0 \
  --allow=tcp:80,tcp:443

# Deny all egress to specific CIDR
gcloud compute firewall-rules create "deny-malicious-egress" \
  --network="default" \
  --direction=EGRESS \
  --priority=100 \
  --destination-ranges="203.0.113.0/24" \
  --action=DENY \
  --rules=all
```

#### Post-execution Validation

```bash
gcloud compute firewall-rules describe "{{user.firewall_rule_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, network, direction, priority, sourceRanges, allowed}'
```

### Operation: Update Firewall Rule

```bash
gcloud compute firewall-rules update "{{user.firewall_rule_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --source-ranges="{{user.source_cidr}}" \
  --format="json"
```

### Operation: Delete Firewall Rule (Safety Gate)

#### Pre-flight (Safety Gate)
```text
🔴 WARNING: This will permanently delete firewall rule "{{user.firewall_rule_name}}".
This rule controls {{user.direction}} traffic on network {{user.network_name}}.
Deleting it may open or close access to resources.

To proceed, type the rule name: _______________
```

#### Execution — CLI (`gcloud`)

```bash
gcloud compute firewall-rules delete "{{user.firewall_rule_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet
```

### Operation: List / Describe Routes

**List routes:**
```bash
gcloud compute routes list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Filter by network:**
```bash
gcloud compute routes list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="network:{{user.network_name}}" \
  --format="json"
```

**Describe route:**
```bash
gcloud compute routes describe "{{user.route_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Operation: Create VPN Tunnel (HA VPN)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cloud Router exists | `gcloud compute routers list --region="{{user.region}}"` | Router exists | Create router first |
| Peer gateway IP | User-provided | Reachable IP | HALT; verify peer IP |
| IKE version | Compatibility check | Same version both sides | HALT; align IKE version |

#### Execution — CLI (`gcloud`)

```bash
# Create VPN gateway
gcloud compute vpn-gateways create "{{user.vpn_name}}-gw" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --network="{{user.network_name}}" \
  --format="json"

# Create VPN tunnel
# SECURITY: Generate a random shared-secret instead of taking user input.
# The secret is visible in process listing (`ps aux`) — mitigate by using
# `gcloud` native input or rotating immediately after creation.
SHARED_SECRET=$(openssl rand -base64 24)
gcloud compute vpn-tunnels create "{{user.vpn_tunnel_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --vpn-gateway="{{user.vpn_name}}-gw" \
  --peer-address="{{user.peer_ip}}" \
  --shared-secret="${SHARED_SECRET}" \
  --ike-version=2 \
  --router="{{user.router_name}}" \
  --format="json"
echo "Shared secret (save this): ${SHARED_SECRET}"
```

### Operation: Create Cloud NAT

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cloud Router exists | `gcloud compute routers list --region="{{user.region}}"` | Router exists | HALT; create router first |

#### Execution — CLI (`gcloud`)

```bash
gcloud compute routers nats create "{{user.nat_gateway_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --router="{{user.router_name}}" \
  --nat-all-subnet-ip-ranges \
  --auto-allocate-nat-external-ips \
  --format="json"
```

### Operation: Create VPC Peering

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CIDR overlap | Compare peering network subnets | No overlap | HALT; overlapping CIDRs will fail |
| IAM permission | SA has `compute.networks.updatePeering` | Has permission | HALT; grant permission |
| Peering limit | `gcloud compute networks list` peer count | < 25 peering limit | HALT; delete old peers |

#### Execution — CLI (`gcloud`)

```bash
gcloud compute networks peerings create "{{user.peering_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --network="{{user.network_name}}" \
  --peer-project="{{user.peer_project}}" \
  --peer-network="{{user.peer_network}}" \
  --export-custom-routes \
  --import-custom-routes \
  --format="json"
```

## Prerequisites

1. **Install gcloud CLI:**
   ```bash
   # Self-healing: probe first, install only if missing
   if ! command -v gcloud &>/dev/null; then
     curl https://sdk.cloud.google.com | bash
     exec -l $SHELL
   fi
   gcloud init
   ```

2. **Bootstrap Go runtime** (JIT fallback):
   ```bash
   if ! command -v go &> /dev/null; then
       OS=$(uname -s | tr '[:upper:]' '[:lower:]')
       ARCH=$(uname -m)
       [ "$ARCH" = "x86_64" ] && ARCH="amd64"
       [ "$ARCH" = "aarch64" ] && ARCH="arm64"
       mkdir -p /tmp/go-runtime
       curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
       export PATH="/tmp/go-runtime/go/bin:$PATH"
   fi
   go version
   ```

3. **Configure Credentials:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
   export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
   gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
   gcloud config set project "$CLOUDSDK_CORE_PROJECT"
   ```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [gcloud Usage](references/gcloud-usage.md)
- [Troubleshooting Guide](references/troubleshooting.md)
- [Monitoring & Alerts](references/monitoring.md)
- [Integration](references/integration.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Idempotency Checklist](references/idempotency-checklist.md)
- [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md)
- [Execution Environment Setup](../gcp-skill-generator/references/execution-environment.md)
- [Enhanced Self-Healing Framework](../gcp-skill-generator/references/enhanced-self-healing-framework.md)
- [CLI Behavioral Reference](../gcp-skill-generator/references/cli-behavior.md)

## Operational Best Practices

- **Hierarchical firewall:** Use hierarchical firewall policies (at folder/organization level) for consistent rules across projects
- **Shared VPC:** Use Shared VPC for multi-project isolation with centralized network administration
- **Subnet CIDR planning:** Allocate /16 for network, /20-24 per subnet; leave room for expansion
- **VPC Flow Logs:** Enable for critical subnets; sample rate 1:1 for security, 1:10 for cost savings
- **Private Google Access:** Enable on subnets for VM-to-Google-API traffic without external IP
- **Cloud NAT:** Use Cloud NAT for private VM internet access; avoid public IPs on VMs when possible
- **Peering:** Never peer networks with overlapping CIDRs; use export/import custom routes selectively

## Quality Gate (GCL)

This skill uses the **Generator-Critic-Loop (GCL)** adversarial quality gate.

| Dimension | Classification | Default `max_iter` | Most-scrutinized ops |
|-----------|---------------|:------------------:|----------------------|
| Cloud VPC | `required` | 2 | Delete Network, Delete Subnet, Delete Firewall Rule, Modify Firewall Rule (broadening access) |

**Rubric:** See [references/rubric.md](references/rubric.md)
**Prompt templates:** See [references/prompt-templates.md](references/prompt-templates.md)

## Token Efficiency Guidelines (P0 — 强制)

### TE-1: API Query > Static Tables
Use `gcloud compute machine-types list`, `gcloud compute regions describe` to fetch runtime data instead of hardcoding.

### TE-2: No docstrings in code
Inline `#` comments only. No function-level docstrings.

### TE-3: Compact error tables
See [troubleshooting.md](references/troubleshooting.md) for compact error table format.

### TE-4: Centralized JSON paths
JSON paths are declared at the top of this file under [Common JSON Paths](#common-json-paths).

### TE-5: YAML anchors in example-config.yaml
See [assets/example-config.yaml](assets/example-config.yaml) for YAML anchor patterns.

### TE-6: Eliminate cross-file duplicate flows
SKILL.md has full execution flows; references do not repeat them.

## See Also

| Skill | Relationship |
|-------|-------------|
| [gcp-gce-ops](../gcp-gce-ops/SKILL.md) | VM network interface attachment |
| [gcp-gke-ops](../gcp-gke-ops/SKILL.md) | GKE cluster networking |
| [gcp-cloudsql-ops](../gcp-cloudsql-ops/SKILL.md) | Cloud SQL private IP / Private Services Access |
| [gcp-lb-ops](../gcp-lb-ops/SKILL.md) | Internal/external load balancer subnet usage |
| [gcp-dns-ops](../gcp-dns-ops/SKILL.md) | Private DNS zone association with VPC |
| [gcp-iam-ops](../gcp-iam-ops/SKILL.md) | IAM roles for VPC operations |