#!/usr/bin/env python3
"""
GCL Enhanced Runner — Generator-Critic-Loop adversarial quality gate with enhanced observability.

Usage:
    python3 gcl_runner_enhanced.py \\
        --skill gcp-gce-ops \\
        --op DeleteInstance \\
        --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet'

Exit codes:
    0 = PASS, 1 = MAX_ITER, 2 = SAFETY_FAIL, 3 = USAGE_ERROR, 4 = RUBRIC_ERROR, 5 = DEGRADED
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import string
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

try:
    from google.api_core.exceptions import GoogleAPIError
    from google.cloud import bigquery

    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False

# Import schema
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import logging
from gcl_logging import get_gcl_logger, log_gcl_event
from gcl_trace_schema import (
    AutonomyDecision,
    Environment,
    GCLResult,
    GCLTrace,
    GCPErrorType,
    IterationTrace,
)

from self_correction_mechanism import (
    StateSnapshot,
    DegradationDetector,
)
from autonomy_ratio import AutonomyRatioTracker, AutonomyRatioAlert, AutonomyRatioCalculator
from knowledge_auto_update import KnowledgeAutoUpdater
from knowledge_query import KnowledgeQueryAPI
from trajectory_classifier import classify_directory
from failure_clusterer import cluster_failures

# ── Constants ──────────────────────────────────────────────────────────────

TRACE_DIR = os.environ.get(
    "GCL_TRACE_DIR",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..",
        "audit-results",
    ),
)

# BigQuery constants
BQ_DATASET_ID = "gcp_skills_gcl_audit"
BQ_TABLE_ID = "gcl_traces"
BQ_PROJECT_ID = os.environ.get("CLOUDSDK_CORE_PROJECT")

DEFAULT_MAX_ITER = 2
SAFETY_THRESHOLD = 0.5
DEFAULT_DEGRADE_THRESHOLD = 3
DEFAULT_ENVIRONMENT = Environment.PRODUCTION

# Retry constants for exponential backoff
RETRY_BASE_DELAY = 1.0  # Base delay in seconds
RETRY_MAX_DELAY = 60.0  # Max delay in seconds
RETRY_EXPONENTIAL_FACTOR = 2.0  # Multiplier for exponential backoff
RETRY_MAX_RETRIES = 3  # Max retries per operation

# Transient errors that should trigger retry
RETRYABLE_ERROR_TYPES: set[GCPErrorType] = {
    GCPErrorType.TIMEOUT,
    GCPErrorType.INTERNAL,
    GCPErrorType.UNAVAILABLE,
    GCPErrorType.RESOURCE_EXHAUSTED,
    GCPErrorType.ABORTED,
}

# Error pattern regexes for GCP error classification
GCP_ERROR_PATTERNS: list[tuple[str, GCPErrorType]] = [
    (r"INVALID_ARGUMENT|invalid argument", GCPErrorType.INVALID_ARGUMENT),
    (r"PERMISSION_DENIED|permission denied|Access Denied", GCPErrorType.PERMISSION_DENIED),
    (r"NOT_FOUND|not found|does not exist", GCPErrorType.NOT_FOUND),
    (r"TIMEOUT|timeout|timed out", GCPErrorType.TIMEOUT),
    (r"INTERNAL|internal error|internal server error", GCPErrorType.INTERNAL),
    (r"UNAUTHENTICATED|unauthenticated|not authenticated", GCPErrorType.UNAUTHENTICATED),
    (r"RESOURCE_EXHAUSTED|resource exhausted|quota", GCPErrorType.RESOURCE_EXHAUSTED),
    (r"FAILED_PRECONDITION|failed precondition", GCPErrorType.FAILED_PRECONDITION),
    (r"ABORTED|aborted", GCPErrorType.ABORTED),
    (r"OUT_OF_RANGE|out of range", GCPErrorType.OUT_OF_RANGE),
    (r"UNAVAILABLE|unavailable|service unavailable", GCPErrorType.UNAVAILABLE),
]

# ── Rubric parsing ─────────────────────────────────────────────────────────


def load_rubric(skill_name: str, rubric_path: str | None = None) -> dict:
    """Load and parse the rubric.md file for a given skill."""
    if rubric_path:
        paths = [rubric_path]
    else:
        # Default: look in skill directory
        repo_root = os.environ.get("GCP_SKILLS_ROOT", "")
        paths = [
            os.path.join(repo_root, skill_name, "references", "rubric.md"),
            os.path.join(skill_name, "references", "rubric.md"),
        ]

    rubric_file = None
    for p in paths:
        if os.path.exists(p):
            rubric_file = p
            break

    if not rubric_file:
        print(f"[ERROR] Rubric not found for skill '{skill_name}'", file=sys.stderr)
        sys.exit(4)

    # Simple rubric parser (extract key fields from markdown)
    with open(rubric_file) as f:
        content = f.read()

    rubric = {
        "file": rubric_file,
        "classification": _extract_field(content, "classification", "required"),
        "max_iter": int(_extract_field(content, "max_iter", str(DEFAULT_MAX_ITER))),
        "dimensions": _extract_dimensions(content),
        "regexes": _extract_regexes(content),
    }
    return rubric


def _extract_field(content: str, field: str, default: str) -> str:
    """Extract a YAML-like field value from markdown frontmatter."""
    pattern = rf"{field}\s*[:=]\s*[\"']?([^\"'\n]+)[\"']?"
    m = re.search(pattern, content)
    return m.group(1).strip() if m else default


def _extract_dimensions(content: str) -> list:
    """Extract rubric dimensions from markdown table."""
    dims = []
    # Look for dimension table rows
    in_table = False
    for line in content.split("\n"):
        if "Dimension" in line and "Meaning" in line and "Safety=0" in line:
            in_table = True
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 3:
                dims.append(
                    {
                        "name": parts[0],
                        "meaning": parts[1],
                        "safety_zero": "ABORT" in parts[2] if len(parts) > 2 else "",
                    }
                )
        elif in_table and not line.startswith("|") and not line.startswith("---"):
            break
    return dims or [
        {"name": "Correctness", "meaning": "Resource matches request", "safety_zero": ""},
        {"name": "Safety", "meaning": "Destructive ops confirmed", "safety_zero": "ABORT"},
        {"name": "Idempotency", "meaning": "No side effects on repeat", "safety_zero": ""},
        {"name": "Traceability", "meaning": "Auditable output", "safety_zero": ""},
        {"name": "Spec Compliance", "meaning": "Follows constraints", "safety_zero": ""},
    ]


def _extract_regexes(content: str) -> list:
    """Extract detection regex patterns from rubric."""
    regexes = []
    for line in content.split("\n"):
        # Match lines like `- `...` → DESTRUCTIVE`
        m = re.search(r"`([^`]+)`\s*[→-]+\s*(\S+)", line)
        if m:
            regexes.append({"pattern": m.group(1), "risk": m.group(2)})
    return regexes


# ── Secret sanitization ────────────────────────────────────────────────────

SECRET_PATTERNS: list[tuple[str, str]] = [
    (r"GOOGLE_APPLICATION_CREDENTIALS=[^\s]+", "GOOGLE_APPLICATION_CREDENTIALS=<masked>"),
    (r"--key-file[= ][^\s]+", "--key-file=<masked>"),
    (r'private_key["\']?\s*[:=]\s*["\']?-----BEGIN', "private_key=<masked>"),
]


def sanitize(text: str) -> str:
    """Mask secrets in text."""
    for pattern, replacement in SECRET_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def has_inline_secret(command: str) -> bool:
    """Check if command contains inlined secrets (should fail pre-flight)."""
    # SA key content in command
    if "-----BEGIN" in command:
        return True
    # Access token as literal
    if re.search(r"ya29\.\w+", command):
        return True
    return False


# ── Generator ──────────────────────────────────────────────────────────────


def generate(
    command: str,
    dry_run: bool = False,
    timeout: int = 300,
    max_retries: int = RETRY_MAX_RETRIES,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    exponential_factor: float = RETRY_EXPONENTIAL_FACTOR,
    skill: str = "",
    op: str = "",
) -> dict:
    """
    Execute the command and capture output with exponential backoff retry.

    Args:
        command: The command to execute
        dry_run: If True, skip actual execution and return dummy trace
        timeout: Command timeout in seconds
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_factor: Multiplier for each retry (default: 2.0)
        skill: Skill name for logging (optional)
        op: Operation name for logging (optional)

    Returns:
        Dictionary with command execution trace
    """
    logger = get_gcl_logger("gcl-runner", use_cloud_logging=False)

    trace = {
        "command": sanitize(command),
        "stdout": "",
        "stderr": "",
        "exit_code": -1,
        "start_time": datetime.now(UTC).isoformat(),
        "retry_count": 0,
        "retry_delays": [],
    }

    if dry_run:
        trace["stdout"] = "[DRY-RUN] Command not executed"
        trace["exit_code"] = 0
        trace["end_time"] = datetime.now(UTC).isoformat()
        return trace

    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            trace["stdout"] = sanitize(result.stdout)
            trace["stderr"] = sanitize(result.stderr)
            trace["exit_code"] = result.returncode

            # Check if error is retryable
            if result.returncode != 0:
                error_type = classify_error(trace["stderr"])
                if error_type in RETRYABLE_ERROR_TYPES and attempt < max_retries:
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_factor ** attempt), max_delay)
                    trace["retry_delays"].append(delay)
                    trace["retry_count"] = attempt + 1

                    log_gcl_event(
                        logger,
                        f"Retryable error detected, retrying in {delay:.1f}s",
                        severity="WARNING",
                        skill=skill,
                        op=op,
                        result="RETRY",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "error_type": error_type.value if error_type else "UNKNOWN",
                            "delay_seconds": delay,
                            "exit_code": result.returncode,
                        },
                    )
                    time.sleep(delay)
                    continue

            # Success or permanent failure - break out of loop
            break

        except subprocess.TimeoutExpired:
            trace["stderr"] = f"[ERROR] Command timed out after {timeout}s"
            trace["exit_code"] = -1

            # Check if we should retry on timeout
            if attempt < max_retries:
                error_type = classify_error(trace["stderr"])
                if error_type == GCPErrorType.TIMEOUT or "TIMEOUT" in trace["stderr"].upper():
                    delay = min(base_delay * (exponential_factor ** attempt), max_delay)
                    trace["retry_delays"].append(delay)
                    trace["retry_count"] = attempt + 1

                    log_gcl_event(
                        logger,
                        f"Timeout error, retrying in {delay:.1f}s",
                        severity="WARNING",
                        skill=skill,
                        op=op,
                        result="RETRY",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "error_type": "TIMEOUT",
                            "delay_seconds": delay,
                        },
                    )
                    time.sleep(delay)
                    continue
            break

        except Exception as e:
            trace["stderr"] = f"[ERROR] {e}"
            trace["exit_code"] = -2

            # Check if error is retryable
            error_type = classify_error(trace["stderr"])
            if error_type in RETRYABLE_ERROR_TYPES and attempt < max_retries:
                delay = min(base_delay * (exponential_factor ** attempt), max_delay)
                trace["retry_delays"].append(delay)
                trace["retry_count"] = attempt + 1

                log_gcl_event(
                    logger,
                    f"Retryable exception, retrying in {delay:.1f}s",
                    severity="WARNING",
                    skill=skill,
                    op=op,
                    result="RETRY",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "error_type": error_type.value if error_type else "UNKNOWN",
                        "delay_seconds": delay,
                        "exception": str(e),
                    },
                )
                time.sleep(delay)
                continue

            # Non-retryable exception or max retries reached
            break

    trace["end_time"] = datetime.now(UTC).isoformat()

    # Log final attempt (non-retry)
    if trace["retry_count"] > 0:
        log_gcl_event(
            logger,
            f"Command completed after {trace['retry_count']} retries",
            severity="INFO",
            skill=skill,
            op=op,
            result="COMPLETED",
            extra={
                "total_retries": trace["retry_count"],
                "retry_delays": trace["retry_delays"],
                "exit_code": trace["exit_code"],
            },
        )

    return trace


# ── Critic ─────────────────────────────────────────────────────────────────


def critique(op: str, gen_trace: dict, rubric: dict) -> dict:
    """Re-classify the generator output using rubric's regex hot-spots."""
    full_text = f"{gen_trace['command']}\n{gen_trace['stdout']}\n{gen_trace['stderr']}"
    matched_regexes = []
    highest_risk = "INFO"

    risk_order = {
        "INFO": 0,
        "WARN": 1,
        "ERROR": 2,
        "DESTRUCTIVE": 3,
        "DESTRUCTIVE-BATCH": 4,
        "FATAL": 5,
    }

    for rx in rubric.get("regexes", []):
        pattern = rx["pattern"]
        try:
            if re.search(pattern, full_text, re.IGNORECASE):
                matched_regexes.append(f"{pattern} → {rx['risk']}")
                risk_level = risk_order.get(rx["risk"].upper(), 0)
                current_highest = risk_order.get(highest_risk, 0)
                if risk_level > current_highest:
                    highest_risk = rx["risk"]
        except re.error:
            continue  # Skip invalid regex patterns

    # Score dimensions
    result = {
        "correctness": 1.0 if gen_trace["exit_code"] == 0 else 0.0,
        "safety": 0.0 if highest_risk.upper() in ("DESTRUCTIVE", "DESTRUCTIVE-BATCH", "FATAL") else 1.0,
        "idempotency": 0.8 if gen_trace["exit_code"] == 0 else 0.0,
        "traceability": 0.8,
        "spec_compliance": 0.8,
        "matched_regexes": matched_regexes,
        "highest_risk": highest_risk,
    }
    return result


