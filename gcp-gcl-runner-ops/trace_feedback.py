#!/usr/bin/env python3
"""
GCL Trace Feedback — closed-loop quality aggregation from GCL traces.

This CLI scans GCL trace JSON files (produced by the GCL runner into
`audit-results/`) and aggregates them per skill to surface failure patterns
that should flow back into skill improvement. It closes the AIOps loop:
traces -> skill quality report.

Usage:
    python3 trace_feedback.py --trace-dir ./audit-results
    python3 trace_feedback.py --trace-dir ./audit-results --report-path report.md

Exit codes:
    0 = report generated, 1 = usage/IO error
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gcl_logging import get_gcl_logger

logger = get_gcl_logger("gcl-trace-feedback")

# Result values considered successful (see gcl_trace_schema.GCLResult)
PASS_RESULTS = {"PASS"}


@dataclass
class SkillQuality:
    """Aggregated quality metrics for a single skill."""

    skill: str
    total: int = 0
    failures: int = 0
    result_counts: Counter = field(default_factory=Counter)
    error_types: Counter = field(default_factory=Counter)
    degraded_count: int = 0
    low_safety_count: int = 0
    low_autonomy_count: int = 0
    failure_ops: Counter = field(default_factory=Counter)
    failure_traces: list[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.total - self.failures) / self.total


def _is_failure(result: str) -> bool:
    return result not in PASS_RESULTS


def _load_trace(path: Path) -> dict[str, Any] | None:
    """Load and minimally validate a single trace file. Returns None on skip."""
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"skip unreadable trace {path.name}: {exc}")
        return None
    if not isinstance(data, dict) or "skill" not in data:
        logger.warning(f"skip malformed trace {path.name}: missing 'skill'")
        return None
    return data


def scan_traces(trace_dir: Path) -> list[dict[str, Any]]:
    """Scan trace_dir for gcl-trace-*.json files and load them."""
    if not trace_dir.is_dir():
        logger.error(f"trace dir not found: {trace_dir}")
        return []
    traces = []
    for path in sorted(trace_dir.glob("gcl-trace-*.json")):
        data = _load_trace(path)
        if data is not None:
            traces.append(data)
    logger.info(f"scanned {len(traces)} trace(s) in {trace_dir}")
    return traces


def aggregate(traces: list[dict[str, Any]]) -> dict[str, SkillQuality]:
    """Aggregate traces per skill into SkillQuality records."""
    by_skill: dict[str, SkillQuality] = {}
    for trace in traces:
        skill = trace.get("skill", "unknown")
        q = by_skill.setdefault(skill, SkillQuality(skill=skill))
        q.total += 1

        result = str(trace.get("result", ""))
        q.result_counts[result] += 1
        if _is_failure(result):
            q.failures += 1
            q.failure_ops[trace.get("op", "unknown")] += 1
            q.failure_traces.append(trace.get("trace_id", "unknown"))

        error_type = trace.get("error_type")
        if error_type:
            q.error_types[str(error_type)] += 1

        if trace.get("degraded_to_human"):
            q.degraded_count += 1

        safety = trace.get("safety_score")
        if isinstance(safety, int | float) and safety < 1.0:
            q.low_safety_count += 1

        autonomy = trace.get("autonomy_ratio")
        if isinstance(autonomy, int | float) and autonomy < 1.0:
            q.low_autonomy_count += 1

    return by_skill


def build_report(by_skill: dict[str, SkillQuality]) -> str:
    """Render the aggregated skill quality report as Markdown."""
    total_traces = sum(q.total for q in by_skill.values())
    total_failures = sum(q.failures for q in by_skill.values())

    lines: list[str] = []
    lines.append("# GCL Skill Quality Report")
    lines.append("")
    lines.append(f"- Total traces: {total_traces}")
    lines.append(f"- Total failures: {total_failures}")
    lines.append(f"- Overall pass rate: {_pct(total_traces - total_failures, total_traces)}")
    lines.append("")

    if not by_skill:
        lines.append("_No traces found._")
        return "\n".join(lines)

    for skill in sorted(by_skill, key=lambda s: (-by_skill[s].failures, s)):
        q = by_skill[skill]
        lines.append(f"## {skill}")
        lines.append("")
        lines.append(f"- Traces: {q.total} | Failures: {q.failures} | "
                     f"Pass rate: {_pct(q.total - q.failures, q.total)}")
        if q.failures:
            lines.append("")
            lines.append("**Failure dimensions:**")
            lines.append(f"- Result breakdown: {dict(q.result_counts)}")
            if q.error_types:
                lines.append(f"- Error types: {dict(q.error_types)}")
            if q.degraded_count:
                lines.append(f"- Degraded to human: {q.degraded_count}")
            if q.low_safety_count:
                lines.append(f"- Low safety score (<1.0): {q.low_safety_count}")
            if q.low_autonomy_count:
                lines.append(f"- Low autonomy ratio (<1.0): {q.low_autonomy_count}")
            if q.failure_ops:
                top_ops = q.failure_ops.most_common(3)
                lines.append(f"- Top failing ops: {top_ops}")
        lines.append("")

    return "\n".join(lines)


def _pct(num: int, den: int) -> str:
    if den == 0:
        return "n/a"
    return f"{100.0 * num / den:.1f}%"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate GCL traces into a per-skill quality report.",
    )
    parser.add_argument(
        "--trace-dir",
        default="./audit-results",
        help="Directory containing gcl-trace-*.json files (default: ./audit-results)",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Write the report to this file instead of stdout",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    trace_dir = Path(args.trace_dir)

    traces = scan_traces(trace_dir)
    by_skill = aggregate(traces)
    report = build_report(by_skill)

    if args.report_path:
        try:
            Path(args.report_path).write_text(report)
            logger.info(f"report written to {args.report_path}")
        except OSError as exc:
            logger.error(f"failed to write report: {exc}")
            return 1
    else:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
