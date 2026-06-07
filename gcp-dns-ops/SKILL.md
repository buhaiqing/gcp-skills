---
name: gcp-dns-ops
description: >-
  Use when the user needs to create, manage, troubleshoot, or monitor Google
  Cloud DNS resources — managed zones, record-sets, DNS policies, and zone
  operations. User mentions Cloud DNS, DNS zone, managed zone, DNS records,
  A record, CNAME, MX record, NS record, DNSSEC, private DNS, or describes
  DNS scenarios (e.g., "create DNS zone", "add A record", "DNS not resolving",
  "private DNS for VPC", "configure DNSSEC") even without naming the product
  directly. Not for Cloud Domains registration, Cloud Load Balancing, or other
  networking products that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with DNS Admin IAM
  role, network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://dns.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud dns --help confirms subcommands: managed-zones, record-sets,
    policies, response-policies. See
    https://cloud.google.com/sdk/gcloud/reference/dns
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud DNS Operations Skill

## Overview

Google Cloud DNS is a scalable, reliable, and managed DNS service. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery for managed zones, record-sets, and DNS policies.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` supports Cloud DNS via `gcloud dns managed-zones`, `gcloud dns record-sets`, and `gcloud dns policies`. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step for every operation. Coverage gaps (SDK-only operations) are listed in `references/gcloud-usage.md`.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Cloud DNS) with clear delegation to related skills (VPC, Load Balancing, Monitoring) |

Refer to the [meta-skill](../gcp-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions of each standard.

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | DNSSEC signing, private zones with VPC binding, IAM policies (roles/dns.admin), VPC Service Controls | `references/well-architected-assessment.md` §2.1 |
| **Stability** | DNS propagation management, TTL strategies, failover record configuration, multi-region DNS | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Managed zone pricing, DNS query costs, DNSSEC signing costs, optimization patterns | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Transaction-based bulk record operations, automation patterns, SDK vs CLI selection | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Query latency monitoring, cache TTL optimization, name server performance, response policies | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Cloud DNS", "Google DNS", "managed zone", "DNS records", "A record", "CNAME", "MX record", "NS record", "DNSSEC", "private DNS"
- Task involves CRUD or lifecycle operations on managed zones (create, describe, update, delete, list)
- Task involves record-set operations (create, describe, update, delete, list) via transaction API
- Task involves DNS policies (list, describe, create, delete)
- Task involves managed-zone operations monitoring
- User describes DNS scenarios: "zone not resolving", "add DNS record", "delete DNS entry", "configure DNSSEC", "private DNS for VPC", "DNS propagation delay"
- Keywords: managed-zone, record-set, DNS, A, AAAA, CNAME, MX, TXT, NS, SOA, SRV, PTR, NAPTR, SPF, DNSSEC, peering zone, private zone

### SHOULD NOT Use This Skill When

- Task is about domain registration or transfer → delegate to: `gcp-domains-ops` (when present) or Cloud Domains console
- Task is about load balancer configuration (not DNS records for LB) → delegate to: `gcp-lb-ops`
- Task is about VPC network or firewall rules → delegate to: `gcp-vpc-ops`
- Task is about Cloud Monitoring or alerting → delegate to: `gcp-monitoring-ops`
- Task is about IAM / service accounts → delegate to: `gcp-iam-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- **VPC network for private zones**: If VPC network does not exist or needs configuration, delegate to `gcp-vpc-ops` first. Private zones require VPC network binding.
- **Load balancer DNS records**: When creating DNS records pointing to load balancer IPs, verify LB exists via `gcp-lb-ops` before adding records.
- **Compute Engine instance DNS**: When configuring DNS for compute instances, coordinate with `gcp-gce-ops` for internal IP resolution.
- **Monitoring/Alerts for DNS**: Delegate DNS query monitoring and alerting to `gcp-monitoring-ops`.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.zone_name}}` | Managed zone name | Ask once; reuse |
| `{{user.dns_name}}` | DNS domain name (e.g., example.com) | Ask once; reuse |
| `{{user.record_name}}` | Record-set FQDN (e.g., www.example.com) | Ask once; reuse |
| `{{user.record_type}}` | Record type (A, AAAA, CNAME, MX, TXT, NS, SOA, SRV, PTR, NAPTR, SPF) | Ask once; reuse |
| `{{user.ttl}}` | TTL in seconds (default: 300) | Ask once; reuse |
| `{{user.record_data}}` | Record data (IP, hostname, text, etc.) | Ask once; reuse |
| `{{user.visibility}}` | Zone visibility: `public` or `private` | Ask once; reuse |
| `{{user.network}}` | VPC network name (for private zones) | Ask once; reuse |
| `{{user.description}}` | Zone or record description | Ask once; reuse |
| `{{output.zone_name}}` | Created/identified managed zone name | Parse from API response |
| `{{output.name_servers}}` | Assigned name servers for zone | Parse from API response |
| `{{output.change_id}}` | Change operation ID from record transaction | Parse from API response |
| `{{output.dnssec_status}}` | DNSSEC signing status | Parse from API response |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value in console output, debug messages, error messages, or logs. Python SDK reads credentials via env var automatically (safe). Go SDK scripts' `config` structs, `fmt.Println(config)`, and `log.Printf("%+v", ...)` can all leak credentials — prohibit such output.

## API and Response Conventions (Agent-Readable)

- **REST API is canonical**: `https://dns.googleapis.com/dns/v1/`
- **JSON paths centralized** (TE-4):

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Create zone | `$.name` | string | Zone name |
| Create zone | `$.dnsName` | string | DNS domain name |
| Create zone | `$.nameServers[]` | array | Assigned name servers |
| Create zone | `$.visibility` | string | `public` or `private` |
| Describe zone | `$.creationTime` | string | RFC 3339 timestamp |
| Describe zone | `$.dnssecConfig.state` | string | DNSSEC state |
| List zones | `$.managedZones[].name` | array | Zone names |
| List zones | `$.managedZones[].dnsName` | array | Zone DNS names |
| Execute change | `$.change.kind` | string | Change resource kind |
| Execute change | `$.change.id` | string | Change ID |
| Execute change | `$.change.startTime` | string | Start timestamp |
| Describe change | `$.change.status` | string | `pending` or `done` |
| List records | `$.rrsets[].name` | array | Record-set names |
| List records | `$.rrsets[].type` | array | Record types |
| List records | `$.rrsets[].ttl` | array | TTL values |
| List records | `$.rrsets[].rrdatas[]` | array | Record data arrays |
| List operations | `$.operations[].status` | array | Operation status |
| List operations | `$.operations[].startTime` | array | Start timestamps |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create zone | — | `PENDING` → `ACTIVE` | 5s | 120s |
| Record change | — | `pending` → `done` | 5s | 300s |
| Delete zone | `ACTIVE` | absent | 10s | 180s |