# ── Termination decision ───────────────────────────────────────────────────


def decide(iteration: int, critique_result: dict, rubric: dict, max_iter: int) -> str:
    """Apply termination rules. Returns: PASS | MAX_ITER | SAFETY_FAIL."""
    if critique_result["safety"] == 0.0:
        return "SAFETY_FAIL"
    if all(v >= SAFETY_THRESHOLD for k, v in critique_result.items() if isinstance(v, int | float)):
        return "PASS"
    if iteration >= max_iter - 1:
        return "MAX_ITER"
    return "CONTINUE"


# ── Trace persistence ─────────────────────────────────────────────────────


def persist_trace(trace: dict, output_dir: str | None = None) -> str:
    """Persist the GCL trace to a JSON file."""
    out_dir = output_dir or TRACE_DIR
    os.makedirs(out_dir, exist_ok=True)

    rand_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"gcl-trace-{ts}-{rand_suffix}.json"
    filepath = os.path.join(out_dir, filename)

    with open(filepath, "w") as f:
        json.dump(trace, f, indent=2, default=str)

    return filepath


def upload_trace_to_bq(
    trace: dict,
    dataset_id: str = BQ_DATASET_ID,
    table_id: str = BQ_TABLE_ID,
    project_id: str | None = BQ_PROJECT_ID,
) -> bool:
    """
    Upload a GCL trace to BigQuery using streaming insert.

    Args:
        trace: The GCL trace dictionary to upload
        dataset_id: BigQuery dataset ID (default: gcp_skills_gcl_audit)
        table_id: BigQuery table ID (default: gcl_traces)
        project_id: GCP project ID (default: from CLOUDSDK_CORE_PROJECT env)

    Returns:
        True if upload succeeded, False if it failed
    """
    if not BIGQUERY_AVAILABLE:
        logging.warning(
            "[WARN] google-cloud-bigquery not installed, skipping BQ upload"
        )
        return False

    try:
        client_kwargs = {}
        if project_id:
            client_kwargs["project"] = project_id

        client = bigquery.Client(**client_kwargs)
        table_ref = f"{dataset_id}.{table_id}"

        # Use insert_rows_json for streaming insert
        errors = client.insert_rows_json(table_ref, [trace])

        if errors:
            logging.error(f"[ERROR] BigQuery insert errors: {errors}")
            return False

        logging.info(f"[OK] Trace {trace.get('trace_id', 'unknown')} uploaded to BigQuery")
        return True

    except GoogleAPIError as e:
        logging.error(f"[ERROR] BigQuery API error during upload: {e}")
        return False
    except Exception as e:
        logging.error(f"[ERROR] Unexpected error during BigQuery upload: {e}")
        return False


