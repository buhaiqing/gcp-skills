# GCL Structured Logging — Cloud Logging Integration

This document describes the structured logging system for the Generator-Critic-Loop (GCL) adversarial quality gate, including Cloud Logging (GCP) integration.

---

## Overview

The GCL logging module provides **structured JSON logging** with native **Google Cloud Logging** integration. Logs are formatted as JSON objects with consistent fields for easy querying and analysis in GCP Console and BigQuery.

---

## Quick Start

```python
from gcl_logging import get_gcl_logger, log_gcl_event

# Get a structured logger
logger = get_gcl_logger("gcl-runner")

# Log a GCL event
log_gcl_event(
    logger,
    "GCL iteration completed",
    severity="INFO",
    skill="gcp-gce-ops",
    op="DeleteInstance",
    result="PASS",
    latency_ms=1234,
    autonomy_ratio=0.75,
)

# Or use logger directly with extra fields
logger.info("GCL loop finished", extra={
    "result": "PASS",
    "latency_ms": 500,
    "autonomy_ratio": 0.8,
})
```

---

## Log Format

Each log entry contains the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 format (e.g., `2026-07-18T14:30:52+00:00`) |
| `severity` | string | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `logger` | string | Logger name (e.g., `gcl-runner`, `gcl-generator`) |
| `message` | string | Human-readable log message |
| `trace_id` | string | Unique trace ID for the GCL run (format: `gcl-trace-YYYYMMDD-HHMMSS-xxxxxx`) |
| `skill` | string | Skill name (e.g., `gcp-gce-ops`) |
| `op` | string | Operation name (e.g., `DeleteInstance`) |
| `result` | string | GCL result: `PASS`, `FAIL`, `MAX_ITER`, `SAFETY_FAIL`, `ERROR`, `SKIPPED` |
| `latency_ms` | int | Operation latency in milliseconds |
| `autonomy_ratio` | float | Autonomy ratio (0.0 - 1.0) |
| `extra` | object | Additional custom fields |

### Example Log Entry

```json
{
  "timestamp": "2026-07-18T14:30:52+00:00",
  "severity": "INFO",
  "logger": "gcl-runner",
  "message": "GCL iteration completed",
  "trace_id": "gcl-trace-20260718-143052-abc123",
  "skill": "gcp-gce-ops",
  "op": "DeleteInstance",
  "result": "PASS",
  "latency_ms": 1234,
  "autonomy_ratio": 0.75,
  "extra": {}
}
```

---

## Log Severity Levels

| Level | Use Case |
|-------|----------|
| `DEBUG` | Detailed debugging information, regex matches, intermediate decisions |
| `INFO` | Normal operation flow, iteration start/complete, final verdicts |
| `WARNING` | Non-critical issues (e.g., missing optional rubric fields, retries) |
| `ERROR` | Operation failures, exceptions, non-safety-critical errors |
| `CRITICAL` | Safety failures, credential leaks detected, abort conditions |

### When to Use Each Level

- **INFO**: GCL loop started, iteration complete, final verdict reached
- **WARNING**: Missing rubric fields (using defaults), retries attempted
- **ERROR**: Command execution failed, rubric parse error, timeout
- **CRITICAL**: Safety check failed (destructive op unconfirmed), secret detected in command

---

## Cloud Logging Integration

### Prerequisites

1. **Install the Google Cloud Logging library**:
   ```bash
   pip install google-cloud-logging
   ```

2. **Set up credentials** (one of):
   - Service Account key file: `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json`
   - Application Default Credentials: `gcloud auth application-default login`

3. **Set GCP project**:
   ```bash
   export CLOUDSDK_CORE_PROJECT=your-project-id
   ```

### Automatic Integration

Cloud Logging is enabled by default when:
- `google-cloud-logging` package is installed
- `GOOGLE_APPLICATION_CREDENTIALS` or ADC is configured
- `CLOUDSDK_CORE_PROJECT` environment variable is set

### Disable Cloud Logging

```python
logger = get_gcl_logger("gcl-runner", use_cloud_logging=False)
```

### Resource Type

Logs are written to Cloud Logging with the resource type `gcp_skills_gcl` and labels:
- `project_id`: Your GCP project ID
- `environment`: `development` (or `GCP_SKILLS_ENV` env var value)

---

## Error Classification

The module provides error classification helpers for GCP errors:

```python
from gcl_logging import classify_gcp_error, classify_result, GCLErrorType, GCLResult

# Classify a GCP error message
error_type = classify_gcp_error("PERMISSION_DENIED: Access denied")
# Returns: GCLErrorType.PERMISSION_DENIED

# Classify a GCL result
result = classify_result(exit_code=1, stderr="PERMISSION_DENIED: Access denied", error_type=error_type)
# Returns: GCLResult.SAFETY_FAIL
```

### Supported GCP Error Types