## Quick Start

### What This Skill Does
This skill enables you to manage Cloud DNS resources on Google Cloud using the `gcloud` CLI (primary) or Python/Go SDK (fallback). Operations include managed zone lifecycle, record-set management via transaction API, DNS policy configuration, and zone operation monitoring.

### Prerequisites
- [ ] `gcloud` CLI installed (or Python 3.8+ / Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`
- [ ] IAM role: `roles/dns.admin` (full access) or `roles/dns.reader` (read-only)

### Verify Setup
```bash
# Check gcloud and project
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "Auth OK"

# Verify DNS access
gcloud dns managed-zones list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" --limit=1
```

### Your First Command
```bash
# List managed zones
gcloud dns managed-zones list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Understand Cloud DNS architecture
- [Common Operations](#execution-flows) — Create, manage, and delete DNS resources
- [Troubleshooting](references/troubleshooting.md) — Fix common DNS issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Create Managed Zone | Create a public or private DNS zone | Low | Low |
| Describe Managed Zone | View zone details and name servers | Low | None |
| List Managed Zones | View all zones in a project | Low | None |
| Update Managed Zone | Modify zone description or config | Low | Low |
| Delete Managed Zone | Remove a DNS zone | Low | **High** — irreversible |
| Create Record-Set | Add DNS records via transaction | Medium | Medium |
| List Record-Sets | View all records in a zone | Low | None |
| Describe Record-Set | View a specific record-set | Low | None |
| Delete Record-Set | Remove DNS records via transaction | Medium | Medium |
| List Zone Operations | Monitor zone operation status | Low | None |
| List DNS Policies | View DNS response policies | Low | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial DNS operations skill with dual-path (gcloud + SDK) support |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud and/or SDK/API) → Validate → Recover**. Do not skip phases.

### Operation: Create Managed Zone

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI available | `gcloud dns --help` | Exit code 0 | HALT — install gcloud SDK |
| Credentials | `gcloud auth describe --format=json` | Valid account | HALT — user authenticates |
| Project set | `gcloud config get-value project` | Non-empty project ID | HALT — user sets project |
| DNS quota | `gcloud dns managed-zones list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \| jq '. \| length'` | Under zone quota limit | HALT — user requests quota increase |
| DNS name valid | Validate `{{user.dns_name}}` matches `^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.$` | Valid DNS name format | HALT — user provides valid DNS name |

#### Execution — CLI (`gcloud`) (Primary Path)

```bash
# Create public managed zone
gcloud dns managed-zones create "{{user.zone_name}}" \
  --dns-name="{{user.dns_name}}" \
  --description="{{user.description:-Managed zone for {{user.dns_name}}}}" \
  --visibility="{{user.visibility:-public}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Create private managed zone (requires VPC network)
gcloud dns managed-zones create "{{user.zone_name}}" \
  --dns-name="{{user.dns_name}}" \
  --description="{{user.description:-Private zone for {{user.dns_name}}}}" \
  --visibility="private" \
  --networks="{{user.network}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Execution — Python SDK (Fallback)

```python
# create_zone.py
import os
from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ManagedZonesClient()

zone = dns_v1.ManagedZone(
    name="{{user.zone_name}}",
    dns_name="{{user.dns_name}}",
    description="{{user.description}}",
    visibility=dns_v1.ManagedZone.Visibility.{{user.visibility:-PUBLIC}},
)

if zone.visibility == dns_v1.ManagedZone.Visibility.PRIVATE:
    zone.private_visibility_config = dns_v1.ManagedZone.PrivateVisibilityConfig(
        networks=[dns_v1.ManagedZone.PrivateVisibilityConfig.Network(
            network_url=f"https://www.googleapis.com/compute/v1/projects/{project}/global/networks/{{user.network}}"
        )]
    )

parent = f"projects/{project}"
created = client.create_managed_zone(parent=parent, managed_zone=zone)
print(f"Zone created: {created.name}")
print(f"Name servers: {created.name_servers}")
```

Execute:
```bash
pip install --quiet --user google-cloud-dns
python3 create_zone.py
```

#### Execution — JIT Go SDK (Secondary Fallback)

```go
// main.go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    "google.golang.org/api/option"
    dns "google.golang.org/api/dns/v1"
)

