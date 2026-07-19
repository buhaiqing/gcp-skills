---
name: gcp-armor-ops
description: >-
  Use when the user needs to create, configure, manage, or troubleshoot Google
  Cloud Armor — security policies, WAF rules, DDoS protection, rate limiting,
  bot management, IP allowlist/denylist, and pre-configured WAF rules. User
  mentions Cloud Armor, WAF, DDoS, security policy, firewall rule, rate limit,
  bot protection, or describes protection scenarios (e.g., "block SQL injection",
  "add IP denylist", "configure rate limiting") even without naming the product
  directly. Not for VPC firewall rules, Load Balancing, or CDN that have their
  own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Compute
  Security Admin IAM role, network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-15"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://compute.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud compute security-policies --help confirms subcommands: create, delete,
    describe, list, update, rules. See https://cloud.google.com/sdk/gcloud/reference/compute/security-policies
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Armor Operations Skill

## Overview

Google Cloud Armor provides DDoS protection and WAF (Web Application Firewall) for applications behind Google Cloud Load Balancers. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` supports Cloud Armor operations via `gcloud compute security-policies`. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Cloud Armor) with clear delegation to related skills (LB, VPC, CDN) |

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | WAF rules, DDoS protection, IP denylist, bot management, pre-configured rules | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Rule versioning, adaptive protection, fail-open vs fail-closed | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Security policy pricing, request-based billing | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Rule evaluation order, pre-configured rules, bulk operations | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Rule impact on latency, logging configuration | `references/well-architected-assessment.md` §2.5 |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Cloud Armor", "WAF", "DDoS protection", "security policy"
- Task involves creating, describing, modifying, or deleting Cloud Armor security policies
- Task involves managing WAF rules (allow, deny, throttle, redirect, return-404)
- Task involves configuring rate limiting, bot management, IP allowlist/denylist
- Task involves pre-configured WAF rules (SQL injection, XSS, etc.)
- Task involves adaptive DDoS protection
- User describes protection scenarios (e.g., "block attacks", "protect my app", "add firewall rules")

### SHOULD NOT Use This Skill When

- Task is purely about VPC firewall rules → delegate to: `gcp-vpc-ops`
- Task is purely about Cloud Load Balancing → delegate to: `gcp-lb-ops`
- Task is purely about Cloud CDN → delegate to: `gcp-cdn-ops`
- Task is purely about IAM / permissions → delegate to: `gcp-iam-ops`
- Task is purely about billing / cost → delegate to: `gcp-billing-ops`
- User insists on **console-only** flows with no API → state limitation

### Delegation Rules

| Resource | Delegated Skill | Flow |
|----------|----------------|------|
| Load Balancer + Armor | `gcp-lb-ops` | LB creates → Armor policy attached to backend service |
| VPC firewall rules | `gcp-vpc-ops` | VPC network → Armor provides L7 protection |
| CDN + Armor | `gcp-cdn-ops` | CDN cache → Armor protects origin |

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.policy_name}}` | Security policy name | Ask once; reuse |
| `{{user.rule_priority}}` | Rule priority (1-2147483647) | Ask once; reuse |
| `{{output.policy_id}}` | From last API or `gcloud` JSON response | Parse per REST API path |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value.

## API and Response Conventions (Agent-Readable)

- **REST API is canonical** for path, query, body fields, enums, and response shapes.
- **Errors:** Map SDK/gRPC/HTTP errors to canonical gRPC status codes and messages.
- **Timestamps:** RFC 3339 with timezone when the API returns strings.

### Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Create | `$.targetLink` | string | New security policy URL |
| Describe | `$.fingerprint` | string | Policy fingerprint for updates |
| List | `$.items[].name` | array | Security policy names |
| Update | `$.operationType` | string | Operation tracking |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create | — | `READY` | via Operations API | 300s |
| Update | `READY` | `READY` | via Operations API | 300s |
| Delete | any stable state | absent | via Operations API | 300s |

## Quick Start

