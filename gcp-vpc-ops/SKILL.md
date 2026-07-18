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
  version: "1.2.0"
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
| 1.2.0 | 2026-06-12 | Added Create/Delete Route, Describe/List/Delete VPN Tunnels, Delete Cloud NAT, Delete VPC Peering; advanced docs (Shared VPC, Private Service Connect, AIOps, FinOps) |
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

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute networks list` | List all networks in project |
| 2 | `gcloud compute networks describe` | Describe `{{user.network_name}}`; extract `name, selfLink, autoCreateSubnetworks, routingConfig, subnetworks` |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

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

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute networks create` | Create network with `--subnet-mode` (auto/custom) + `--bgp-routing-mode` (regional/global) |
| 2 | Python SDK fallback | `compute_v1.NetworksClient().insert(...)` — full script at [assets/code-snippets/create_network.py](assets/code-snippets/create_network.py) |
| 3 | Go SDK fallback | `compute.NewNetworksRESTClient().Insert(...)` — full script at [assets/code-snippets/create_network.go](assets/code-snippets/create_network.go) |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

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

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute networks delete` | Delete `{{user.network_name}}` with `--quiet` (only after Safety Gate passes) |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

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

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute networks subnets delete` | Delete `{{user.subnet_name}}` in `{{user.region}}` with `--quiet` (only after Safety Gate passes) |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|---------------|-------------|--------------|-------------|
| `RESOURCE_IN_USE` / 400 | 0 | HALT | `[ERROR] Subnet is in use by VMs. Delete or migrate VMs first.` |
| `NOT_FOUND` / 404 | 0 | Report success | Subnet already deleted. |
| `PERMISSION_DENIED` / 403 | 0 | HALT | `[ERROR] PERMISSION_DENIED: Missing compute.subnetworks.delete permission.` |

### Operation: Describe / List Subnets

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute networks subnets list` | List subnets in `{{user.network_name}}` |
| 2 | `gcloud compute networks subnets describe` | Describe `{{user.subnet_name}}`; extract `name, ipCidrRange, gatewayAddress, network, privateIpGoogleAccess, enableFlowLogs` |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

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

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute networks subnets create` | Create `{{user.subnet_name}}` in `{{user.region}}` with `--range={{user.subnet_cidr}}`, `--private-ip-google-access`, `--enable-flow-logs` |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

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

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute firewall-rules create` | Create `{{user.firewall_rule_name}}` with `--direction` (INGRESS/EGRESS), `--priority`, `--source-ranges`/`--destination-ranges`, `--allow`/`--action` |
| 2 | Common variants | Allow web: `--allow=tcp:80,tcp:443 --source-ranges=0.0.0.0/0`; Deny egress: `--direction=EGRESS --action=DENY --rules=all` |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

#### Post-execution Validation

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute firewall-rules describe` | Extract `name, network, direction, priority, sourceRanges, allowed` |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

### Operation: Update Firewall Rule

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute firewall-rules update` | Update `{{user.firewall_rule_name}}` (e.g. `--source-ranges={{user.source_cidr}}`) |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

### Operation: Delete Firewall Rule (Safety Gate)

#### Pre-flight (Safety Gate)
```text
🔴 WARNING: This will permanently delete firewall rule "{{user.firewall_rule_name}}".
This rule controls {{user.direction}} traffic on network {{user.network_name}}.
Deleting it may open or close access to resources.

To proceed, type the rule name: _______________
```

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute firewall-rules delete` | Delete `{{user.firewall_rule_name}}` with `--quiet` (only after Safety Gate passes) |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