func main() {
    ctx := context.Background()
    svc, err := dns.NewService(ctx, option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("Failed to create DNS service: %v", err)
    }

    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    zone := &dns.ManagedZone{
        Name:        "{{user.zone_name}}",
        DnsName:     "{{user.dns_name}}",
        Description: "{{user.description}}",
        Visibility:  "{{user.visibility:-public}}",
    }

    created, err := svc.ManagedZones.Create(project, zone).Do()
    if err != nil {
        log.Fatalf("Failed to create zone: %v", err)
    }

    fmt.Printf("Zone created: %s\n", created.Name)
    fmt.Printf("Name servers: %v\n", created.NameServers)
}
```

Execute:
```bash
cd /tmp/gcp-sdk-workspace
go mod init sdk-script
go get google.golang.org/api/dns/v1
go get google.golang.org/api/option
go run ./main.go
```

#### Post-execution Validation

1. Parse `{{output.zone_name}}` from `$.name` and `{{output.name_servers}}` from `$.nameServers[]`:
```bash
gcloud dns managed-zones describe "{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name: .name, dnsName: .dnsName, nameServers: .nameServers, visibility: .visibility}'
```

2. For public zones, report name servers to user for external registrar delegation.

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|---------------|--------------|-------------|
| `invalidName / 400` | HALT | `[ERROR] Invalid DNS name format. How to fix: Ensure domain name is valid (e.g., example.com).` |
| `alreadyExists / 409` | HALT | `[ERROR] Zone already exists. How to fix: Use a different zone name or describe existing zone.` |
| `forbidden / 403` | HALT | `[ERROR] Insufficient permissions. How to fix: Grant roles/dns.admin to service account.` |
| `quotaExceeded / 429` | HALT | `[ERROR] DNS quota exceeded. How to fix: Delete unused zones or request quota increase.` |
| `serverFailure / 500` | Retry 3x, backoff | `[ERROR] Server error. Retrying...` |

### Operation: Describe Managed Zone

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Zone exists | `gcloud dns managed-zones list` with name filter | Zone in list | HALT — verify zone name |

#### Execution — CLI (`gcloud`)

```bash
gcloud dns managed-zones describe "{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Execution — Python SDK

