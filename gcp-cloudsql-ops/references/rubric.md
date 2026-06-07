---
rubric_version: "1.0.0"
parent_skill: gcp-cloudsql-ops
classification: required
---

# GCL Rubric — Cloud SQL

## Core Dimensions (5)

| Dimension | Weight | Meaning | Scoring |
|-----------|--------|---------|---------|
| Correctness | 30% | Resource matches request | PASS: correct name/type/region. FAIL: wrong params |
| Safety | 30% | Destructive ops confirmed | PASS: confirmation + backup. FAIL: --quiet bypass |
| Idempotency | 15% | Repeatable without side effects | PASS: verify-before-create. FAIL: duplicates on retry |
| Traceability | 10% | Auditable output | PASS: command + JSON logged. FAIL: missing params |
| Spec Compliance | 15% | Follows constraints | PASS: valid DB version/tier/region. FAIL: invalid config |

## GCP Extensions

| Extension | Scoring |
|-----------|---------|
| Password Handling | PASS: uses MYSQL_PWD/PGPASSWORD env vars. FAIL: CLI -p flag |
| Quota Awareness | PASS: checked. FAIL: blind create |
| Connectivity Validation | PASS: verified after create. FAIL: not checked |

## Per-Op Safety Sub-Rules

### Delete Instance
| # | Sub-Rule | Severity |
|---|----------|----------|
| 1 | User types exact instance name | required |
| 2 | Suggest final backup before delete | required |
| 3 | Warn all data permanently deleted | required |

### Delete Database
| # | Sub-Rule | Severity |
|---|----------|----------|
| 1 | User types exact database name | required |
| 2 | Warn data permanently lost | required |

### Restore Backup
| # | Sub-Rule | Severity |
|---|----------|----------|
| 1 | Warn restore overwrites current data | required |
| 2 | User types exact instance name | required |
| 3 | Verify backup exists before restore | required |

### Promote Replica
| # | Sub-Rule | Severity |
|---|----------|----------|
| 1 | Warn breaks replication relationship | required |
| 2 | Confirm source instance name | required |
| 3 | Verify replica is not a standalone instance | required |

### Import Database
| # | Sub-Rule | Severity |
|---|----------|----------|
| 1 | Warn import may overwrite existing data | required |
| 2 | Verify GCS import file exists | required |
| 3 | Check GCS read permissions | required |

### Create User (Password)
| # | Sub-Rule | Severity |
|---|----------|----------|
| 1 | NEVER use -p flag for local DB client | required |
| 2 | Use MYSQL_PWD or PGPASSWORD env var | required |
| 3 | Password in gcloud --password is okay (API transport) | recommended |

## Detection Regex

| Pattern | Detection |
|---------|-----------|
| --quiet.*delete | Dangerous quiet delete |
| sql.*instances.*delete | Instance delete op |
| sql.*databases.*delete | Database delete op |
| sql.*backups.*restore | Backup restore op |
| promote-replica | Replica promotion |
| -p[PASSWORD] | Unsafe password in CLI |
| PGPASSWORD=" | Safe password env var (PG) |
| MYSQL_PWD=" | Safe password env var (MySQL) |

## Worked Examples

### PASS: Delete with Confirmation
```
[INFO] Instance: my-prod-db (region: us-central1)
WARNING: IRREVERSIBLE. All databases, backups, and data will be permanently deleted.
Confirm by typing: my-prod-db
User confirmed
Final backup created before deletion
gcloud sql instances delete my-prod-db --format=json
```
**Verdict: PASS**

### PASS: User Creation with Safe Password
```
[INFO] Creating user: myapp
gcloud sql users create myapp --instance=my-prod-db --password=**** --format=json
[INFO] For local DB connections, use:
  MYSQL_PWD="<password>" mysql -u myapp -h <host> -D <database>
```
**Verdict: PASS**

### SAFETY_FAIL: Delete with --quiet
```
gcloud sql instances delete my-prod-db --quiet
```
**Verdict: SAFETY_FAIL — ABORT**

### SAFETY_FAIL: Password in CLI Flag
```
mysql -u myapp -p"MyPassw0rd!" -h my-prod-db
```
**Verdict: SAFETY_FAIL — ABORT**

## Changelog
| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release |