### Operation: List / Describe Routes

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute routes list` | List all routes; add `--filter="network:{{user.network_name}}"` to scope |
| 2 | `gcloud compute routes describe` | Describe `{{user.route_name}}` |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

**JSON response structure:**
```json
{
  "name": "route-name",
  "network": "https://www.googleapis.com/compute/v1/projects/PROJECT_ID/global/networks/network-name",
  "destRange": "10.0.0.0/24",
  "nextHopGateway": "default-internet-gateway",
  "nextHopVpnTunnel": "vpn-tunnel-link",
  "nextHopInstance": "https://www.googleapis.com/compute/v1/projects/PROJECT_ID/zones/ZONE/instances/instance-name",
  "nextHopIp": "10.1.0.2",
  "priority": 1000,
  "tags": ["tag-name"],
  "nextHopNetwork": "network-link"
}
```

### Operation: Create Route

#### Smart Defaults

| Parameter | Default | When to Override |
|-----------|---------|------------------|
| `--priority` | 1000 | Higher priority (lower number) wins |
| `--next-hop-gateway` | none | Use `--next-hop-instance` for VM, `--next-hop-vpn-tunnel` for VPN |
| `--destination-range` | `0.0.0.0/0` | Specific CIDR for more granular routing |

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Next hop validity | `gcloud compute instances describe {{user.instance_name}} --format=json` | Not ERROR | HALT; instance doesn't exist |
| destination-range | User provides valid CIDR (e.g., `10.0.0.0/24`) | CIDR notation | HALT; invalid CIDR |
| Destination CIDR overlap | Check with existing subnets | No overlap with local subnet | WARING; potential routing issues |
| Admin role check | `gcloud projects get-iam-policy` | Has role | HALT; insufficient permissions |

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute routes create` (default gateway) | `--next-hop-gateway=default-internet-gateway` |
| 2 | `gcloud compute routes create` (to VM) | `--next-hop-instance={{user.zone}}/{{user.instance_name}} --tags={{user.tags \| default('routes')}}` |
| 3 | `gcloud compute routes create` (to VPN) | `--next-hop-vpn-tunnel={{user.vpn_tunnel_name}} --tags={{user.tags \| default('routes')}}` |
| 4 | `gcloud compute routes create` (to IP) | `--next-hop-ip={{user.next_hop_ip}}` |
| 5 | Python SDK fallback | `compute_v1.RoutesClient().insert(...)` — full script at [assets/code-snippets/create_route.py](assets/code-snippets/create_route.py) |

All variants use `--network {{user.network_name}} --destination-range={{user.destination_range}} --priority={{user.priority | default(1000)}}`. Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

#### Post-execution Validation

| Step | Command | Expected | On Failure |
|------|---------|----------|------------|
| Verify route exists | `gcloud compute routes describe {{user.route_name}} --format=json` | Route details returned | HALT; route not created |
| Check route destination | `jq '{name, destination_range, next_hop}'` | Matches request | HALT; mismatch |
| Verify route in network | `gcloud compute routes list --filter="network:{{user.network_name}} --format=json"` | Route in list | HALT; not bound to network |

#### Failure Recovery

| Error | Fix |
|-------|-----|
| `400 Bad Request - Invalid CIDR range` | Validate `--destination-range` format (e.g., `10.0.0.0/24`) |
| `400 Bad Request - Destination CIDR overlaps with subnet` | Remove or update conflicting subnet; verify CIDR not used by existing subnets |
| `400 Bad Request - Next hop not found` | Check VM instance exists: `gcloud compute instances describe {{user.instance_name}}` |
| `403 Forbidden` | Verify IAM role `roles/compute.networkAdmin` exists |
| `409 Conflict - Route already exists` | Use different `--name` or delete existing route first |

### Operation: Delete Route

#### Safety Gate: HIGH

