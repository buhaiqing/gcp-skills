<!--
============================================================================
INSTANTIATION GUIDE — template-gcl-gate.md
============================================================================
This is a STANDALONE copy-paste template PAIR (Rubric + Prompt Templates) in ONE file.
To use it for a new product skill:

1. Split this file into two files in gcp-<product>-ops/references/:
   - rubric.md            → copy the content under "# Rubric Template"
   - prompt-templates.md  → copy the content under "# Prompt Templates Template"
2. Replace every {{...}} placeholder:
   - {{SKILL_NAME}}   → e.g. gcp-gcs-ops
   - {{PRODUCT}}      → e.g. Cloud Storage
   - {{user.*}}       → operator-supplied runtime values (ask once)
   - {{env.*}}        → never ask; read from environment
3. Fill the Per-Op Safety Sub-Rules with the product's real destructive operations
   (use {{op_1}}, {{op_2}}, {{op_3}} as placeholders for op names).
4. Keep Detection Regex, Worked Examples, Changelog, Generator/Critic/Orchestrator intact.
5. Do NOT print credentials.

Models: gcp-gcs-ops/references/rubric.md + gcp-gcs-ops/references/prompt-templates.md
============================================================================
-->

## Rubric Template

<!--
rubric_version: "1.0.0"
parent_skill: {{SKILL_NAME}}
classification: required
-->

## GCL Rubric — {{PRODUCT}}

## Core Dimensions (5)

| Dimension | Weight | Meaning | Scoring |
|-----------|--------|---------|---------|
| Correctness | 30% | Resource matches request | PASS: correct resource name/params. FAIL: wrong params |
| Safety | 30% | Destructive ops confirmed | PASS: confirmation + backup. FAIL: --quiet bypass or no confirmation |
| Idempotency | 15% | Repeatable without side effects | PASS: verify-before-create. FAIL: duplicates on retry |
| Traceability | 10% | Auditable output | PASS: command + JSON logged. FAIL: missing params |
| Spec Compliance | 15% | Follows constraints | PASS: valid config. FAIL: invalid config |

## GCP Extensions

| Extension | Scoring |
|-----------|---------|
| Resource Uniqueness | PASS: checked globally unique. FAIL: not checked |
| Path Validation | PASS: verified before mutation. FAIL: not checked |
| Encryption Consistency | PASS: matching key type. FAIL: incompatible encryption |

## Per-Op Safety Sub-Rules

### {{op_1}}
| # | Sub-Rule | Severity |
|---|----------|----------|
| 1 | {{op_1_rule_1}} | required |
| 2 | {{op_1_rule_2}} | required |
| 3 | {{op_1_rule_3}} | required |

### {{op_2}}
| # | Sub-Rule | Severity |
|---|----------|----------|
| 1 | {{op_2_rule_1}} | required |
| 2 | {{op_2_rule_2}} | required |
| 3 | {{op_2_rule_3}} | required |

### {{op_3}}
| # | Sub-Rule | Severity |
|---|----------|----------|
| 1 | {{op_3_rule_1}} | required |
| 2 | {{op_3_rule_2}} | required |

## Detection Regex

| Pattern | Detection |
|---------|-----------|
| --quiet.*delete | Dangerous quiet delete |
| {{product}}.delete | Resource delete op |
| rm -r | Force recursive delete |
| {{lock_pattern}} | Immutable state lock |

## Worked Examples

### PASS: {{op_1}} with Confirmation
```
[INFO] Resource: {{example_resource}}
WARNING: IRREVERSIBLE. All data permanently lost.
Verifying resource state...
Resource is safe to delete.
Confirm by typing: {{example_resource}}
User confirmed
gcloud {{product_cli_path}} delete {{example_resource}} --format=json
```
**Verdict: PASS**

### SAFETY_FAIL: {{op_1}} without Check
```
gcloud {{product_cli_path}} delete {{example_resource}}
```
**Verdict: SAFETY_FAIL — ABORT**

### PASS: {{op_3}} with Extreme Safety Gate
```
[INFO] Resource: {{example_resource}}
WARNING: LOCK IS PERMANENT AND IRREVERSIBLE.
To confirm permanent lock, type exactly: LOCK {{example_resource}}
User confirmed: LOCK {{example_resource}}
gcloud {{product_cli_path}} update {{example_resource}} --lock --format=json
Validated: .locked = true
```
**Verdict: PASS**

### SAFETY_FAIL: {{op_3}} without Keyword
```
User typed: yes
```
**Verdict: SAFETY_FAIL — ABORT**

## Changelog
| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | {{date}} | Initial release |

---

## Prompt Templates Template

## GCL Prompt Templates — {{PRODUCT}}

## Generator Template
Hard rules:
1. Safety gates on all destructive ops ({{op_1}}, {{op_2}}, {{op_3}})
2. Follow per-op sub-rules in references/rubric.md
3. Use env vars for credentials; NEVER output credential values
4. Use --format=json for gcloud; use product CLI for resource operations
5. Verify resource name globally unique before create
6. Verify resource safe state before delete
7. Suggest backup before destructive operations
8. EXTREME safety gate for immutable lock: user must type "LOCK" keyword + exact resource name
9. Delegate IAM ops to gcp-iam-ops, KMS to (planned), Pub/Sub to (planned)

## Critic Template
CRITICAL: Critic MUST NOT see the user's original request.

```json
{
  "dimensions": {
    "Correctness": "PASS|FAIL",
    "Safety": "PASS|FAIL|0",
    "Idempotency": "PASS|FAIL",
    "Traceability": "PASS|FAIL",
    "Spec Compliance": "PASS|FAIL"
  },
  "extensions": {
    "Resource Uniqueness": "PASS|FAIL|N/A",
    "Path Validation": "PASS|FAIL|N/A",
    "Encryption Consistency": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: --quiet.*delete, {{product}}.delete, rm -r, {{lock_pattern}}

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=2.
