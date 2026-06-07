# User Experience Specification — GCP Skill Generator

> **Purpose:** Defines user experience (UX) requirements and design patterns that MUST be integrated into every generated `gcp-[product]-ops` skill.
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07
> **Status:** MANDATORY — all generated skills MUST pass UX review against this spec

---

## Table of Contents

1. [UX Design Principles](#1-ux-design-principles)
2. [Onboarding & Guidance](#2-onboarding--guidance)
3. [Interaction Design](#3-interaction-design)
4. [Feedback Mechanisms](#4-feedback-mechanisms)
5. [Error Handling & Recovery](#5-error-handling--recovery)
6. [UX Patterns Library](#6-ux-patterns-library)

---

## 1. UX Design Principles

### 1.1 Core Principles

| Principle | Description | Success Criteria |
|-----------|-------------|------------------|
| **Clarity** | Every action and its consequence is unambiguous | User never wonders "what just happened?" |
| **Efficiency** | Common tasks require minimal steps | 80% of tasks complete in ≤ 3 prompts |
| **Forgiveness** | Mistakes are recoverable with clear guidance | Non-destructive errors have clear recovery paths |
| **Consistency** | Patterns are uniform across all gcp skills | User learns once, applies everywhere |
| **Transparency** | System state is always visible | User always knows what the system is doing |

### 1.2 UX Maturity Model

| Level | Name | Characteristics |
|-------|------|-----------------|
| 1 | Functional | Skill works; minimal UX consideration |
| 2 | Usable | Basic guidance; clear error messages |
| 3 | Comfortable | Onboarding flow; consistent patterns; helpful defaults |
| 4 | Delightful | Anticipates needs; proactive suggestions; minimal friction |
| 5 | Intuitive | Feels like natural conversation; zero learning curve |

**Target:** All generated skills MUST achieve **Level 3 (Comfortable)** minimum.

---

## 2. Onboarding & Guidance

### 2.1 Quick Start Requirement

Every SKILL.md MUST include a Quick Start section that enables first-timers to run their first command within 60 seconds.

**Minimal Quick Start:**
```markdown
## Quick Start

### What This Skill Does
This skill enables you to manage [Product Name] resources.

### Prerequisites
- [ ] gcloud CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `CLOUDSDK_CORE_PROJECT`

### Verify Setup
```bash
gcloud config get-value project
```

### Your First Command
```bash
gcloud [product] [resources] list --format="json"
```
```

---

## 3. Interaction Design

### 3.1 Prompt Requirements

| Operation | Max Prompts | Smart Defaults |
|-----------|-------------|----------------|
| Create | ≤ 2 required fields | Use `{{user.resource_name}}-$(date +%s)` for names |
| Describe | ≤ 1 (resource name) | List resources if name not provided |
| Modify | ≤ 2 (resource + changed field) | Show current config first |
| Delete | ≤ 1 (confirmation) | Resource name/ID required for confirmation |
| List | ≤ 0 (auto-execute) | Use env project/zone defaults |

### 3.2 Confirmation for Destructive Operations

DELETE, DROP, TERMINATE, RELEASE, and similar operations MUST:

1. Display complete resource identification (name, ID, location)
2. State the operation is irreversible
3. Require user to explicitly confirm with the resource identifier
4. NOT use `--quiet` as a substitute for the safety gate

**Correct Pattern:**
```
🔴 WARNING: This will irreversibly DELETE resource "my-instance" (us-central1-a).

To proceed, type the resource name: my-instance

✅ Confirmed. Executing delete...
```

---

## 4. Feedback Mechanisms

### 4.1 Success Messages

```text
✅ Resource "my-instance" created successfully.
   • Name: my-instance
   • Zone: us-central1-a
   • Status: RUNNING
   • Created: 2026-06-07T10:00:00Z
```

### 4.2 Progress for Long Operations (> 5s)

```text
⏳ Creating instance "my-instance"... (this may take up to 60s)
   Operation: https://compute.googleapis.com/.../operations/xxx
```

### 4.3 Error Messages Format

Standardized `[ERROR]` format:
```text
[ERROR] {code}: {summary}

What happened:
{explanation}

How to fix:
{remediation}

Next step:
{next_action}
```

---

## 5. Error Handling & Recovery

| Scenario | Agent Action | UX Output |
|----------|-------------|-----------|
| QUOTA_EXCEEDED | HALT | `[ERROR] QUOTA_EXCEEDED: ... How to fix: ...` |
| PERMISSION_DENIED | HALT | `[ERROR] PERMISSION_DENIED: ... How to fix: ...` |
| Rate limited | Retry 3x, exponential backoff | `⚠️ Rate limit hit. Retrying in {s}s...` |
| Network timeout | Retry 3x | `⚠️ Connection timeout. Retrying...` |
| Resource not found | HALT | `[ERROR] NOT_FOUND: ... How to fix: ...` |

---

## 6. UX Patterns Library

### Pattern: Pre-Flight Check Table

```markdown
| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Project | `gcloud config get-value project` | Non-empty | HALT — set CLOUDSDK_CORE_PROJECT |
| Auth | `gcloud auth print-access-token` | Non-empty | HALT — authenticate SA |
| Quota | `gcloud compute regions describe` | Sufficient | HALT — request increase |
```

### Pattern: Confirmation Template (Destructive)

```markdown
#### Confirmation Required
- Resource: {{user.resource_name}}
- Type: [Resource Type]
- Location: {{user.zone}}/{{user.region}}
- Action: **DELETE (irreversible)**

You must confirm by providing the exact resource name:
> Type resource name to confirm: _______________
```

### Pattern: Standardized Error Format

```markdown
| Error Code | Summary | Explanation | Remediation | Next Step |
|------------|---------|-------------|-------------|-----------|
| QUOTA_EXCEEDED | Resource quota limit | Project has reached max resources | Delete unused or raise quota | Check quotas in Console |
```