> **⛔ DELETE DANGER:** Deleting a route can break network connectivity. Routes may be auto-created by Google Cloud (e.g., default routes from internet gateways, subnets, routers). **NEVER delete auto-created routes unless you understand the impact.**

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Route exists | `gcloud compute routes describe {{user.route_name}} --format=json` | Route details returned | HALT; route doesn't exist |
| Route is user-created | Check `tags` or validate route is not Google-created | No "Google-managed" label OR user-provided tags | WARN; confirm deletion intent |
| Verify no critical dependencies | Review route `nextHopGateway`, `nextHopInstance`, `nextHopVpnTunnel` | No VMs/VPN tunnels depend on this route | HALT; confirm no dependent resources |
| Confirmation | User provides route name again | User confirms deletion | HALT; no confirmation |

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute routes describe` | Confirm route exists; extract `name, destination_range, next_hop_*` |
| 2 | `gcloud compute routes delete` | Delete `{{user.route_name}}` with `--quiet` (only after Safety Gate passes) |
| 3 | Python SDK fallback | `route_client.get(...)` then `route_client.delete(...)` — full script at [assets/code-snippets/delete_route.py](assets/code-snippets/delete_route.py) |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

#### Post-execution Validation

| Step | Command | Expected | On Failure |
|------|---------|----------|------------|
| Verify deletion | `gcloud compute routes describe {{user.route_name}} --format=json` | Returns NOT_FOUND | HALT; deletion failed |
| Check pending operations | `gcloud compute operations list --filter="targetLink=~routes.*{{user.route_name}}" --format=json` | No pending operations | WARN; may still be deleting |

#### Failure Recovery

| Error | Fix |
|-------|-----|
| `404 Not Found - Route not found` | Route already deleted or wrong name |
| `400 Bad Request - Route is in use` | Verify no VMs/bound to this route; disable VMs or update VM network interfaces first |
| `403 Forbidden` | Verify IAM role `roles/compute.networkAdmin` |
| `400 Bad Request - Route cannot be deleted` | Route is a dependency for VM network interfaces; disassociate from VMs first |

### Operation: Describe / List VPN Tunnels

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute vpn-tunnels list` | List tunnels in `{{user.region}}`; add `--filter="vpnGateway:{{user.vpn_gateway_name}}"` to scope |
| 2 | `gcloud compute vpn-tunnels describe` | Describe `{{user.vpn_tunnel_name}}`; extract `name, selfLink, targetVpnGateway, peerIp, ikeVersion, sharedSecret (masked), status` |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

**JSON response structure:**
```json
{
  "name": "vpn-tunnel-name",
  "selfLink": "https://www.googleapis.com/compute/v1/projects/PROJECT_ID/regions/REGION/operationLink",
  "creationTimestamp": "2026-06-12T10:00:00Z",
  "targetVpnGateway": "https://www.googleapis.com/compute/v1/projects/PROJECT_ID/regions/REGION/targetVpnGateways/gateway-name",
  "peerIpAddress": "203.0.113.5",
  "sharedSecret": "YjslA9wZk89/3xL3mQ==",
  "ikeVersion": 2,
  "router": "https://www.googleapis.com/compute/v1/projects/PROJECT_ID/regions/REGION/routers/router-name",
  "status": "ESTABLISHED"
}
```

### Operation: Create VPN Tunnel

#### Safety Gate: MEDIUM

> **⚠️ VPN CAUTION:** VPN tunnels establish encrypted connections between GCP and on-premises or peer VPCs. Configuration must be consistent on both sides to avoid connectivity failures.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cloud Router exists | `gcloud compute routers list --region="{{user.region}}"` | Router exists | HALT; create router first |
| Peer gateway IP | User provides reachable IP | Valid IPv4 | HALT; verify IP format |
| IKE version compatibility | IKEv1 and IKEv2 must match on both sides | Same version | HALT; align with peer |
| IAM role | SA has `roles/compute.networkAdmin` | Has role | HALT; insufficient permissions |

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute vpn-gateways create` | Create `{{user.vpn_gateway_name}}` in `{{user.region}}` on `{{user.network_name}}` |
| 2 | `gcloud compute vpn-tunnels create` | Create `{{user.vpn_tunnel_name}}` with `--peer-address`, `--shared-secret`, `--ike-version={{user.ike_version \| default(2)}}`, `--router` |
| 3 | HA VPN (failover) | Create `{{user.vpn_tunnel_name}}-secondary` with `--peer-address={{user.peer_gateway_ip_secondary}}` |

> **SECURITY:** Generate the shared secret securely: `SHARED_SECRET=$(openssl rand -base64 24)`. Print and save it immediately — it cannot be recovered after creation. Never log the secret value.

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

#### Post-execution Validation

| Step | Command | Expected | On Failure |
|------|---------|----------|------------|
| Verify tunnel exists | `gcloud compute vpn-tunnels describe {{user.vpn_tunnel_name}}` | Tunnel details returned | HALT; not created |
| Check tunnel status | `jq '.status'` | `ESTABLISHED` or `INITIATED` | WARN; may take time |
| Verify shared secret | Compare saved secret with GCP output | Match | HALT; secret not saved |

#### Failure Recovery

| Error | Fix |
|-------|-----|
| `400 Bad Request - Peer IP unreachable` | Verify peer IP is reachable: `ping {{user.peer_gateway_ip}}` |
| `400 Bad Request - IKE version mismatch` | Ensure both sides use same IKE version (1 or 2) |
| `403 Forbidden` | Verify IAM role `roles/compute.networkAdmin` |
| `409 Conflict - Tunnel already exists` | Use different tunnel name or delete existing tunnel |

### Operation: Delete VPN Tunnel

#### Safety Gate: HIGH

> **⛔ DELETE DANGER:** Deleting a VPN tunnel helps connectivity, but peer side must also delete its tunnel to close the connection. This operation is not reversible.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Tunnel exists | `gcloud compute vpn-tunnels describe {{user.vpn_tunnel_name}} --region={{user.region}}` | Tunnel details returned | HALT; tunnel not found |
| No active traffic/users | Review tunnel status and operations | Not BUSY | WARN; verify connectivity OK |
| Peer configuration | Verify peer network has matching tunnel | Peer will also delete | Confirm peer action |
| Confirmation | User explicitly confirms | User confirms deletion | HALT; no confirmation |

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute vpn-tunnels describe` | Show `{{user.vpn_tunnel_name}}` details (`name, targetVpnGateway, peerIpAddress, status`) before deletion |
| 2 | Confirm | User must type `CONFIRM DELETE` to proceed |
| 3 | `gcloud compute vpn-tunnels delete` | Delete with `--quiet` (only after Safety Gate passes) |
| 4 | Python SDK fallback | `tunnel_client.get(...)` then `tunnel_client.delete(...)` — full script at [assets/code-snippets/delete_vpn_tunnel.py](assets/code-snippets/delete_vpn_tunnel.py) |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

