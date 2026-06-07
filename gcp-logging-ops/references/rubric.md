---
name: logging-ops-rubric
description: GCL scoring rubric for Cloud Logging operations
classification: recommended
gcl_max_iter: 3
---

# Rubric — Cloud Logging (GCL)

## Core Dimensions (5)

| Dimension | Weight | Max | Meaning |
|-----------|--------|-----|---------|
| **Correctness** | 30% | 10 | Filter matches expected logs, resources correctly identified |
| **Safety** | 30% | 10 | Delete operations confirmed, _Required/_Default buckets protected |
| **Idempotency** | 15% | 10 | Repeated calls produce same result |
| **Traceability** | 10% | 10 | Commands, params, and responses recorded |
| **Spec Compliance** | 15% | 10 | Follows core-concepts.md constraints |

## GCP Extensions (3 additional dimensions, bonus)

| Dimension | Max | Scoring Criteria |
|-----------|-----|------------------|
| Log Query Accuracy | 5 | Filter returns expected entries, no false positives |
| Bucket Retention Validation | 5 | Retention days are honored after update |
| Sink Delivery Validation | 5 | Log entries reach destination within expected time |

## Per-Op Safety Sub-Rules

| Operation | Safety Rule |
|-----------|-------------|
| Delete Log Bucket | User types name → confirm; warn about _Required/_Default buckets; check for referencing sinks |
| Delete Log View | User types name → confirm |
| Delete Log Sink | User types name → confirm; show destination/filter; warn about export impact |
| Delete Log Metric | User types name → confirm; note monitoring dependencies |
| Update Retention | Warn: retention decrease may cause data loss |

## Detection Regex

```
delete|drop|remove|erase|purge
```

## Worked Examples

### PASS — Create Log Sink

**Request:** Create sink exporting ERROR logs to BigQuery

**G Actions:**
1. Pre-flight: Check project, auth, API enabled, destination exists
2. Execute: `gcloud logging sinks create error-sink "bigquery.googleapis.com/projects/P/datasets/D" --log-filter="severity>=ERROR" --format=json`
3. Verify: Describe sink, extract writerIdentity, verify destination IAM
4. Report: sink name, destination, filter, writer identity

**C Score:** Correctness=10, Safety=10 (no destructive op), Idempotency=10, Traceability=9, Spec Compliance=10

### SAFETY_FAIL — Delete _Required Bucket

**Request:** Delete log bucket "_Required"

**G Actions:**
1. Pre-flight: User confirms bucket name "_Required"
2. HALT: `_Required` bucket is protected, cannot be deleted
3. Report: Safety score 0, abort execution

**Verdict:** ABORT — Safety=0, no partial result