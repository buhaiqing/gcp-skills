# gcloud CLI Behavioral Reference

> **Purpose:** Verified behavioral notes and invocation patterns for the `gcloud` CLI, derived from official reference documentation. Every generated skill MUST follow these conventions.
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07

---

## Table of Contents

1. [Default Output is Human-Readable](#1-default-output-is-human-readable)
2. [--format Flag for Machine Output](#2---format-flag-for-machine-output)
3. [Credentials and Auth](#3-credentials-and-auth)
4. [Project Configuration](#4-project-configuration)
5. [Common Invocation Patterns](#5-common-invocation-patterns)
6. [Common Mistakes to Avoid](#6-common-mistakes-to-avoid)

---

## 1. Default Output is Human-Readable

The `gcloud` CLI's default output is **human-readable formatted text** (spaces/tables). Unlike `aliyun`, you MUST use `--format=json` for machine-parseable output:

```bash
# Human-readable (default) — NOT for agent execution
gcloud compute instances list

# Machine-parseable — ALWAYS use this for agent
gcloud compute instances list --format="json"
```

**Fix for generated skills:** ALWAYS append `--format="json"` to gcloud commands that need structured output.

---

## 2. --format Flag for Machine Output

`gcloud` supports multiple output formats:

| Format | Use Case | Example |
|--------|----------|---------|
| `json` | Full structured output | `--format="json"` |
| `yaml` | YAML output | `--format="yaml"` |
| `table(...)` | Tabular output | `--format="table(name,status)"` |
| `json` + `jq` | Field extraction | `gcloud ... --format="json" \| jq -r '.items[].name'` |
| `value(...)` | Single value | `--format="value(name)"` |
| `flattened` | Flat key-value | `--format="flattened"` |

**Recommended pattern for agent execution:**
```bash
# Full JSON for complex operations
gcloud compute instances describe "instance-name" --zone=us-central1-a --format="json"

# jq for field extraction
gcloud compute instances describe "instance-name" --zone=us-central1-a --format="json" | jq -r '.status'

# value() for single field
gcloud config get-value project --format="value(core.project)"
```

---

## 3. Credentials and Auth

### Service Account (Preferred for Automation)

```bash
# Via environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"

# Or via gcloud command
gcloud auth activate-service-account --key-file="/path/to/key.json"
```

### Application Default Credentials (ADC)

```bash
gcloud auth application-default login
```

### Access Token

```bash
export CLOUDSDK_AUTH_ACCESS_TOKEN=$(gcloud auth application-default print-access-token)
```

---

## 4. Project Configuration

```bash
# Via environment variable (recommended for agent)
export CLOUDSDK_CORE_PROJECT="my-project"

# Via gcloud config
gcloud config set project my-project

# Read current project
gcloud config get-value project
```

---

## 5. Common Invocation Patterns

### List Resources
```bash
gcloud [service] [resources] list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Describe Resource
```bash
gcloud [service] [resources] describe "{{user.resource_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --zone="{{user.zone}}" \
  --format="json"
```

### Create Resource
```bash
gcloud [service] [resources] create "{{user.resource_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --zone="{{user.zone}}" \
  --format="json"
```

### Update Resource
```bash
gcloud [service] [resources] update "{{user.resource_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --[flag]="[value]" \
  --format="json"
```

### Delete Resource
```bash
gcloud [service] [resources] delete "{{user.resource_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --zone="{{user.zone}}" \
  --quiet
```

> **Note:** `--quiet` suppresses interactive prompts. Use with caution — the safety gate should happen BEFORE this command, not during.

### Long-Running Operations

Many gcloud create/update/delete commands are **synchronous** by default — they block until the operation completes:

```bash
# This command waits for operation to finish
gcloud compute instances create "instance-name" --zone=us-central1-a

# Use --async for non-blocking (returns operation ID)
gcloud compute instances create "instance-name" --zone=us-central1-a --async
```

For operations that support `--async`, poll with:
```bash
gcloud compute operations describe "operation-name" --zone=us-central1-a --format="json" | jq -r '.status'
```

### Filtering Lists

```bash
# Filter by label
gcloud compute instances list \
  --filter="labels.env=prod" \
  --format="json"

# Filter by status
gcloud compute instances list \
  --filter="status=RUNNING" \
  --format="json"
```

---

## 6. Common Mistakes to Avoid

### Mistake 1: Expecting Default JSON Output
```bash
# WRONG: default output is human-readable
gcloud compute instances list

# CORRECT: add --format="json"
gcloud compute instances list --format="json"
```

### Mistake 2: Using `--output json` (AWS-style)
```bash
# WRONG: gcloud uses --format, not --output
gcloud compute instances list --output json

# CORRECT:
gcloud compute instances list --format="json"
```

### Mistake 3: Hardcoding Project
```bash
# WRONG: Hardcoded project
gcloud compute instances list --project=my-project

# CORRECT: Use env placeholder
gcloud compute instances list --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Mistake 4: Missing Zone for Zonal Resources
```bash
# WRONG: Zone required but missing
gcloud compute instances describe "instance-name"

# CORRECT:
gcloud compute instances describe "instance-name" --zone="us-central1-a"
```

### Mistake 5: Using `--quiet` as Safety Gate
```bash
# WRONG: --quiet bypasses all safety prompts
gcloud compute instances delete "instance-name" --quiet

# CORRECT: Safety gate BEFORE the command
## Pre-flight: user confirms deletion
gcloud compute instances delete "instance-name" --quiet
```

---

## See Also

- [Google Cloud SDK Documentation](https://cloud.google.com/sdk/docs)
- [gcloud CLI Cheat Sheet](https://cloud.google.com/sdk/docs/cheatsheet)
- [Execution Environment Setup](execution-environment.md)