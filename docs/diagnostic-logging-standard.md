# Diagnostic Logging Standard (MANDATORY for data-plane ops)

> **Purpose:** Standardized log format for all scripts executed via remote channels.
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07

---

All scripts executed via remote channels MUST use a consistent log format:

```
[HH:MM:SS] [PHASE] key=value
```

## Log Phase Prefix

| PHASE | Meaning | Example |
|-------|---------|---------|
| `DIAG` | Diagnostic info / environment snapshot | `[DIAG] PHASE=env-snapshot` |
| `INSTALL` | Installation process | `[INSTALL] method=apt` |
| `EXEC` | Command being executed | `[EXEC] gcloud compute instances list --format=json` |
| `RESULT` | Key result key-value pairs | `[RESULT] GCLOUD_INSTALL=SUCCESS` |
| `WARN` | Warning | `[WARN] gcloud version outdated` |
| `ERROR` | Error classification | `[ERROR] TYPE=AUTH_FAILED FIX=Check SA key path` |
| `SUMMARY` | Final summary | `[SUMMARY] Status=READY` |

## Error Classification

```
[ERROR] TYPE={category} FIX={one-line action}
```

| ERROR TYPE | Meaning | FIX |
|------------|---------|-----|
| `AUTH_FAILED` | SA key missing or invalid | Check GOOGLE_APPLICATION_CREDENTIALS path |
| `PERMISSION_DENIED` | IAM permission missing | Grant required IAM role |
| `QUOTA_EXCEEDED` | Resource quota limit | Request quota increase |
| `NOT_FOUND` | Resource does not exist | Verify resource name |
| `TIMEOUT` | Network timeout | Check network or increase timeout |
| `UNSUPPORTED_ARCH` | Architecture not supported | Use Docker gcloud |

## Exit Code Convention

| ExitCode | Meaning | Agent Action | Human Intervention |
|:--------:|---------|-------------|:------------------:|
| 0 | Success | Read SUMMARY and return | No |
| 10-19 | Environment check failed | Auto-remediation (e.g., install) | No |
| 20-29 | Installation failed | Output diagnostic info | Yes |
| 30-39 | Network issue | Output DNS/connection diagnostics | Yes |
| 40-49 | Command execution failed | Output `[ERROR] TYPE=... FIX=...` | Yes |