```python
# describe_zone.py
import os
from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ManagedZonesClient()
zone_name = "{{user.zone_name}}"

name = f"projects/{project}/managedZones/{zone_name}"
zone = client.get_managed_zone(name=name)
print(f"Zone: {zone.name}, DNS: {zone.dns_name}, Visibility: {zone.visibility}")
print(f"Name servers: {zone.name_servers}")
```

#### Present to User

| Field | JSON Path | Notes |
|-------|-----------|-------|
| Name | `$.name` | Zone identifier |
| DNS Name | `$.dnsName` | Domain name |
| Visibility | `$.visibility` | `public` or `private` |
| Name Servers | `$.nameServers[]` | For public zone delegation |
| Created Time | `$.creationTime` | RFC 3339 timestamp |
| DNSSEC State | `$.dnssecConfig.state` | `on`, `off`, or `transfer` |

### Operation: List Managed Zones

#### Execution — CLI (`gcloud`)

```bash
gcloud dns managed-zones list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Filter by visibility
gcloud dns managed-zones list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="visibility=public" \
  --format="json"
```

#### Execution — Python SDK

```python
# list_zones.py
import os
from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ManagedZonesClient()
parent = f"projects/{project}"

for zone in client.list_managed_zones(parent=parent):
    print(f"Zone: {zone.name}, DNS: {zone.dns_name}, Visibility: {zone.visibility}")
```

### Operation: Update Managed Zone

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Zone exists | `gcloud dns managed-zones describe` | Zone found and `ACTIVE` | HALT — zone does not exist |
| Fields updatable | Check API docs for mutable fields | Only description, labels, DNSSEC config | HALT — immutable fields cannot be changed |

#### Execution — CLI (`gcloud`)

```bash
gcloud dns managed-zones update "{{user.zone_name}}" \
  --description="{{user.description}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Execution — Python SDK

```python
# update_zone.py
import os
from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ManagedZonesClient()
zone_name = "{{user.zone_name}}"

zone = dns_v1.ManagedZone(name=zone_name, description="{{user.description}}")
name = f"projects/{project}/managedZones/{zone_name}"
updated = client.update_managed_zone(name=name, managed_zone=zone)
print(f"Zone updated: {updated.name}")
```

### Operation: Delete Managed Zone

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of managed zone `{{user.zone_name}}` and all associated record-sets.
- **MUST NOT** proceed without clear user assent.
- **MUST** verify zone has no active changes: `gcloud dns managed-zone operations list`.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Zone exists | `gcloud dns managed-zones describe "{{user.zone_name}}"` | Zone found | HALT — zone does not exist |
| No active operations | `gcloud dns managed-zone operations list --zone="{{user.zone_name}}"` | No `PENDING` operations | HALT — wait for operations to complete |
| User confirmation | Explicit delete confirmation of `{{user.zone_name}}` | User confirms | HALT — do not proceed |

#### Execution — CLI (`gcloud`)

```bash
gcloud dns managed-zones delete "{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

#### Execution — Python SDK

```python
# delete_zone.py
import os
from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ManagedZonesClient()
zone_name = "{{user.zone_name}}"

name = f"projects/{project}/managedZones/{zone_name}"
client.delete_managed_zone(name=name)
print(f"Zone deleted: {zone_name}")
```

#### Post-execution Validation

1. Verify zone no longer exists:
```bash
gcloud dns managed-zones describe "{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" 2>&1 | grep -q "notFound" && echo "Zone deleted successfully"
```

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|---------------|--------------|-------------|
| `notFound / 404` | Already deleted | `[WARN] Zone not found — may already be deleted.` |
| `forbidden / 403` | HALT | `[ERROR] Insufficient permissions. How to fix: Grant roles/dns.admin.` |
| `badZoneState / 412` | HALT | `[ERROR] Zone is in invalid state. How to fix: Wait for active operations to complete.` |

### Operation: Create Record-Set (Transaction)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Zone exists | `gcloud dns managed-zones describe` | Zone found and `ACTIVE` | HALT — verify zone name |
| Record name valid | Validate FQDN ends with zone's `dnsName` | Valid FQDN | HALT — user provides valid record name |
| Record type valid | Check type in supported set (A, AAAA, CNAME, MX, TXT, NS, SOA, SRV, PTR, NAPTR, SPF) | Valid type | HALT — user provides valid record type |
| Data format | Validate record data matches type format | Valid data format | HALT — user provides valid data |

#### Execution — CLI (`gcloud`)