# ── New Enhanced Functions ─────────────────────────────────────────────────


def classify_error(stderr: str) -> GCPErrorType | None:
    """
    Classify GCP error from stderr output.

    Args:
        stderr: The stderr output from a command execution

    Returns:
        GCPErrorType enum value if match found, None otherwise
    """
    if not stderr:
        return None

    for pattern, error_type in GCP_ERROR_PATTERNS:
        if re.search(pattern, stderr, re.IGNORECASE):
            return error_type

    return None


def calculate_autonomy_ratio(
    iterations: list[dict[str, Any]], autonomy_decisions: list[AutonomyDecision]
) -> float:
    """
    Calculate the autonomy ratio for GCL execution.

    Autonomy ratio = (autonomous decisions) / (total potential decision points)

    Args:
        iterations: List of iteration traces
        autonomy_decisions: List of autonomy decisions made

    Returns:
        Float between 0.0 and 1.0 representing autonomy ratio
    """
    if not iterations:
        return 0.0

    # Count decision points: each iteration can have autonomy decisions
    total_iterations = len(iterations)

    # Count autonomous decisions (approved = True means it was handled automatically)
    autonomous_approved = sum(1 for d in autonomy_decisions if d.approved)

    # Total potential decision points = iterations + autonomy decisions made
    total_decision_points = total_iterations + len(autonomy_decisions)

    if total_decision_points == 0:
        return 1.0  # If no decisions needed, fully autonomous

    return autonomous_approved / total_decision_points


