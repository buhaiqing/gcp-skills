---
name: gcp-lb-ops
description: >-
  Use when the user needs to create, configure, manage, or troubleshoot Google
  Cloud Load Balancing — forwarding rules, backend services, backend buckets,
  target proxies, URL maps, SSL certificates, health checks, and network
  endpoint groups (NEGs). User mentions load balancer, LB, forwarding rule,
  backend service, URL map, health check, NEG, target proxy, SSL certificate,
  Cloud CDN, or describes load-balancing scenarios (e.g., "set up HTTPS load
  balancer", "expose service to internet", "health check failing", "traffic not
  reaching backends", "certificate expired") even without naming the product
  directly. Not for VPC, IAM, DNS, or instance-level operations that have their
  own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Compute Load
  Balancer Admin IAM role, network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://compute.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud compute --help confirms subcommands: forwarding-rules, backend-services,
    backend-buckets, target-http-proxies, target-https-proxies, target-tcp-proxies,
    target-ssl-proxies, target-grpc-proxies, target-pools, url-maps, ssl-certificates,
    ssl-policies, health-checks, network-endpoint-groups. See
    https://cloud.google.com/sdk/gcloud/reference/compute
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Load Balancing Operations Skill

## Overview

Google Cloud Load Balancing distributes traffic across backend resources — VM instances, managed instance groups (MIGs), NEGs, Cloud Storage buckets, and serverless services. Six LB types cover external HTTP(S), TCP/SSL proxy, TCP/UDP passthrough, and their internal equivalents. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the User Experience Specification (gcp-skill-generator). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` fully supports Load Balancing via `gcloud compute forwarding-rules`, `gcloud compute backend-services`, etc. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step for every operation. Coverage gaps (SDK-only operations) are listed in `references/gcloud-usage.md`.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Load Balancing) with clear delegation to related skills (VPC, GCE, DNS) |

Refer to the meta-skill (gcp-skill-generator) for detailed descriptions of each standard.

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | SSL policies, TLS versions, Cloud Armor, IAP origin/device filtering, private LB with VPC SC | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Multi-region backend distribution, failover backends (regional LB), health check fail-fast, drain mode | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Pricing model (no charge for LB itself, data processing charges), backend bucket vs backend service cost, CDN egress | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | URL map path/routing efficiency, backend capacity planning, NEG vs instance group considerations | `references/well-architected-assessment.md` §2.4 |
| **Performance** | LB types latency comparison (global vs regional), session affinity, connection draining, compression | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "load balancer", "LB", "forwarding rule", "backend service", "backend bucket", "URL map", "health check", "NEG", "target proxy", "SSL certificate", "Cloud CDN"
- Task involves creating, describing, modifying, or deleting forwarding rules (global/regional, external/internal)
- Task involves managing backend services (global, regional) with instance groups, NEGs, or serverless backends
- Task involves URL maps (path matchers, host rules)
- Task involves SSL certificates (managed Google-issued, self-managed) and SSL policies
- Task involves health checks (HTTP, HTTPS, TCP, SSL, gRPC)
- Task involves network endpoint groups (zonal, regional, internet, serverless, hybrid, GCE VM)
- User describes LB scenarios: "traffic not reaching backends", "health check failing", "certificate error", "404 on LB", "set up HTTPS", "expose service to internet", "internal load balancing"
- Keywords: load balancer, LB, forwarding rule, backend, URL map, health check, NEG, target proxy, SSL certificate, Cloud Armor, CDN, traffic split, session affinity, connection draining

### SHOULD NOT Use This Skill When

- Task is purely about VPC / subnets / firewall rules → delegate to: `gcp-vpc-ops`
- Task is purely about DNS records / Cloud DNS → delegate to: `gcp-dns-ops`
- Task is purely about IAM / service accounts → delegate to: `gcp-iam-ops`
- Task is purely about Cloud CDN origin/policy only (no LB changes) → delegate to: `gcp-cdn-ops`
- Task is purely about instance-level operations (SSH, OS, disk) → delegate to: `gcp-gce-ops`
- Task is purely about container/GKE ingress → delegate to: `gcp-gke-ops`
- User insists on console-only flows → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- **VPC**: For subnet selection in forwarding rules, internal LB ranges → delegate to `gcp-vpc-ops`.
- **GCE**: For MIG/instance group backend creation → delegate to `gcp-gce-ops`; do not duplicate MIG flows.
- **DNS**: For DNS record setup pointing at LB IP → delegate to `gcp-dns-ops`.
- **SSL Certificates**: For Certificate Manager (beyond compute SSL certs) → reference `gcp-certificate-manager-ops` when available.
- **GCL**: Execution quality gate uses `gcp-gcl-runner-ops`.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.region}}` | Regional LB region | Ask once; reuse |
| `{{user.name}}` | Resource name (generic) | Ask once; reuse |
| `{{user.lb_name}}` | Load balancer naming prefix | Ask once; reuse |
| `{{user.forwarding_rule_name}}` | Forwarding rule name | Ask once; reuse |
| `{{user.backend_service_name}}` | Backend service name | Ask once; reuse |
| `{{user.url_map_name}}` | URL map name | Ask once; reuse |
| `{{user.health_check_name}}` | Health check name | Ask once; reuse |
| `{{user.neg_name}}` | NEG name | Ask once; reuse |
| `{{user.certificate_name}}` | SSL certificate name | Ask once; reuse |
| `{{user.ip_address}}` | Static IP address | Ask once; reuse |
| `{{user.port}}` | Port number | Default: 80 (HTTP) or 443 (HTTPS) |
| `{{output.forwarding_rule_ip}}` | LB IP address from create/describe | Parse from `$.IPAddress` |
| `{{output.forwarding_rule_self_link}}` | Forwarding rule self link | Parse from `$.selfLink` |
| `{{output.backend_service_self_link}}` | Backend service self link | Parse from `$.selfLink` |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** NEVER log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value in console output, debug messages, error messages, or logs.

| Execution Path | Safe Pattern | Unsafe Pattern |
|----------------|-------------|----------------|
| Console output | `GOOGLE_APPLICATION_CREDENTIALS=<masked>` | `{"private_key": "-----BEGIN...` |
| Error messages | `Error: API call failed (credential omitted)` | `Error: ... actual SA key content...` |
| Verification | `test -f "$GOOGLE_APPLICATION_CREDENTIALS"` | `cat $GOOGLE_APPLICATION_CREDENTIALS` |
| Go SDK | `os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")` | `log.Printf("%+v", client)` |

## API and Response Conventions (Agent-Readable)

- **REST API is canonical**: Compute Engine v1 API (`compute.googleapis.com`). All JSON paths verified against official docs.
- **Errors**: Map HTTP/gRPC status codes to canonical error types.
- **Idempotency**: Named resources use unique naming; `ALREADY_EXISTS` for duplicates.

### Key JSON Paths (Centralized per TE-4)

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Forwarding Rule Create | `$.IPAddress` | string | Assigned IP address |
| Forwarding Rule Create | `$.name` | string | Operation name |
| Forwarding Rule Describe | `$.{name,IPAddress,IPProtocol,portRange,backendService,loadBalancingScheme}` | mixed | Forwarding rule details |
| Backend Service Create | `$.targetLink` | string | Resource self-link |
| Backend Service Describe | `$.{name,backends,healthChecks,sessionAffinity,timeoutSec}` | mixed | Backend service details |
| URL Map Describe | `$.{name,defaultService,hostRules,pathMatchers}` | mixed | URL map details |
| Health Check Describe | `$.{name,type,checkIntervalSec,timeoutSec,healthyThreshold,unhealthyThreshold}` | mixed | Health check details |
| NEG Describe | `$.{name,networkEndpointType,size,zone}` | mixed | NEG details |
| Operation Describe | `$.{status,httpErrorMessage,error}` | mixed | Operation tracking |

### Expected State Transitions

| Resource | Terminal State | Notes |
|----------|---------------|-------|
| Forwarding Rule | `DONE` (sync) | No async polling needed |
| Backend Service | `DONE` (sync) | No async polling needed |
| URL Map | `DONE` (sync) | No async polling needed |
| Health Check | `DONE` (sync) | No async polling needed |
| NEG | `DONE` (sync) | No async polling needed |
| SSL Certificate | `DONE` (sync) | No async polling needed |

## Quick Start

### What This Skill Does
This skill enables you to create, configure, troubleshoot, and monitor Google Cloud Load Balancing resources using the `gcloud` CLI (primary) or Go SDK (fallback).

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `CLOUDSDK_CORE_PROJECT`
- [ ] IAM roles: `roles/compute.loadBalancerAdmin`

### Verify Setup
```bash
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
gcloud compute forwarding-rules list --limit=1 --format="json" &>/dev/null && echo "✅ LB API OK"
```

### Your First Command
```bash
# List all forwarding rules
gcloud compute forwarding-rules list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — LB types, architecture, quotas
- [Common Operations](#execution-flows) — Create and manage LB resources
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Forwarding Rule Create | Create external/internal forwarding rules | Medium | **Medium** — traffic exposure |
| Backend Service Create | Create global/regional backend services | Medium | Medium |
| Backend Service Add Backend | Add instance group/NEG to backend service | Low | Medium |
| URL Map Create | Create URL map with host/path routing | Medium | Medium |
| URL Map Update | Update URL map routing rules | Medium | **Medium** — traffic disruption |
| Health Check Create | Create health check (HTTP/HTTPS/TCP/SSL/gRPC) | Low | Low |
| SSL Certificate Create | Create managed or self-managed SSL cert | Low | Low |
| NEG Create | Create network endpoint group | Low | Low |
| Health Check Delete | Delete a health check | Low | **High** — backend health monitoring lost |
| Forwarding Rule Delete | Delete a forwarding rule | Low | **High** — traffic drops |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release: forwarding rules, backend services, URL maps, health checks, NEGs, SSL certs, dual-path gcloud+SDK, GCL quality gate |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud + SDK/API) → Validate → Recover**. Do not skip phases.

### Operation: Create External HTTP(S) Load Balancer (Global)

This is the most common LB setup, composed of multiple resources.

#### Component Architecture

```
Internet → Forwarding Rule → Target HTTPS Proxy → SSL Certificate
                                                       ↓
                                                  URL Map
                                                     ↓
                                          Backend Service ← Health Check
                                               ↓
                                    Instance Group / NEG
```

The recommended creation order:
1. Health Check
2. Backend Service (with backends)
3. URL Map (routing to backend service)
4. SSL Certificate (managed)
5. Target HTTPS Proxy
6. Forwarding Rule

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI | `gcloud version` | Exit 0 | HALT — install gcloud |
| Credentials | `gcloud auth print-access-token --quiet` | Token valid | HALT — authenticate |
| Project | `gcloud config get-value project` | Set | HALT — set project |
| Compute API | `gcloud services list --enabled|grep compute.googleapis.com` | Enabled | HALT — enable API |
| Static IP | If using reserved IP: `gcloud compute addresses describe {{user.ip_name}} --global --quiet` | Exit 0 | HALT — create IP first |
| Backend exists | Instance group or NEG exists | Exit 0 | HALT — create via gcp-gce-ops |

#### Smart Defaults

| Field | Default | Rationale |
|-------|---------|-----------|
| region | Global (for external LB) | Global LB has single anycast IP |
| LB scheme | `EXTERNAL_MANAGED` | Modern managed LB with advanced features |
| IP version | `IPV4` | Universal client compatibility |
| Protocol | `HTTPS` | Industry standard with TLS |

#### Execution (gcloud — full commands in `references/gcloud-usage.md`)

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute health-checks create http` | HTTP health check (port `{{user.port:-80}}`, interval 10s, timeout 5s, 2/3 thresholds) |
| 2 | `gcloud compute backend-services create` | Global HTTP backend service, attach health check, `--enable-cdn` |
| 3 | `gcloud compute backend-services add-backend` | Add instance group (`--balancing-mode=UTILIZATION --max-utilization=0.8`) **or** NEG (`--network-endpoint-group`) |
| 4 | `gcloud compute url-maps create` | URL map → default backend service |
| 5 | `gcloud compute ssl-certificates create` | Managed cert for `{{user.domain_name}}` (provision 5–10 min) |
| 6 | `gcloud compute target-https-proxies create` | Target proxy → url-map + cert + ssl-policy |
| 7 | `gcloud compute forwarding-rules create` | Rule `{{user.lb_name}}-https-rule`, `--ports=443 --load-balancing-scheme=EXTERNAL_MANAGED` |

**HTTP-only alternative:** skip steps 5–6; use `target-http-proxies create` + forwarding rule `--ports=80`.

#### Post-execution Validation

1. Describe forwarding rule to get assigned IP:
```bash
gcloud compute forwarding-rules describe "{{user.lb_name}}-https-rule" \
  --global --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq '{name, IPAddress, IPProtocol, portRange, loadBalancingScheme}'
```
2. Verify backend health: `gcloud compute backend-services get-health "{{user.backend_service_name}}" --global --format="json"`
3. Test LB endpoint: `curl -sI "https://{{user.domain_name}}/" | head -5`
4. On failure, go to **Failure Recovery**.

#### Failure Recovery

| Error Code | Max retries | Agent Action | UX Feedback |
|------------|-------------|--------------|-------------|
| INVALID_ARGUMENT / 400 | 0-1 | Fix args; retry once | `[ERROR] Parameter invalid — see API reference` |
| QUOTA_EXCEEDED / 429 | 0 | HALT | `[ERROR] Forwarding rule/backend service quota exceeded — request increase` |
| PERMISSION_DENIED / 403 | 0 | HALT | `[ERROR] SA lacks compute.* permissions for LB operations` |
| ALREADY_EXISTS / 409 | 0 | Ask rename | `[ERROR] Resource name already in use` |
| `RESOURCE_NOT_READY` | 3 | exp. backoff | `⚠️ Backend resource not ready. Retrying after {backoff}s` |
| INTERNAL / 500 | 3 | 2/4/8s | `[ERROR] GCP server error — escalate if persistent` |
| `INVALID_FORWARDING_RULE_TARGET` | 0 | HALT | `[ERROR] Target proxy not found or mismatch — verify resource names` |
| `CERTIFICATE_PREPARATION` | 3 | 15s intervals | `⚠️ Managed SSL certificate provisioning in progress. Wait 5-10 min for FULLY_PROVISIONED` |

---

### Operation: Create Internal TCP/UDP Load Balancer (Regional)

#### Smart Defaults

| Field | Default | Rationale |
|-------|---------|-----------|
| LB scheme | `INTERNAL_MANAGED` | Managed internal LB |
| Protocol | `TCP` | Most common for internal |
| Region | `us-central1` | Default common region |
| Network | `default` | Default VPC |

#### Execution (gcloud — full commands in `references/gcloud-usage.md`)

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute health-checks create tcp` | TCP health check, `--region={{user.region}}` |
| 2 | `gcloud compute backend-services create` | Regional `INTERNAL_MANAGED` TCP service, attach health check |
| 3 | `gcloud compute backend-services add-backend` | Add MIG (`--balancing-mode=CONNECTION`), `--region` |
| 4 | `gcloud compute forwarding-rules create` | Rule `{{user.lb_name}}-internal-rule`, `--ports=ALL --network=default --subnet={{user.subnet}} --ip-protocol=TCP` |

#### Post-execution Validation

```bash
gcloud compute forwarding-rules describe "{{user.lb_name}}-internal-rule" \
  --region="{{user.region}}" \
  --format="json" | jq '{name, IPAddress, backendService, loadBalancingScheme}'
```

---

### Operation: Describe LB Resources

#### Execution (gcloud — full commands in `references/gcloud-usage.md`)

| Resource | Action | JSON extraction |
|----------|--------|----------------|
| Forwarding rule | `gcloud compute forwarding-rules describe {{user.forwarding_rule_name}} --global` | `$.{name,IPAddress,IPProtocol,portRange,backendService,loadBalancingScheme}` |
| Backend service | `gcloud compute backend-services describe {{user.backend_service_name}} --global` | `jq` → backends[group,balancingMode,capacityScaler], healthChecks, sessionAffinity, timeoutSec |
| URL map | `gcloud compute url-maps describe {{user.url_map_name}} --global` | `jq` → defaultService, hostRules, pathMatchers |
| Health check | `gcloud compute health-checks describe {{user.health_check_name}}` | full JSON |
| NEG | `gcloud compute network-endpoint-groups describe {{user.neg_name}} --zone={{user.zone}}` | `jq` → name, networkEndpointType, size, zone |

---

### Operation: Add URL Map Path Matcher

#### Pre-flight (Safety Gate)

- **MUST** display current URL map configuration so user sees existing routing rules
- **MUST** warn: "Traffic matching the path pattern will be rerouted to the new backend service"
- **MUST** verify new backend service reference is valid: `gcloud compute backend-services describe "{{user.api_backend_service_name}}" --global --quiet`
- **SHOULD** suggest canary testing with weighted backend routing (`--path-rules` with multiple `backend=weight` pairs)
- **MUST** obtain explicit user confirmation before applying routing changes

#### Execution (gcloud — full commands in `references/gcloud-usage.md`)

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute url-maps describe` | Show current map (`jq '{name, defaultService, hostRules, pathMatchers}'`) |
| 2 | `gcloud compute url-maps add-path-matcher` | `--default-service={{user.backend_service_name}} --path-matcher-name=api-matcher --path-rules="/api={{user.api_backend_service_name}}" --global` |

#### Post-execution Validation

```bash
gcloud compute url-maps describe "{{user.url_map_name}}" \
  --global --format="json" | jq '.pathMatchers[] | select(.name=="api-matcher")'
```

---

### Operation: Create NEG (Zonal)

#### Execution (gcloud — full commands in `references/gcloud-usage.md`)

| Type | Action | Key flags |
|------|--------|-----------|
| Zonal (VM) | `gcloud compute network-endpoint-groups create` | `--network-endpoint-type=GCE_VM_IP_PORT --zone={{user.zone}} --network=default --subnet={{user.subnet}} --default-port={{user.port:-80}}` |
| Serverless | `gcloud compute network-endpoint-groups create` | `--network-endpoint-type=SERVERLESS --region={{user.region}} --cloud-run-service={{user.cloud_run_service_name}}` |

---

### Operation: Delete Forwarding Rule

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: traffic will stop for users hitting this forwarding rule
- **MUST** show the forwarding rule details (name, IP address, ports, LB scheme)
- **MUST** confirm: `Proceed with delete of forwarding rule <name> (IP: <ip>)? This will drop all traffic. Confirm by typing the forwarding rule name:`
- **SHOULD** ask: "Has traffic been redirected to another LB or DNS updated?" — suggest traffic draining before proceeding

#### Execution (gcloud — full command in `references/gcloud-usage.md`)

```bash
gcloud compute forwarding-rules delete "{{user.forwarding_rule_name}}" --global
```

**Note:** Do NOT use `--quiet` — the pre-flight safety gate above provides interactive confirmation. `--quiet` would bypass it for any agent that copies the command directly.

#### Post-execution Validation

```bash
gcloud compute forwarding-rules describe "{{user.forwarding_rule_name}}" \
  --global --quiet 2>&1 || echo "✅ Forwarding rule confirmed deleted"
```

---

### Operation: Delete Backend Service

#### Pre-flight (Safety Gate)

- MUST warn: backend service may be in use by a URL map or target proxy
- MUST check: `gcloud compute url-maps list --format="json" | jq -r '.[].defaultService'` or path matchers referencing this backend
- If in use: HALT — advise user to delete/reassign URL map reference first
- **MUST** require the user to type the exact backend service name to confirm irreversible deletion
- SHOULD check backends' dependent resources (MIG/NEG) exist independently

#### Execution (gcloud — full command in `references/gcloud-usage.md`)

```bash
gcloud compute backend-services delete "{{user.backend_service_name}}" --global
```

---

### Operation: Create Managed SSL Certificate

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Domain DNS resolves | `dig +short {{user.domain_name}} A` | Returns IP | HALT — point DNS to LB IP first |
| CAA record (if exists) | `dig +short {{user.domain_name%%.*}} CAA` | Contains `pki.goog` or absent | Warn — CAA must include `pki.goog` for Google CA |
| LB IP provisioned | Pre-existing forwarding rule with static IP | LB IP matches DNS A record | HALT — create LB or reserve IP first |

#### Execution (gcloud — full command in `references/gcloud-usage.md`)

```bash
gcloud compute ssl-certificates create "{{user.certificate_name}}" \
  --domains="{{user.domain_name}}" --global
```

> **Async note:** Provisioning takes 5–10 minutes. Do NOT proceed to attach to target proxy until `FULLY_PROVISIONED`.

#### Post-execution Validation

Google-managed certificates take 5-10 minutes to provision. Poll status:
```bash
gcloud compute ssl-certificates describe "{{user.certificate_name}}" \
  --global --format="json" | jq '{
    name, type,
    managed: {status: .managed.status, domains: .managed.domains, domainStatuses: .managed.domainStatuses}
  }'
```

Status transitions: `PROVISIONING` → `PROVISIONING` (domain validation) → `FULLY_PROVISIONED`
On `FAILED` → check `.managed.domainStatuses` for specific domain errors.

---

## Prerequisites

> **Self-Healing:** Installation flows include multi-path recovery per the enhanced-self-healing-framework (gcp-skill-generator). Each step has ≥ 3 error-handling strategies.

1. **Install gcloud CLI**:
   > See AGENTS.md §0.3 — embedded gcloud install script (do not duplicate here).

2. **Bootstrap Go runtime** (JIT fallback):
   > See AGENTS.md §0.2 — embedded Go JIT bootstrap (do not duplicate here).

3. **Configure Credentials**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
   export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
   gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" 2>/dev/null \
   || gcloud auth login --quiet
   gcloud config set project "$CLOUDSDK_CORE_PROJECT"
   ```

4. **Verify Configuration**:
   ```bash
   gcloud config list
   gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
   ```

## Reference Directory

- [Core Concepts](references/core-concepts.md) — LB types, architecture, quotas, regions
- [API & SDK Usage](references/api-sdk-usage.md) — REST API, operation map, pagination
- [gcloud Usage](references/gcloud-usage.md) — `gcloud compute` command map for LB
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes, diagnostics, health check issues
- [Monitoring & Alerts](references/monitoring.md) — Cloud Monitoring metrics for LB
- [Integration](references/integration.md) — Go SDK bootstrap, env vars, credential rules
- [Idempotency Checklist](references/idempotency-checklist.md) — Retry-safe patterns
- [Well-Architected Assessment](references/well-architected-assessment.md) — Five-pillar assessment
- [Rubric — GCL](references/rubric.md) — Generator-Critic-Loop scoring rubric
- [Prompt Templates — GCL](references/prompt-templates.md) — GCL generator and critic templates

## Operational Best Practices

- **Traffic safety**: Never delete a forwarding rule or backend service without confirming impact and migrating traffic first.
- **Health checks**: Always configure health checks; avoid default "everything healthy" behavior.
- **SSL/TLS**: Use managed certificates (Google-issued) for simplicity; use SSL policies to enforce TLS 1.2+ and modern ciphers.
- **Connection draining**: Set connection draining timeout (60-300s) on backend services to avoid killing in-flight requests during updates.
- **Capacity**: Monitor backend capacity; configure `maxRatePerInstance` or `maxUtilization` for scaling signals.
- **Logging**: Enable Cloud Logging for LB (HTTP logs) for debugging and audit.
- **Naming**: Follow `{env}-{lb-type}-{app}` convention; eg. `prod-ext-https-app`.
- **Global vs Regional**: Use global LB for multi-region backends; regional LB for latency-optimized single-region deployments.

## Quality Gate (GCL)

> This skill implements the **Generator-Critic-Loop (GCL)** adversarial quality gate per the repo AGENTS.md §11.

| Property | Value |
|----------|-------|
| Classification | **required** (LB changes affect production traffic; delete operations present) |
| max_iter | 2 |
| Most-scrutinized operations | Delete Forwarding Rule, Delete Backend Service, Delete Health Check, Modify URL Map routing |

- **Rubric**: [references/rubric.md](references/rubric.md) — 5 core dimensions + 3 GCP extensions
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md) — Generator + Critic templates

> Token Efficiency 规则详见根目录 AGENTS.md §9（TE-1~TE-8，禁止跨文件重复 — TE-6）。

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release: forwarding rules, backend services, URL maps, health checks, NEGs, SSL certs; dual-path gcloud+SDK; GCL quality gate |

## See Also

- **Meta-Skill**: gcp-skill-generator
- **VPC**: gcp-vpc-ops — Networking for internal LB
- **GCE**: gcp-gce-ops — Instance groups and NEGs as backends
- **DNS**: gcp-dns-ops — DNS records pointing at LB IP
- **Monitoring**: gcp-monitoring-ops — Dashboards and alerts
- **GCL Runner**: gcp-gcl-runner-ops — Execution quality gate

## AIOps 自愈 (Self-Healing)

> Cloud Load Balancing 异常检测与自愈锚点（健康检查失败、后端容量耗尽、SSL 证书过期）见 [references/advanced/aiops-lb-anomaly.md](references/advanced/aiops-lb-anomaly.md)。所有自愈动作均带 **dry-run + 幂等 + 人工复核门禁**，破坏性操作标 **HALT**，绝不自动执行。