```bash
# Start transaction
gcloud dns record-sets transaction start --zone="{{user.zone_name}}"

# Add record-set to transaction
gcloud dns record-sets transaction add "{{user.record_name}}" \
  --type="{{user.record_type}}" \
  --ttl="{{user.ttl:-300}}" \
  --rrdatas="{{user.record_data}}" \
  --zone="{{user.zone_name}}"

# Execute transaction
gcloud dns record-sets transaction execute \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Execution — Python SDK

```python
# create_record.py
import os
from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ChangesClient()

zone_name = "{{user.zone_name}}"
zone_path = f"projects/{project}/managedZones/{zone_name}"

# List existing records for the same name+type to build additions
rrset = dns_v1.ResourceRecordSet(
    name="{{user.record_name}}",
    type="{{user.record_type}}",
    ttl={{user.ttl:-300}},
    rrdatas=["{{user.record_data}}"],
)

change = dns_v1.Change(additions=[rrset])
change = client.create_change(managed_zone=zone_path, change=change)
print(f"Change ID: {change.id}, Status: {change.status}")
```

#### Post-execution Validation

1. Parse `{{output.change_id}}` from `$.change.id`:
```bash
gcloud dns record-sets transaction execute \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{changeId: .change.id, status: .change.status}'
```

2. Verify record-set created:
```bash
gcloud dns record-sets describe "{{user.record_name}}" \
  --type="{{user.record_type}}" \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|---------------|--------------|-------------|
| `invalidChange / 400` | HALT | `[ERROR] Invalid DNS change. How to fix: Check record name, type, and data format.` |
| `alreadyExists / 409` | HALT or use `transaction remove` first | `[ERROR] Record-set already exists. How to fix: Use update instead or remove existing record first.` |
| `notFound / 404` | HALT | `[ERROR] Zone not found. How to fix: Verify zone name.` |
| `operationAborted / 409` | Retry 3x, backoff | `[WARN] Concurrent modification. Retrying...` |

### Operation: List Record-Sets

#### Execution — CLI (`gcloud`)

```bash
gcloud dns record-sets list \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Filter by type
gcloud dns record-sets list \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="type=A" \
  --format="json"
```

#### Execution — Python SDK

```python
# list_records.py
import os
from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ResourceRecordSetsClient()
zone_name = "{{user.zone_name}}"

parent = f"projects/{project}/managedZones/{zone_name}"
for rrset in client.list_resource_record_sets(parent=parent):
    print(f"Name: {rrset.name}, Type: {rrset.type}, TTL: {rrset.ttl}")
    for rd in rrset.rrdatas:
        print(f"  Data: {rd}")
```

### Operation: Describe Record-Set

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Zone exists | `gcloud dns managed-zones describe` | Zone found | HALT — verify zone name |
| Record exists | `gcloud dns record-sets list` with name filter | Record in list | HALT — verify record name and type |

#### Execution — CLI (`gcloud`)

```bash
gcloud dns record-sets describe "{{user.record_name}}" \
  --type="{{user.record_type}}" \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Present to User

| Field | JSON Path | Notes |
|-------|-----------|-------|
| Name | `$.name` | Record-set FQDN |
| Type | `$.type` | A, AAAA, CNAME, MX, TXT, etc. |
| TTL | `$.ttl` | Time-to-live in seconds |
| Data | `$.rrdatas[]` | Record data values |

### Operation: Delete Record-Set (Transaction)

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: deletion of record-set `{{user.record_name}}` type `{{user.record_type}}` in zone `{{user.zone_name}}`.
- **MUST** verify record exists before deletion.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Record exists | `gcloud dns record-sets describe` | Record found | HALT — record does not exist |
| User confirmation | Explicit delete confirmation | User confirms | HALT — do not proceed |

#### Execution — CLI (`gcloud`)

```bash
# Start transaction
gcloud dns record-sets transaction start --zone="{{user.zone_name}}"

# Remove record-set from transaction
gcloud dns record-sets transaction remove "{{user.record_name}}" \
  --type="{{user.record_type}}" \
  --ttl="{{user.ttl:-300}}" \
  --rrdatas="{{user.record_data}}" \
  --zone="{{user.zone_name}}"

# Execute transaction
gcloud dns record-sets transaction execute \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Execution — Python SDK

```python
# delete_record.py
import os
from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ChangesClient()
zone_name = "{{user.zone_name}}"
zone_path = f"projects/{project}/managedZones/{zone_name}"

rrset = dns_v1.ResourceRecordSet(
    name="{{user.record_name}}",
    type="{{user.record_type}}",
    ttl={{user.ttl:-300}},
    rrdatas=["{{user.record_data}}"],
)

change = dns_v1.Change(deletions=[rrset])
change = client.create_change(managed_zone=zone_path, change=change)
print(f"Change ID: {change.id}, Status: {change.status}")
```