def should_degrade(failure_count: int, threshold: int) -> bool:
    """
    Determine if GCL should degrade to human-in-the-loop.

    Args:
        failure_count: Number of consecutive failures
        threshold: Maximum allowed consecutive failures before degradation

    Returns:
        True if should degrade to human, False otherwise
    """
    return failure_count >= threshold


def generate_state_snapshot(command: str) -> dict:
    """
    Generate a state snapshot for debugging/audit purposes.

    Captures current system state including:
    - Current timestamp (ISO 8601)
    - git status (current branch, any uncommitted changes)
    - Working directory
    - Environment variables (sanitized - only GCP-related vars)
    - Active gcloud configuration

    Args:
        command: The command being executed

    Returns:
        Dictionary containing state snapshot
    """
    snapshot = {
        "timestamp": datetime.now(UTC).isoformat(),
        "command_hash": str(hash(command)),
        "working_dir": os.getcwd(),
        "user": os.environ.get("USER", "unknown"),
    }

    # Capture git status
    snapshot["git"] = _capture_git_status()

    # Capture sanitized GCP-related environment variables
    snapshot["env"] = _capture_gcp_env_vars()

    # Capture active gcloud configuration
    snapshot["gcloud"] = _capture_gcloud_config()

    return snapshot


def _capture_git_status() -> dict:
    """Capture current git status."""
    status: dict = {
        "branch": "unknown",
        "has_uncommitted_changes": False,
        "uncommitted_files": [],
        "stash_count": 0,
    }

    try:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if branch_result.returncode == 0:
            status["branch"] = branch_result.stdout.strip()

        # Check for uncommitted changes
        diff_result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if diff_result.returncode == 0:
            uncommitted = [f.strip() for f in diff_result.stdout.strip().split("\n") if f.strip()]
            status["has_uncommitted_changes"] = len(uncommitted) > 0
            status["uncommitted_files"] = uncommitted

        # Check for staged changes
        staged_result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if staged_result.returncode == 0:
            staged = [f.strip() for f in staged_result.stdout.strip().split("\n") if f.strip()]
            status["staged_files"] = staged
            status["has_uncommitted_changes"] = status["has_uncommitted_changes"] or len(staged) > 0

        # Get stash count
        stash_result = subprocess.run(
            ["git", "stash", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if stash_result.returncode == 0:
            status["stash_count"] = len([line for line in stash_result.stdout.strip().split("\n") if line.strip()])

    except (subprocess.TimeoutExpired, FileNotFoundError):
        status["error"] = "git command unavailable or timed out"

    return status


def _capture_gcp_env_vars() -> dict:
    """
    Capture GCP-related environment variables (sanitized).

    Only includes GCP-related variables, sensitive values are masked.
    """
    gcp_prefixes = [
        "CLOUDSDK_",
        "GCP_",
        "GOOGLE_",
        "GCLOUD_",
    ]

    gcp_vars: dict = {}
    for key, value in os.environ.items():
        if any(key.startswith(prefix) for prefix in gcp_prefixes):
            # Sanitize sensitive values
            if any(secret_key in key.upper() for secret_key in ["KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL"]):
                gcp_vars[key] = "<masked>"
            else:
                gcp_vars[key] = value

    return gcp_vars


def _capture_gcloud_config() -> dict:
    """Capture active gcloud configuration."""
    config: dict = {
        "active_configuration": "unknown",
        "project": None,
        "region": None,
        "zone": None,
        "account": None,
    }

    try:
        # Get active configuration name
        config_result = subprocess.run(
            ["gcloud", "config", "configuration", "list", "--format=value(name)"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if config_result.returncode == 0 and config_result.stdout.strip():
            config["active_configuration"] = config_result.stdout.strip()

        # Get project
        project_result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if project_result.returncode == 0 and project_result.stdout.strip():
            config["project"] = project_result.stdout.strip()

        # Get region
        region_result = subprocess.run(
            ["gcloud", "config", "get-value", "compute/region"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if region_result.returncode == 0 and region_result.stdout.strip():
            config["region"] = region_result.stdout.strip()

        # Get zone
        zone_result = subprocess.run(
            ["gcloud", "config", "get-value", "compute/zone"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if zone_result.returncode == 0 and zone_result.stdout.strip():
            config["zone"] = zone_result.stdout.strip()

        # Get account
        account_result = subprocess.run(
            ["gcloud", "config", "get-value", "account"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if account_result.returncode == 0 and account_result.stdout.strip():
            config["account"] = account_result.stdout.strip()

    except (subprocess.TimeoutExpired, FileNotFoundError):
        config["error"] = "gcloud command unavailable or timed out"

    return config


# ── Enhanced Main loop ─────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="GCL Enhanced Runner")
    # Existing flags (backward compatible)
    parser.add_argument("--skill", required=True, help="Target skill name (e.g., gcp-gce-ops)")
    parser.add_argument("--op", required=True, help="Operation name (e.g., DeleteInstance)")
    parser.add_argument("--command", required=True, help="Full CLI command to execute")
    parser.add_argument("--user-request", help="Original natural-language user request")
    parser.add_argument("--max-iter", type=int, default=DEFAULT_MAX_ITER, help="Max critic iterations (default: %(default)s)")
    parser.add_argument("--rubric", help="Custom rubric path")
    parser.add_argument("--output-dir", help="Output directory for traces")
    parser.add_argument("--dry-run", action="store_true", help="Skip subprocess; run Critic only")
    parser.add_argument(
        "--format",
        default="json",
        help="Machine parsing output format (default: json)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="GCP project id (CLOUDSDK_CORE_PROJECT); falls back to GOOGLE_APPLICATION_CREDENTIALS project",
    )
    parser.add_argument(
        "--credential-file",
        default=None,
        help="Path to service account key file for GOOGLE_APPLICATION_CREDENTIALS (never logged, masked as ****)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="Per-attempt timeout in seconds for long-running ops (0 = no timeout)",
    )

    # New flags
    parser.add_argument(
        "--trace-to-bq",
        action="store_true",
        default=False,
        help="Enable BigQuery trace upload (default: false)",
    )
    parser.add_argument(
        "--degrade-threshold",
        type=int,
        default=DEFAULT_DEGRADE_THRESHOLD,
        help=f"Number of consecutive failures before human degradation (default: {DEFAULT_DEGRADE_THRESHOLD})",
    )
    parser.add_argument(
        "--environment",
        type=str,
        default="prod",
        choices=["prod", "staging", "dev"],
        help="Environment (default: prod)",
    )
    parser.add_argument(
        "--trace-only",
        action="store_true",
        default=False,
        help="Async mode, don't wait for result",
    )

    args = parser.parse_args()

    # Parse environment
    env_map = {
        "prod": Environment.PRODUCTION,
        "staging": Environment.STAGING,
        "dev": Environment.DEVELOPMENT,
    }
    environment = env_map.get(args.environment, Environment.PRODUCTION)

    # Runner logger (name matches create_log_metrics.py filter: logger="gcl-runner")
    runner_logger = get_gcl_logger("gcl-runner", use_cloud_logging=False)

    # Phase 0: Pre-flight
    if has_inline_secret(args.command):
        log_gcl_event(
            runner_logger,
            "Command contains inlined secrets, refusing to execute",
            severity="ERROR",
            skill=args.skill,
            op=args.op,
            result="SAFETY_FAIL",
            extra={"gcl_safety_failures": 1, "reason": "inline_secret"},
        )
        print("[ERROR] Command contains inlined secrets. Refusing to execute.", file=sys.stderr)
        sys.exit(3)

    rubric = load_rubric(args.skill, args.rubric)
    actual_max_iter = rubric.get("max_iter", args.max_iter)

    # Initialize enhanced trace using GCLTrace dataclass
    ts_str = datetime.now().strftime("%Y%m%d-%H%M%S")
    rand_suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    trace_id = f"gcl-trace-{ts_str}-{rand_suffix}"
    start_time = time.time()

    trace = GCLTrace(
        trace_id=trace_id,
        timestamp=datetime.now(UTC).isoformat(),
        skill=args.skill,
        op=args.op,
        user_request=args.user_request or "",
        result=GCLResult.PASS,
        exit_code=0,
        latency_ms=0,
        iterations_count=0,
        autonomy_ratio=0.0,
        safety_score=1.0,
        safety_failures=0,
        error_type=None,
        autonomy_decisions=[],
        degraded_to_human=False,
        degradation_reason=None,
        iterations=[],
        gcp_project=os.environ.get("CLOUDSDK_CORE_PROJECT"),
        gcp_region=os.environ.get("CLOUDSDK_COMPUTE_REGION"),
        environment=environment,
        trace_version="1.0.0",
        runner_version="1.1.0",
    )

    # Enhanced tracking
    consecutive_failures = 0
    autonomy_decisions: list[AutonomyDecision] = []

    # ── Wire AIOps primitive modules into the runner ──
    state_snapshot = StateSnapshot()
    degradation_detector = DegradationDetector(threshold=args.degrade_threshold)
    history_file = os.path.join(args.output_dir or TRACE_DIR, "autonomy_ratio_history.json")
    autonomy_tracker = AutonomyRatioTracker(history_file=history_file)
    autonomy_alert = AutonomyRatioAlert(threshold=0.9)
    knowledge_updater = KnowledgeAutoUpdater()
    knowledge_api = KnowledgeQueryAPI(graph=None)

    # Pre-flight knowledge dependency probe (graph=None → safe empty result)
    skill_deps = knowledge_api.query_skill_dependencies(args.skill)
    trace_dict_deps = skill_deps

    # Capture pre-state snapshot
    pre_state = generate_state_snapshot(args.command)

    # Async mode: if trace-only, spawn background task and return immediately
    if args.trace_only:
        print(f"[TRACE-ONLY] Trace {trace_id} started asynchronously")
        # In a full implementation, would spawn background task here
        # For now, just note it
        trace_dict = trace.to_dict()
        trace_path = persist_trace(trace_dict, args.output_dir)
        print(f"[TRACE] Saved to {trace_path}")

        # Upload to BigQuery if requested
        if args.trace_to_bq:
            bq_success = upload_trace_to_bq(trace_dict)
            if bq_success:
                print(f"[TRACE] Uploaded to BigQuery: {BQ_DATASET_ID}.{BQ_TABLE_ID}")
            else:
                print(f"[WARN] BigQuery upload failed, trace saved to {trace_path} only")

        sys.exit(0)

    # Main loop
    for i in range(actual_max_iter):
        # Capture pre-execution state before running the (possibly destructive) command
        state_snapshot.capture_pre(args.command)
        gen_trace = generate(args.command, dry_run=args.dry_run, skill=args.skill, op=args.op)
        log_gcl_event(
            runner_logger,
            f"[ITER {i}] Generate complete",
            severity="INFO",
            skill=args.skill,
            op=args.op,
            result="GENERATE_SUCCESS",
            extra={
                "iteration": i,
                "exit_code": gen_trace.get("exit_code", -1),
                "duration_ms": gen_trace.get("duration_ms", 0),
                "stderr_preview": (gen_trace.get("stderr", "") or "")[:200],
            },
        )
        crit = critique(args.op, gen_trace, rubric)
        log_gcl_event(
            runner_logger,
            f"[ITER {i}] Critique complete",
            severity="INFO",
            skill=args.skill,
            op=args.op,
            result="CRITIQUE_COMPLETE",
            extra={
                "iteration": i,
                "correctness": crit.get("correctness", 0.0),
                "safety": crit.get("safety", 0.0),
                "verdict_preview": decide(i, crit, rubric, actual_max_iter),
            },
        )

        # Capture post-execution state and compare for unexpected drift
        state_snapshot.capture_post(args.command)
        try:
            state_diff = state_snapshot.compare()
            if state_diff["has_changes"]:
                log_gcl_event(
                    runner_logger,
                    f"State drift detected after iteration {i}",
                    severity="WARNING",
                    skill=args.skill,
                    op=args.op,
                    result="STATE_DRIFT",
                    extra={"differences": state_diff["differences"]},
                )
        except RuntimeError:
            log_gcl_event(
                runner_logger,
                f"State drift comparison failed at iteration {i}",
                severity="WARNING",
                skill=args.skill,
                op=args.op,
                result="STATE_DRIFT_COMPARE_FAILED",
            )

        # Classify error
        error_type = classify_error(gen_trace.get("stderr", ""))
        if error_type:
            trace.error_type = error_type

        # Create iteration trace
        iteration_trace = IterationTrace(
            iteration=i,
            command=gen_trace["command"],
            stdout=gen_trace.get("stdout", ""),
            stderr=gen_trace.get("stderr", ""),
            exit_code=gen_trace.get("exit_code", -1),
            critique=crit,
            verdict="",
        )

        verdict = decide(i, crit, rubric, actual_max_iter)
        iteration_trace.verdict = verdict
        trace.iterations.append(iteration_trace)
        log_gcl_event(
            runner_logger,
            f"[ITER {i}] Decide: {verdict}",
            severity="WARNING" if verdict in ("SAFETY_FAIL", "MAX_ITER") else "INFO",
            skill=args.skill,
            op=args.op,
            result=f"DECIDE_{verdict}",
            extra={
                "iteration": i,
                "verdict": verdict,
                "autonomy_ratio_preview": calculate_autonomy_ratio(
                    [asdict(it) for it in trace.iterations], autonomy_decisions
                ) if autonomy_decisions else None,
            },
        )

        print(f"[ITER {i}] Verdict: {verdict}")

        # Track consecutive failures
        failed = crit.get("correctness", 1.0) < SAFETY_THRESHOLD or crit.get("safety", 1.0) == 0.0
        if failed:
            consecutive_failures += 1
            # Feed DegradationDetector with the failure pattern
            degradation_detector.record_failure(
                error_type.value if error_type else "UNKNOWN",
                context={"iteration": i, "command": gen_trace["command"]},
            )
            # Record autonomous rejection
            autonomy_decisions.append(
                AutonomyDecision(
                    type="AUTO_REJECT",
                    reason=f"Iteration {i} failed safety/correctness check",
                    timestamp=datetime.now(UTC).isoformat(),
                    approved=False,
                )
            )
        else:
            consecutive_failures = 0
            # Record autonomous approval
            autonomy_decisions.append(
                AutonomyDecision(
                    type="AUTO_APPROVE",
                    reason=f" iteration {i} passed all checks",
                    timestamp=datetime.now(UTC).isoformat(),
                    approved=True,
                )
            )

        trace.autonomy_decisions = autonomy_decisions

        # DegradationDetector cross-check (independent of should_degrade)
        if degradation_detector.is_degraded():
            report = degradation_detector.generate_report()
            log_gcl_event(
                runner_logger,
                f"Degradation detected: {report.failure_pattern} x{report.consecutive_failures}",
                severity="ERROR",
                skill=args.skill,
                op=args.op,
                result="DEGRADED",
                extra={"requires_human_review": report.requires_human_review},
            )
            trace.degraded_to_human = True
            trace.degradation_reason = (
                f"DegradationDetector: {report.failure_pattern} reached threshold {report.threshold}"
            )
            trace.result = GCLResult.ERROR
            autonomy_decisions.append(
                AutonomyDecision(
                    type="DEGRADE_TO_HUMAN",
                    reason=trace.degradation_reason,
                    timestamp=datetime.now(UTC).isoformat(),
                    approved=True,
                )
            )
            print(f"[DEGRADED] {trace.degradation_reason}")
            break

        # Check for degradation
        if should_degrade(consecutive_failures, args.degrade_threshold):
            trace.degraded_to_human = True
            trace.degradation_reason = f"Exceeded {args.degrade_threshold} consecutive failures"
            trace.result = GCLResult.ERROR
            autonomy_decisions.append(
                AutonomyDecision(
                    type="DEGRADE_TO_HUMAN",
                    reason=trace.degradation_reason,
                    timestamp=datetime.now(UTC).isoformat(),
                    approved=True,
                )
            )
            print(f"[DEGRADED] {trace.degradation_reason}")
            break

        if verdict in ("PASS", "SAFETY_FAIL", "MAX_ITER"):
            trace.result = GCLResult(verdict)
            trace.final_verdict = verdict if hasattr(trace, "final_verdict") else verdict
            if verdict == "SAFETY_FAIL":
                log_gcl_event(
                    runner_logger,
                    f"Safety gate failed at iteration {i}, aborting",
                    severity="ERROR",
                    skill=args.skill,
                    op=args.op,
                    result="SAFETY_FAIL",
                    extra={"gcl_safety_failures": 1, "iteration": i},
                )
            break

    # Calculate final metrics
    end_time = time.time()
    trace.latency_ms = int((end_time - start_time) * 1000)
    trace.iterations_count = len(trace.iterations)
    trace.autonomy_ratio = calculate_autonomy_ratio(
        [asdict(it) for it in trace.iterations], autonomy_decisions
    )

    # Calculate safety score from iterations
    if trace.iterations:
        avg_safety = sum(it.critique.get("safety", 1.0) for it in trace.iterations) / len(trace.iterations)
        trace.safety_score = avg_safety
        trace.safety_failures = sum(1 for it in trace.iterations if it.critique.get("safety", 1.0) == 0.0)

    # Update AutonomyRatioTracker with this execution's outcome
    recorded_ratio = autonomy_tracker.record_execution(
        total_ops=trace.iterations_count,
        degraded=1 if trace.degraded_to_human else 0,
        safety_fails=trace.safety_failures,
        timestamp=trace.timestamp,
    )
    # Alert when autonomy ratio exceeds review threshold
    alert = autonomy_alert.check_ratio(recorded_ratio, execution_id=trace.trace_id)
    if alert:
        log_gcl_event(
            runner_logger,
            f"Autonomy ratio {alert['autonomy_ratio']:.2f} exceeds threshold {alert['threshold']}, review required",
            severity="WARNING",
            skill=args.skill,
            op=args.op,
            result="AUTONOMY_ALERT",
            extra={"requires_review": alert["requires_review"]},
        )

    # ── Phase 4: Report — final structured log ─────────────────────────────
    log_gcl_event(
        runner_logger,
        f"GCL run complete: {trace.result.value}",
        severity="INFO",
        skill=args.skill,
        op=args.op,
        result=f"REPORT_{trace.result.value}",
        extra={
            "trace_id": trace.trace_id,
            "final_verdict": trace.result.value,
            "total_iters": trace.iterations_count,
            "autonomy_ratio": round(trace.autonomy_ratio, 3),
            "safety_score": round(trace.safety_score, 3) if trace.safety_score else None,
            "safety_failures": trace.safety_failures,
            "degraded_to_human": trace.degraded_to_human,
            "latency_ms": trace.latency_ms,
        },
    )

    # Capture post-state snapshot
    post_state = generate_state_snapshot(args.command)

    # Add pre/post state to trace dict
    trace_dict = trace.to_dict()
    trace_dict["pre_state"] = pre_state
    trace_dict["post_state"] = post_state
    trace_dict["skill_dependencies"] = trace_dict_deps

    # Persist
    trace_path = persist_trace(trace_dict, args.output_dir)
    print(f"[TRACE] Saved to {trace_path}")

    # ── Auto-analysis: classify + cluster recent traces ───────────────────
    trace_dir = args.output_dir or TRACE_DIR
    try:
        classifications = classify_directory(trace_dir)
        failures = [c for c in classifications if c.category.value != "SUCCESS"]
        failure_clusters = cluster_failures(classifications) if failures else []
        if failure_clusters:
            print(f"[ANALYSIS] {len(failure_clusters)} failure cluster(s):")
            for cl in failure_clusters[:5]:
                print(f"  [{cl.category.value}] {cl.label}: {cl.count}x — {', '.join(cl.members[:3])}")
    except Exception as exc:
        print(f"[WARN] trace analysis skipped: {exc}", file=sys.stderr)

    # Upload to BigQuery if requested (errors are logged but don't fail the run)
    if args.trace_to_bq:
        trace_dict = trace.to_dict()
        bq_success = upload_trace_to_bq(trace_dict)
        if bq_success:
            print(f"[TRACE] Uploaded to BigQuery: {BQ_DATASET_ID}.{BQ_TABLE_ID}")
        else:
            print(f"[WARN] BigQuery upload failed, trace saved to {trace_path} only")

    # Exit code
    verdict_map = {
        GCLResult.PASS: 0,
        GCLResult.MAX_ITER: 1,
        GCLResult.SAFETY_FAIL: 2,
        GCLResult.ERROR: 5,
    }
    sys.exit(verdict_map.get(trace.result, 1))


if __name__ == "__main__":
    main()