### What This Skill Does
This skill enables you to manage Cloud Armor security policies, WAF rules, DDoS protection, and bot management on Google Cloud using the `gcloud` CLI (primary) or JIT Go SDK (fallback).

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`
- [ ] Compute Security Admin IAM role granted

### Verify Setup
```bash
# Check gcloud and project
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
```

### Your First Command
```bash
# List all security policies
gcloud compute security-policies list --project={{env.CLOUDSDK_CORE_PROJECT}} --format="json"
```

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Create Policy | Create a new security policy | Medium | Low |
| Describe Policy | View policy details | Low | None |
| Update Policy | Modify policy configuration | Medium | Medium |
| Delete Policy | Remove a security policy | Low | **High** — irreversible |
| Add Rule | Add a WAF rule to policy | Medium | Low |
| Update Rule | Modify existing rule | Medium | Low |
| Remove Rule | Delete a rule from policy | Low | Medium |
| List Rules | View all rules in policy | Low | None |

> Token Efficiency 规则详见根目录 AGENTS.md §9（TE-1~TE-8，禁止跨文件重复 — TE-6）。

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-15 | Initial Cloud Armor skill with WAF, DDoS, rate limiting, bot management |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud and/or SDK/API) → Validate → Recover**.

### Operation: Create Security Policy

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI / deps | `gcloud version` | Exit code 0 | Document gcloud install |
| Credentials | gcloud auth / SA key file | Non-empty / valid | HALT; user authenticates |
| Project | `gcloud config get-value project` or env var | Set and valid | HALT; user sets project |
| Quota | Check project quotas | Sufficient quota | HALT; user requests increase |

#### Execution — CLI (`gcloud`)

```bash
gcloud compute security-policies create {{user.policy_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --description="Security policy created by agent" \
  --format="json"
```

#### Execution — Python SDK (Primary Fallback)

```python
# create_security_policy.py
import os
from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = compute_v1.SecurityPoliciesClient()

security_policy = compute_v1.SecurityPolicy(
    name="{{user.policy_name}}",
    description="Security policy created by agent",
)

request = compute_v1.InsertSecurityPolicyRequest(
    project=project,
    security_policy_resource=security_policy,
)

operation = client.insert(request=request)
# Wait for operation to complete
```

#### Post-execution Validation

```bash
gcloud compute security-policies describe {{user.policy_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name: .name, fingerprint: .fingerprint}'
```

#### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|--------------|-------------|---------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | 0–1 | — | Fix args from API reference | `[ERROR] INVALID_ARGUMENT: Invalid policy configuration` |
| `ALREADY_EXISTS` / 409 | 0 | — | Ask reuse vs new name | `[ERROR] ALREADY_EXISTS: Policy name already exists` |
| `QUOTA_EXCEEDED` / 429 | 0 | — | HALT | `[ERROR] QUOTA_EXCEEDED: Security policy quota reached` |
| `PERMISSION_DENIED` / 403 | 0 | — | HALT | `[ERROR] PERMISSION_DENIED: Insufficient IAM permissions` |

### Operation: Add Rule to Policy

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Policy exists | Describe policy | Policy in READY state | HALT — create policy first |
| Priority unique | List rules | Priority not taken | FIX — use different priority |

#### Execution — CLI (`gcloud`)

```bash
# Add allow rule
gcloud compute security-policies rules create {{user.rule_priority}} \
  --security-policy={{user.policy_name}} \
  --expression="origin.ipgeo.country == 'US'" \
  --action="allow" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Add deny rule with pre-configured WAF
gcloud compute security-policies rules create {{user.rule_priority}} \
  --security-policy={{user.policy_name}} \
  --expression="evaluatePreconfiguredWaf('xss-v33-stable')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Add rate limiting rule
gcloud compute security-policies rules create {{user.rule_priority}} \
  --security-policy={{user.policy_name}} \
  --expression="true" \
  --action="throttle" \
  --rate-limit-threshold-count=1000 \
  --rate-limit-threshold-interval-sec=60 \
  --conform-action="allow" \
  --exceed-action="deny-429" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud compute security-policies rules list {{user.policy_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.[] | select(.priority == {{user.rule_priority}})'
```

### Operation: Delete Security Policy

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of `{{user.policy_name}}`.
- **MUST** verify no load balancers reference this policy.
- **MUST NOT** proceed without clear user assent.

#### Execution — CLI (`gcloud`)

```bash
gcloud compute security-policies delete {{user.policy_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet
```

#### Post-execution Validation

Poll describe until `NOT_FOUND` or status indicates deleted.

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [gcloud Usage](references/gcloud-usage.md)
- [Troubleshooting Guide](references/troubleshooting.md)
- [Monitoring & Alerts](references/monitoring.md)
- [Integration](references/integration.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Advanced WAF Rules](references/advanced/advanced-waf-rules.md)
- [Bot Management](references/advanced/bot-management.md)
- [Adaptive Protection](references/advanced/adaptive-protection.md)

## Operational Best Practices

- **Least privilege:** IAM roles scoped to required permissions only.
- **Rule ordering:** Evaluate most specific rules first; use priority wisely.
- **Pre-configured rules:** Use WAF pre-configured rules for common attacks.
- **Logging:** Enable security policy logging for audit and diagnostics.
- **Adaptive protection:** Enable adaptive DDoS protection for automatic tuning.

## AIOps 自愈 (Self-Healing)

When adaptive protection triggers an auto-deploy rule, this skill supports a **closed-loop self-healing** flow: detect → classify (via `docs/error-taxonomy.md`) → **dry-run preview** → **human review gate** → idempotent apply → validate. All mutating actions are dry-run-first, idempotent, and credential-masked (root `AGENTS.md` §0.1); T2/T3 blast-radius actions are gated or **HALT**ed.

- **Attack Mitigation Self-Healing runbook:** [references/advanced/adaptive-protection.md](references/advanced/adaptive-protection.md) §Attack Mitigation Self-Healing
- **Blast radius (Armor → LB → GCE/VPC/CDN):** [docs/cross-skill-blast-radius.md](docs/cross-skill-blast-radius.md)
- **Unified error taxonomy / recovery actions:** [docs/error-taxonomy.md](docs/error-taxonomy.md)