#### Post-execution Validation

1. Verify record-set no longer exists:
```bash
gcloud dns record-sets describe "{{user.record_name}}" \
  --type="{{user.record_type}}" \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" 2>&1 | grep -q "notFound" && echo "Record deleted successfully"
```

### Operation: List Zone Operations

#### Execution — CLI (`gcloud`)

```bash
gcloud dns managed-zone operations list \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Filter by status
gcloud dns managed-zone operations list \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="status=PENDING" \
  --format="json"
```

#### Execution — Python SDK

```python
# list_operations.py
import os
from google.cloud import dns_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = dns_v1.ManagedZoneOperationsClient()
zone_name = "{{user.zone_name}}"

parent = f"projects/{project}/managedZones/{zone_name}"
for op in client.list_managed_zone_operations(parent=parent):
    print(f"Op: {op.id}, Status: {op.status}, Started: {op.start_time}")
```

### Operation: List DNS Policies

#### Execution — CLI (`gcloud`)

```bash
gcloud dns policies list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Describe specific policy
gcloud dns policies describe "{{user.policy_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

## Prerequisites

1. **Install gcloud CLI** (primary execution path):

   ```bash
   # Official installer (auto-detects OS and architecture)
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init

   # Or via apt (Linux)
   sudo apt-get install google-cloud-sdk

   # Or Homebrew (macOS)
   brew install google-cloud-sdk
   ```

2. **Bootstrap Go runtime** (for JIT SDK fallback):

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

3. **Configure Credentials**:

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
   export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
   gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
   gcloud config set project "$CLOUDSDK_CORE_PROJECT"
   ```

4. **Verify Configuration**:
   ```bash
   gcloud config list
   gcloud dns managed-zones list --limit=1 --format="json" && echo "DNS access OK"
   ```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [gcloud Usage](references/gcloud-usage.md)
- [Troubleshooting Guide](references/troubleshooting.md)
- [Monitoring & Alerts](references/monitoring.md)
- [Integration](references/integration.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)

## Operational Best Practices

- **Least privilege:** Use `roles/dns.reader` for read-only operations; `roles/dns.admin` only for write operations.
- **DNS propagation:** Set appropriate TTL values before planned changes; lower TTL (60-300s) before migrations, restore to default (3600s) after.
- **Private zones:** Bind to specific VPC networks; avoid broad network bindings for security.
- **DNSSEC:** Enable DNSSEC for public zones requiring cryptographic validation; monitor key rotation schedules.
- **Transaction batches:** Group multiple record changes into a single transaction for atomicity and efficiency.
- **Cost:** Minimize the number of managed zones; use a single zone with subdomain record-sets when possible.
- **Automation:** Use Python SDK for programmatic bulk operations; `gcloud` for interactive or single operations.

## Token Efficiency Guidelines (P0 — Mandatory)

### TE-1: API Query > Static Tables
Use `gcloud` commands to fetch zone quotas, supported record types, and DNS limits instead of hardcoding.
```bash
gcloud dns managed-zones list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

### TE-2: No docstrings in code
Inline comments only. No function-level docstring in SDK scripts.

### TE-3: Compact error tables
Single row per error code, ≤3 columns.

### TE-4: Centralized JSON paths
Declared in "API and Response Conventions" section above — not repeated per operation.

### TE-5: YAML anchors in example-config.yaml
Use `&anchor` to eliminate repeated zone/record definitions.

### TE-6: Eliminate cross-file duplication
SKILL.md has full execution flow; `references/` files detail SDK/API specifics without repeating CLI commands.

## Quality Gate (GCL)

| Classification | max_iter | Key Risk |
|----------------|:--------:|----------|
| **required** | 2 | Zone deletion and record-set deletion are irreversible destructive operations |

This skill includes delete operations (Delete Managed Zone, Delete Record-Set) that are irreversible. GCL classification is **required** with `max_iter: 2`. The Generator-Critic loop ensures safety confirmation is obtained before any destructive operation.

- **Safety dimension MUST pass**: Destructive operations must have explicit user confirmation.
- **SAFETY_FAIL triggers immediate ABORT**: No partial result if safety check fails.
- **Trace audit**: Every GCL run persists JSON trace to `./audit-results/gcl-trace-*.json`.