#### Post-execution Validation

| Step | Command | Expected | On Failure |
|------|---------|----------|------------|
| Verify deletion | `gcloud compute vpn-tunnels describe {{user.vpn_tunnel_name}} --region={{user.region}}` | Returns NOT_FOUND | HALT; deletion failed |
| Check operations | `gcloud compute operations list --filter="targetLink=~vpn-tunnels.*{{user.vpn_tunnel_name}}"` | No pending deletion | WARN |

#### Failure Recovery

| Error | Fix |
|-------|-----|
| `404 Not Found - Tunnel not found` | Tunnel already deleted or wrong name/region |
| `400 Bad Request - Tunnel in use` | Disassociate from VMs/routers first |
| `403 Forbidden` | Verify IAM role `roles/compute.networkAdmin` |
| `400 Bad Request - Tunnel connection faulted` | Check network connectivity, routing, VPN gateway status |

### Operation: Create Cloud NAT

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cloud Router exists | `gcloud compute routers list --region="{{user.region}}"` | Router exists | HALT; create router first |

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute routers nats create` | Create `{{user.nat_gateway_name}}` with `--nat-all-subnet-ip-ranges --auto-allocate-nat-external-ips` |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

### Operation: Delete Cloud NAT

#### Safety Gate: MEDIUM

> **⚠️ NAT CAUTION:** Deleting Cloud NAT may break internet connectivity for VMs that rely on it. Verify no VMs need NAT before proceeding.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| NAT gateway exists | `gcloud compute routers nats list --region="{{user.region}}"` | NAT found | HALT; NAT doesn't exist |
| VM dependency check | Review NAT targets | No VMs actively using NAT or user confirms | WARN before deletion |
| Router existence | `gcloud compute routers describe {{user.router_name}}` | Router exists | HALT; router must exist |
| Confirmation | User confirms deletion intent | User confirms | HALT; no confirmation |

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute routers nats list` | Verify NAT gateways on `{{user.router_name}}` |
| 2 | `gcloud compute routers nats describe` | Show `{{user.nat_name}}` details (`name, natIpAllocateOption, sourceSubnetworkIpRangesToNat`) before deletion |
| 3 | `gcloud compute routers nats delete` | Delete with `--quiet` (async; monitor via `gcloud compute operations list`) |
| 4 | Python SDK fallback | `nats_client.list(...)` then `nats_client.delete(...)` — full script at [assets/code-snippets/delete_nat_gateway.py](assets/code-snippets/delete_nat_gateway.py) |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

#### Post-execution Validation

| Step | Command | Expected | On Failure |
|------|---------|----------|------------|
| Verify deletion | `gcloud compute routers nats describe {{user.nat_name}}` | Returns NOT_FOUND | HALT; deletion failed |
| Check pending operations | `gcloud compute operations list --filter="targetLink=~nats.*{{user.nat_name}}"` | No pending deletions | WARN; monitor progress |

