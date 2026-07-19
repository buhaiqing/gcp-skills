#!/usr/bin/env python3
"""
GCL Runner — Generator-Critic-Loop adversarial quality gate.

Usage:
    python3 gcl_runner.py \\
        --skill gcp-gce-ops \\
        --op DeleteInstance \\
        --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet'

Exit codes:
    0 = PASS, 1 = MAX_ITER, 2 = SAFETY_FAIL, 3 = USAGE_ERROR, 4 = RUBRIC_ERROR
"""

import argparse
import json
import os
import random
import re
import string
import subprocess
import sys
from datetime import UTC, datetime

# ── Constants ──────────────────────────────────────────────────────────────

TRACE_DIR = os.environ.get(
    "GCL_TRACE_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "audit-results")
)

DEFAULT_MAX_ITER = 2
SAFETY_THRESHOLD = 0.5

# ── Rubric parsing ─────────────────────────────────────────────────────────


def load_rubric(skill_name: str, rubric_path: str = None) -> dict:
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
        # Match lines like `- \`...\` → DESTRUCTIVE`
        m = re.search(r"`([^`]+)`\s*[→-]+\s*(\S+)", line)
        if m:
            regexes.append({"pattern": m.group(1), "risk": m.group(2)})
    return regexes


# ── Secret sanitization ────────────────────────────────────────────────────

SECRET_PATTERNS = [
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


def generate(command: str, dry_run: bool = False, timeout: int = 300) -> dict:
    """Execute the command and capture output."""
    trace = {
        "command": sanitize(command),
        "stdout": "",
        "stderr": "",
        "exit_code": -1,
        "start_time": datetime.now(UTC).isoformat(),
    }

    if dry_run:
        trace["stdout"] = "[DRY-RUN] Command not executed"
        trace["exit_code"] = 0
        trace["end_time"] = datetime.now(UTC).isoformat()
        return trace

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
    except subprocess.TimeoutExpired:
        trace["stderr"] = f"[ERROR] Command timed out after {timeout}s"
        trace["exit_code"] = -1
    except Exception as e:
        trace["stderr"] = f"[ERROR] {e}"
        trace["exit_code"] = -2

    trace["end_time"] = datetime.now(UTC).isoformat()
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


def persist_trace(trace: dict, output_dir: str = None) -> str:
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


# ── Main loop ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="GCL Runner")
    parser.add_argument("--skill", required=True, help="Target skill name (e.g., gcp-gce-ops)")
    parser.add_argument("--op", required=True, help="Operation name (e.g., DeleteInstance)")
    parser.add_argument("--command", required=True, help="Full CLI command to execute")
    parser.add_argument("--user-request", help="Original natural-language user request")
    parser.add_argument("--max-iter", type=int, default=DEFAULT_MAX_ITER, help="Max critic iterations (default: %(default)s)")
    parser.add_argument("--rubric", help="Custom rubric path")
    parser.add_argument("--output-dir", help="Output directory for traces")
    parser.add_argument("--dry-run", action="store_true", help="Skip subprocess; run Critic only")
    args = parser.parse_args()

    # Phase 0: Pre-flight
    if has_inline_secret(args.command):
        print("[ERROR] Command contains inlined secrets. Refusing to execute.", file=sys.stderr)
        sys.exit(3)

    rubric = load_rubric(args.skill, args.rubric)
    actual_max_iter = rubric.get("max_iter", args.max_iter)

    trace = {
        "version": "1.0.0",
        "trace_id": f"gcl-trace-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{''.join(random.choices(string.ascii_lowercase, k=6))}",
        "timestamp": datetime.now(UTC).isoformat(),
        "skill": args.skill,
        "op": args.op,
        "user_request": args.user_request or "",
        "max_iter": actual_max_iter,
        "iterations": [],
        "final_verdict": "",
    }

    # Loop
    for i in range(actual_max_iter):
        gen_trace = generate(args.command, dry_run=args.dry_run)
        crit = critique(args.op, gen_trace, rubric)

        iteration = {
            "iteration": i,
            "command": gen_trace["command"],
            "stdout": gen_trace["stdout"],
            "stderr": gen_trace["stderr"],
            "exit_code": gen_trace["exit_code"],
            "critique": crit,
            "verdict": "",
        }

        verdict = decide(i, crit, rubric, actual_max_iter)
        iteration["verdict"] = verdict
        trace["iterations"].append(iteration)

        print(f"[ITER {i}] Verdict: {verdict}")
        if verdict in ("PASS", "SAFETY_FAIL", "MAX_ITER"):
            trace["final_verdict"] = verdict
            break

    # Persist
    trace_path = persist_trace(trace, args.output_dir)
    print(f"[TRACE] Saved to {trace_path}")

    # Exit code
    verdict_map = {
        "PASS": 0,
        "MAX_ITER": 1,
        "SAFETY_FAIL": 2,
    }
    sys.exit(verdict_map.get(trace["final_verdict"], 1))


if __name__ == "__main__":
    main()