| Error Type | Description |
|------------|-------------|
| `INVALID_ARGUMENT` | Bad request, invalid parameters |
| `PERMISSION_DENIED` | Access denied, insufficient permissions |
| `NOT_FOUND` | Resource does not exist |
| `TIMEOUT` | Operation timed out |
| `INTERNAL` | GCP internal error |
| `UNAUTHENTICATED` | Not authenticated |
| `RESOURCE_EXHAUSTED` | Quota exceeded, rate limited |
| `FAILED_PRECONDITION` | Precondition not met |
| `ABORTED` | Operation aborted, conflict |
| `OUT_OF_RANGE` | Value out of range |
| `UNAVAILABLE` | Service unavailable |
| `UNKNOWN` | Unclassified error |

### GCL Result Types

| Result | Description |
|--------|-------------|
| `PASS` | Operation succeeded, all rubric dimensions met threshold |
| `FAIL` | Operation failed |
| `MAX_ITER` | Reached maximum iterations without passing |
| `SAFETY_FAIL` | Safety check failed (destructive op unconfirmed) |
| `ERROR` | Execution error (timeout, exception) |
| `SKIPPED` | Operation skipped |

---

## Querying Logs in GCP Console

### Filter by Severity

```
severity >= "ERROR"
```

### Filter by Skill and Operation

```
resource.type="gcp_skills_gcl"
resource.labels.project_id="your-project-id"
jsonPayload.skill="gcp-gce-ops"
jsonPayload.op="DeleteInstance"
```

### Filter by Result

```
jsonPayload.result="FAIL"
```

### Filter by Trace ID

```
jsonPayload.trace_id="gcl-trace-20260718-143052-abc123"
```

### Filter by Time Range

```
timestamp >= "2026-07-18T00:00:00Z"
timestamp <= "2026-07-19T00:00:00Z"
```

### Complex Query Example

Find all SAFETY_FAIL results for GCE operations in the last hour:

```
resource.type="gcp_skills_gcl"
jsonPayload.skill="gcp-gce-ops"
jsonPayload.result="SAFETY_FAIL"
timestamp >= "2026-07-18T13:00:00Z"
```

### Export Logs to BigQuery

1. In GCP Console, go to **Logging** → **Log Router**
2. Create a sink to BigQuery dataset
3. Use SQL to analyze GCL performance:

```sql
SELECT
  jsonPayload.skill,
  jsonPayload.op,
  jsonPayload.result,
  AVG(CAST(jsonPayload.latency_ms AS INT64)) as avg_latency_ms,
  AVG(CAST(jsonPayload.autonomy_ratio AS FLOAT64)) as avg_autonomy_ratio,
  COUNT(*) as count
FROM `project.dataset.gcp_skills_gcl`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY jsonPayload.skill, jsonPayload.op, jsonPayload.result
ORDER BY count DESC
```

---

## Trace ID Management

Each GCL run gets a unique trace ID for correlation:

```python
from gcl_logging import set_trace_id, reset_trace_id, _get_or_create_trace_id

# Set a custom trace ID
set_trace_id("custom-trace-123")

# Get current trace ID
trace_id = _get_or_create_trace_id()

# Reset for new GCL run
reset_trace_id()
```

---

## API Reference

### `get_gcl_logger(name, level, *, use_cloud_logging, project_id, resource_type, resource_labels)`

Create or get a structured GCL logger.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | Logger name (e.g., `"gcl-runner"`) |
| `level` | `int` | `logging.INFO` | Logging level |
| `use_cloud_logging` | `bool` | `True` | Enable Cloud Logging handler |
| `project_id` | `str` | `CLOUDSDK_CORE_PROJECT` env | GCP project ID |
| `resource_type` | `str` | `"gcp_skills_gcl"` | Cloud Logging resource type |
| `resource_labels` | `dict` | auto | Resource labels |

### `log_gcl_event(logger, message, severity, *, skill, op, result, latency_ms, autonomy_ratio, **extra)`

Log a GCL event with structured fields.

### `classify_gcp_error(error_message) -> GCLErrorType`

Classify a GCP error from error message or stderr.

### `classify_result(exit_code, stderr, error_type) -> GCLResult`

Classify GCL operation result from exit code and error info.

---

## Security Notes

- **Never log credentials**: The logging module masks `GOOGLE_APPLICATION_CREDENTIALS` paths and private keys
- **Audit access**: Cloud Logging access is controlled by IAM; ensure only authorized personnel can read logs
- **Log retention**: Configure log retention policy per your compliance requirements

---

## Troubleshooting

### Cloud Logging not working

1. Verify credentials: `gcloud auth application-default print-access-token`
2. Check project ID: `echo $CLOUDSDK_CORE_PROJECT`
3. Verify API enabled: `gcloud services list --enabled | grep logging`

### Logs not appearing in GCP Console

1. Check log router sinks and filters
2. Verify resource type matches query (`gcp_skills_gcl`)
3. Check time range filter

### Import errors

Ensure `google-cloud-logging` is installed:
```bash
pip install google-cloud-logging
```

The module gracefully falls back to console-only logging if the Cloud Logging library is not installed.