#### Failure Recovery

| Error | Fix |
|-------|-----|
| `404 Not Found - NAT not found` | NAT already deleted or wrong name/region |
| `400 Bad Request - NAT is required for subnets` | Subnets have NAT: `gcloud compute routes list --filter="nextHopNat:"` |
| `403 Forbidden` | Verify IAM role `roles/compute.networkAdmin` |
| `400 Bad Request - Router not found` | Create router first: `gcloud compute routers create {{user.router_name}}` |

### Operation: Create VPC Peering

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CIDR overlap | Compare peering network subnets | No overlap | HALT; overlapping CIDRs will fail |
| IAM permission | SA has `compute.networks.updatePeering` | Has permission | HALT; grant permission |
| Peering limit | `gcloud compute networks list` peer count | < 25 peering limit | HALT; delete old peers |

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute networks peerings create` | Create `{{user.peering_name}}` with `--peer-project`, `--peer-network`, `--export-custom-routes --import-custom-routes` |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

### Operation: Delete VPC Peering

#### Safety Gate: MEDIUM

> **⚠️ PEERING CAUTION:** Deleting VPC peering closes connectivity between VPCs. Both sides must also delete their peering connections. This may break cross-VPC network resources.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Peering exists | `gcloud compute networks peerings list --network="{{user.network_name}}"` | Peering found | HALT; not found |
| Peering state | `jq '.state'` | `ACTIVE` or `CONNECTED` | Warn before deletion |
| Cross-VPC dependencies | Review VMs/shared VPC services | No VMs using peering | WARN before deletion |
| Confirmation | User explicitly confirms | User confirms | HALT; no confirmation |
| Peer side action | Verify peer will also delete their peering | Peer action confirmed | HALT; peer not coordinated |

#### Execution

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute networks peerings list` | List current peerings on `{{user.network_name}}` |
| 2 | `gcloud compute networks peerings describe` | Show `{{user.peering_name}}` details (`name, peerNetwork, state`) before deletion |
| 3 | Confirm | User must type `CONFIRM DELETE` to proceed |
| 4 | `gcloud compute networks peerings delete` | Delete with `--quiet` (only after Safety Gate passes) |
| 5 | Peer side | **Also delete on peer network:** `gcloud compute networks peerings delete {{user.peering_name}} --peer-project={{user.peer_project}} --peer-network={{user.peer_network}}` |
| 6 | Python SDK fallback | `peering_client.get(...)` then `peering_client.delete(...)` — full script at [assets/code-snippets/delete_vpc_peering.py](assets/code-snippets/delete_vpc_peering.py) |

Full command + flags at [references/gcloud-usage.md](references/gcloud-usage.md).

#### Post-execution Validation

| Step | Command | Expected | On Failure |
|------|---------|----------|------------|
| Verify deletion | `gcloud compute networks peerings describe {{user.peering_name}}` | Returns NOT_FOUND | HALT; deletion failed |
| Check operations | `gcloud compute operations list --filter="targetLink=~peerings.*{{user.peering_name}}"` | No pending operations | WARN |

#### Failure Recovery

| Error | Fix |
|-------|-----|
| `404 Not Found - Peering not found` | Peering already deleted or wrong parameters |
| `403 Forbidden` | Verify IAM role `roles/compute.networkAdmin` on both sides |
| `400 Bad Request - Peering bound to resources` | Disassociate from VMs/shared VIPs first |
| `400 Bad Request - Peering state: READY` | Peering not activated on peer side; wait for peer action |

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

## Quality Gate (GCL)

This skill uses the **Generator-Critic-Loop (GCL)** adversarial quality gate.

| Dimension | Classification | Default `max_iter` | Most-scrutinized ops |
|-----------|---------------|:------------------:|----------------------|
| Cloud VPC | `required` | 2 | Delete Network, Delete Subnet, Delete Firewall Rule, Modify Firewall Rule (broadening access) |

**Rubric:** See [references/rubric.md](references/rubric.md)
**Prompt templates:** See [references/prompt-templates.md](references/prompt-templates.md)
**Best Practices:** See [references/advanced/operational-best-practices.md](references/advanced/operational-best-practices.md)

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