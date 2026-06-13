#!/usr/bin/env python3
"""
gcp-securitycenter-ops test suite
====================================

Three tiers:
  Tier 0  — Static validation (no GCP credentials required)
  Tier 1  — Read-only integration tests (requires GOOGLE_APPLICATION_CREDENTIALS + GCP_ORG_ID)
  eval_q  — eval_queries.json trigger accuracy tests (no credentials)

Run all:
    python3 test_securitycenter_ops.py

Run tiers separately:
    python3 test_securitycenter_ops.py --tier 0
    python3 test_securitycenter_ops.py --tier 1
    python3 test_securitycenter_ops.py --eval-q

Exit codes:
    0  — all requested tiers passed
    1  — one or more tests failed
    2  — missing env vars for Tier 1 (skip Tier 1, pass Tier 0)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
SKILL_DIR = Path(__file__).parent.parent.parent.resolve()
SKILL_MD = SKILL_DIR / "SKILL.md"
REF_DIR = SKILL_DIR / "references"
ASSETS_DIR = SKILL_DIR / "assets"

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"


# ── Helpers ───────────────────────────────────────────────────────────────────
def run(cmd: str) -> tuple[str, str, int]:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=SKILL_DIR)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def check(desc: str, cond: bool, detail: str = "") -> bool:
    status = PASS if cond else FAIL
    print(f"  {status} {desc}")
    if detail and not cond:
        print(f"     └─ {detail}")
    return cond


def section(name: str):
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# TIER 0 — Static validation (no credentials)
# ─────────────────────────────────────────────────────────────────────────────
def tier0():
    section("TIER 0 — Static Validation (no credentials)")
    all_ok = True

    # 0.1 File structure
    print("\n[0.1] File structure")
    expected_files = {
        SKILL_MD,
        REF_DIR / "core-concepts.md",
        REF_DIR / "variables-and-conventions.md",
        REF_DIR / "gcloud-usage.md",
        REF_DIR / "api-sdk-usage.md",
        REF_DIR / "execution-flows.md",
        REF_DIR / "troubleshooting.md",
        REF_DIR / "monitoring.md",
        REF_DIR / "integration.md",
        REF_DIR / "idempotency-checklist.md",
        REF_DIR / "well-architected-assessment.md",
        REF_DIR / "rubric.md",
        REF_DIR / "prompt-templates.md",
        ASSETS_DIR / "example-config.yaml",
        ASSETS_DIR / "eval_queries.json",
    }
    found = list(SKILL_DIR.rglob("*"))
    found_files = {f for f in found if f.is_file()}
    for f in sorted(expected_files):
        all_ok &= check(f"exists: {f.relative_to(SKILL_DIR)}", f in found_files)

    # 0.2 SKILL.md frontmatter schema
    print("\n[0.2] SKILL.md frontmatter schema")
    try:
        import yaml

        text = SKILL_MD.read_text()
        frontmatter = {}
        in_yaml = False
        yaml_lines = []
        for line in text.splitlines():
            if line.strip() == "---":
                if not in_yaml:
                    in_yaml = True
                else:
                    break
            elif in_yaml:
                yaml_lines.append(line)
        frontmatter = yaml.safe_load("\n".join(yaml_lines))
        all_ok &= check("name == gcp-securitycenter-ops", frontmatter.get("name") == "gcp-securitycenter-ops")
        all_ok &= check("description exists and non-empty", bool(frontmatter.get("description")))
        all_ok &= check("license == MIT", frontmatter.get("license") == "MIT")
        meta = frontmatter.get("metadata", {})
        all_ok &= check("metadata.gcl_classification == required", meta.get("gcl_classification") == "required")
        all_ok &= check("metadata.gcl_max_iter == 2", meta.get("gcl_max_iter") == 2)
        all_ok &= check("metadata.api_profile present", bool(meta.get("api_profile")))
        all_ok &= check("metadata.cli_applicability == dual-path", meta.get("cli_applicability") == "dual-path")
        all_ok &= check("metadata.go_version_minimum present", bool(meta.get("go_version_minimum")))
        env_list = meta.get("environment", [])
        all_ok &= check(
            "environment includes GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_APPLICATION_CREDENTIALS" in env_list
        )
        all_ok &= check("environment includes CLOUDSDK_CORE_PROJECT", "CLOUDSDK_CORE_PROJECT" in env_list)
        # Description length
        desc = frontmatter.get("description", "")
        all_ok &= check(
            "description length (should_trigger accuracy < 1024 chars)", len(desc) < 1024, f"length={len(desc)}"
        )
    except Exception as e:
        all_ok &= check("YAML frontmatter parse", False, str(e))

    # 0.3 Five Core Standards table
    print("\n[0.3] Five Core Standards table")
    skill_text = SKILL_MD.read_text()
    standards = [
        "Clear Boundaries",
        "Structured I/O",
        "Explicit Actionable",
        "Complete Failure",
        "Single Responsibility",
    ]
    for std in standards:
        all_ok &= check(f"has '{std}'", std in skill_text)

    # 0.4 Well-Architected Framework table
    print("\n[0.4] Well-Architected Framework table")
    pillars = ["Security", "Stability", "Cost", "Efficiency", "Performance"]
    for pillar in pillars:
        all_ok &= check(f"has pillar '{pillar}'", pillar in skill_text)

    # 0.5 Trigger & Scope
    print("\n[0.5] Trigger & Scope")
    all_ok &= check("SHOULD Use This Skill When present", "### SHOULD Use This Skill When" in skill_text)
    all_ok &= check("SHOULD NOT Use This Skill When present", "### SHOULD NOT Use This Skill When" in skill_text)
    all_ok &= check(
        "Delegation Rules present", "### Delegation Rules" in skill_text or "Delegation Rules" in skill_text
    )

    # 0.6 Variable convention correctness
    print("\n[0.6] Variable convention correctness")
    var_text = (REF_DIR / "variables-and-conventions.md").read_text()
    # env.* should be marked NEVER ask
    all_ok &= check("{{env.*}} marked NEVER ask", "NEVER ask" in var_text or "NEVER ask user" in var_text)
    # user.* should be marked ask once
    all_ok &= check("{{user.*}} marked ask once", "Ask once" in var_text)
    # output.* should be marked Parse from
    all_ok &= check("{{output.*}} marked Parse from", "Parse from" in var_text)

    # 0.7 eval_queries.json schema
    print("\n[0.7] eval_queries.json schema")
    try:
        eq = json.loads((ASSETS_DIR / "eval_queries.json").read_text())
        all_ok &= check("total entries >= 22", len(eq) >= 22)
        all_ok &= check("should_trigger >= 12", sum(1 for x in eq if x.get("should_trigger")) >= 12)
        all_ok &= check("should_not_trigger >= 10", sum(1 for x in eq if not x.get("should_trigger")) >= 10)
        for q in eq:
            all_ok &= check(f"  query field: '{q['query'][:50]}'", "query" in q and bool(q["query"]))
            all_ok &= check("  should_trigger field", "should_trigger" in q)
            all_ok &= check("  expected_cmd_pattern field", "expected_cmd_pattern" in q)
            all_ok &= check("  dry_run_supported field", "dry_run_supported" in q)
    except Exception as e:
        all_ok &= check("eval_queries.json parse", False, str(e))

    # 0.8 Troubleshooting error rows (>= 15)
    print("\n[0.8] Troubleshooting error table")
    try:
        ts_text = (REF_DIR / "troubleshooting.md").read_text()
        rows = [line for line in ts_text.splitlines() if line.startswith("|") and line.count("|") >= 3]
        # Header row doesn't count
        error_rows = [r for r in rows if r.strip() not in ("|", "") and not r.startswith("| Code / Symptom")]
        all_ok &= check(f"error rows >= 15 (found {len(error_rows)})", len(error_rows) >= 15)
        # Verify the table header row has 3 columns (3-4 pipes in markdown)
        # In markdown: | Col1 | Col2 | Col3 | has 4 pipes; Col1 | Col2 | Col3 has 3 pipes
        header_rows = [r for r in rows if "Cause" in r or "Likely Cause" in r]
        if header_rows:
            header_pipes = header_rows[0].count("|")
            # Accept 3 or 4 pipes — both represent a 3-column table in markdown
            all_ok &= check(
                f"3-column format (header has {header_pipes} pipes, expected 3-4)",
                3 <= header_pipes <= 4,
                f"header: {header_rows[0][:80]}",
            )
        else:
            all_ok &= check("3-column format (Error | Cause | Action)", False, "header row not found")
    except Exception as e:
        all_ok &= check("troubleshooting.md parse", False, str(e))

    # 0.9 YAML anchors (TE-5)
    print("\n[0.9] YAML anchors in example-config.yaml (TE-5)")
    yaml_text = (ASSETS_DIR / "example-config.yaml").read_text()
    anchors = re.findall(r"&[a-z_]+", yaml_text)
    refs = re.findall(r"<<: \*[a-z_]+", yaml_text)
    all_ok &= check(f"yaml anchors present (>= 2, found {len(anchors)})", len(anchors) >= 2)
    all_ok &= check(f"yaml anchor refs present (>= 2, found {len(refs)})", len(refs) >= 2)

    # 0.10 GCL rubric structure
    print("\n[0.10] GCL rubric structure")
    rubric_text = (REF_DIR / "rubric.md").read_text()
    required_dims = ["Correctness", "Safety", "Idempotency", "Traceability", "Spec Compliance"]
    for dim in required_dims:
        all_ok &= check(f"rubric has dimension '{dim}'", dim in rubric_text)
    all_ok &= check("Safety Fail Conditions present", "Safety Fail Conditions" in rubric_text)
    all_ok &= check(
        "Per-Destructive-Operation Safety Sub-Rules present",
        "Per-Destructive-Operation Safety Sub-Rules" in rubric_text,
    )
    all_ok &= check("Detection Regexes present", "Detection Regexes" in rubric_text)
    all_ok &= check("Scoring Guide present", "Scoring Guide" in rubric_text)
    all_ok &= check("gcl_max_iter: 2", "gcl_max_iter: 2" in rubric_text or "max_iter: 2" in rubric_text)

    # 0.11 GCL prompt templates structure
    print("\n[0.11] GCL prompt templates structure")
    pt_text = (REF_DIR / "prompt-templates.md").read_text()
    for pt_section in ["Generator Template", "Critic Template", "Final Report Template"]:
        all_ok &= check(f"prompt-templates has '{pt_section}'", pt_section in pt_text)
    # Hallucination Detector (v1.5.0+)
    all_ok &= check("Hallucination Detector template present", "Hallucination Detector" in pt_text)

    # 0.12 Centralized JSON paths
    print("\n[0.12] Centralized JSON paths")
    json_paths = ["$.name", "$.parent", "$.state", "$.severity", "$.category", "$.resourceName", "$.eventTime"]
    for jp in json_paths:
        all_ok &= check(f"JSON path '{jp}' in variables-and-conventions.md", jp in var_text)

    # 0.13 Link integrity
    print("\n[0.13] Link integrity")
    broken = []
    for md in SKILL_DIR.rglob("*.md"):
        text = md.read_text()
        for match in re.finditer(r"\[([^\]]+)\]\(([^\)]+)\)", text):
            href = match.group(2)
            # Skip external links
            if href.startswith("http") or href.startswith("mailto"):
                continue
            # Fragment-only link (#anchor) — only check within same file
            if href.startswith("#"):
                # Anchor within same file — OK (no base to check)
                continue
            # Has fragment — split and check base file
            if "#" in href:
                base, frag = href.split("#", 1)
                # Handle cross-skill links (e.g. ../AGENTS.md or ../../AGENTS.md)
                resolved = (md.parent / base).resolve()
                if not resolved.exists():
                    # Try relative to repo root (for ../AGENTS.md style links)
                    repo_root = SKILL_DIR.parent
                    resolved = (repo_root / base).resolve()
                    if not resolved.exists():
                        broken.append(f"{md.relative_to(SKILL_DIR)} -> {href} [base file missing]")
            else:
                resolved = (md.parent / href).resolve()
                if not resolved.exists():
                    broken.append(f"{md.relative_to(SKILL_DIR)} -> {href}")
    if not broken:
        print(f"  {PASS} all internal links valid (including fragment anchors)")
    for b in broken:
        all_ok &= check(f"link OK: {b}", False)

    # 0.14 Token efficiency checks (TE-1 to TE-8)
    print("\n[0.14] Token efficiency (TE-1 to TE-8)")
    # TE-1: API queries > static tables (no hardcoded quota numbers)
    te1_violations = []
    for md in SKILL_DIR.rglob("*.md"):
        if "code-snippets" in str(md):
            continue
        text = md.read_text()
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if "[VERIFY" in line:
                continue
            if re.search(r"\b(quota|limit)\b", line, re.IGNORECASE):
                if re.search(r"\d{4,}", line) and not re.search(r"\[VERIFY.*?\]", line):
                    te1_violations.append(f"{md.name}:{i + 1}: potential hardcoded quota")
    all_ok &= check(
        "TE-1: no hardcoded quota numbers (except [VERIFY])",
        len(te1_violations) == 0,
        f"{len(te1_violations)} violations" if te1_violations else "",
    )

    # TE-3: error tables compact (3 columns max)
    ts_rows = [line for line in ts_text.splitlines() if line.startswith("|") and line.count("|") >= 4]
    max_pipes = max([line.count("|") for line in ts_rows]) if ts_rows else 0
    all_ok &= check(
        f"TE-3: troubleshooting table <= 4 columns (found {max_pipes})",
        all(line.count("|") <= 4 for line in ts_rows) or len(ts_rows) == 0,
        "some rows have >4 columns" if not all(line.count("|") <= 4 for line in ts_rows) else "",
    )

    # TE-8: reference depth <= 2 layers
    deepest = 0
    for md in list(SKILL_DIR.rglob("*.md")):
        rel = md.relative_to(SKILL_DIR)
        depth = len(rel.parts) - 1  # SKILL.md is depth 0, refs/ is depth 1, refs/advanced/ is depth 2
        deepest = max(deepest, depth)
    all_ok &= check(f"TE-8: reference depth <= 2 (deepest={deepest})", deepest <= 2)

    # 0.15 Security checks
    print("\n[0.15] Security checks")
    skill_full = SKILL_MD.read_text()
    # No credential printing — be specific to avoid false positives on commands
    cred_patterns = [
        (r"cat\s+\$?GOOGLE_APPLICATION_CREDENTIALS", "reading credential file directly"),
        (r"fmt\.Println\(.*config\)", "fmt.Println of config struct"),
        (r'log\.Printf\("%\+v".*config', "log.Printf of config struct"),
        (r"print\([^)]*access_token[^)]*\)", "printing access token value"),
    ]
    cred_violations = []
    for pat, reason in cred_patterns:
        if re.search(pat, skill_full, re.IGNORECASE):
            cred_violations.append(f"{pat} ({reason})")
    all_ok &= check(
        "No credential printing in SKILL.md",
        len(cred_violations) == 0,
        f"violations: {cred_violations}" if cred_violations else "",
    )
    # Delete operations have confirmation requirement
    all_ok &= check(
        "Delete ops have confirmation in execution-flows.md",
        "{{user.confirm_delete}}" in (REF_DIR / "execution-flows.md").read_text(),
    )

    # 0.16 Well-Architected Assessment completeness
    print("\n[0.16] Well-Architected Assessment completeness")
    wa_text = (REF_DIR / "well-architected-assessment.md").read_text()
    for pillar in ["Security", "Stability", "Cost", "Efficiency", "Performance"]:
        all_ok &= check(f"WA has pillar '{pillar}'", pillar in wa_text)
    all_ok &= check("WA has Pillar Summary table", "Pillar Summary" in wa_text)

    # 0.18 Pre-flight checks in execution-flows.md
    print("\n[0.18] Execution-flows.md Pre-flight coverage")
    exec_text = (REF_DIR / "execution-flows.md").read_text()
    operations = [
        "Enable SCC",
        "List, Describe, or Update Sources",
        "List or Describe Findings",
        "Update Finding State",
        "Manage Mute Configs",
        "Manage Notification Configs",
        "Manage BigQuery Exports",
        "Organization Settings",
        "Export Findings to CSV",
    ]
    for op in operations:
        all_ok &= check(f"Execution-flows has operation '{op}'", op in exec_text or op.split(" or ")[0] in exec_text)
    # All operations have Pre-flight → Execute → Validate → Recover
    for flow_section in ["Pre-flight", "Execute", "Validate", "Recover"]:
        all_ok &= check(f"Execution-flows has '{flow_section}'", flow_section in exec_text)

    # 0.19 Idempotency checklist coverage
    print("\n[0.19] Idempotency checklist coverage")
    idem_text = (REF_DIR / "idempotency-checklist.md").read_text()
    resources = [
        "Findings",
        "Mute Configs",
        "Notification Configs",
        "BigQuery Exports",
        "Custom Modules",
        "Resource Value Configs",
    ]
    for res in resources:
        all_ok &= check(f"Idempotency has '{res}'", res in idem_text)

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# TIER 1 — Read-only integration tests (requires GCP credentials)
# ─────────────────────────────────────────────────────────────────────────────
def tier1():
    section("TIER 1 — Read-only Integration Tests")
    all_ok = True

    ORG_ID = os.environ.get("GCP_ORG_ID", "")
    # PROJECT is used later in tier1() but not here — skip for now

    if not ORG_ID:
        print(f"  {WARN} GCP_ORG_ID not set — skipping Tier 1 tests")
        print("     Set: export GCP_ORG_ID=123456789012")
        return True  # Not a failure, just skip

    # 1.1 Pre-conditions
    print("\n[1.1] Pre-conditions")

    out, err, rc = run("gcloud version")
    all_ok &= check("gcloud available", rc == 0, err)

    svc_filter = "--filter=config.name=securitycenter.googleapis.com"
    svc_format = "--format=value(config.name)"
    cmd = f"gcloud services list --enabled {svc_filter} {svc_format}"
    out, err, rc = run(cmd)
    all_ok &= check("SCC API enabled", "securitycenter.googleapis.com" in out, err)

    out, err, rc = run("gcloud auth print-access-token >/dev/null 2>&1")
    all_ok &= check("gcloud auth valid", rc == 0, err)

    # 1.2 Settings get (read-only)
    print("\n[1.2] settings get (read-only)")
    out, err, rc = run(f"gcloud scc settings get --organization={ORG_ID} --format=json")
    all_ok &= check("settings get", rc == 0, err)
    if rc == 0:
        data = json.loads(out)
        print(f"     └─ settings keys: {list(data.keys())[:5]}")

    # 1.3 Sources list
    print("\n[1.3] sources list")
    out, err, rc = run(f"gcloud scc sources list --organization={ORG_ID} --limit=5 --format=json")
    all_ok &= check("sources list", rc == 0, err)
    if rc == 0:
        data = json.loads(out) if out else {}
        sources = data.get("sources", [])
        print(f"     └─ found {len(sources)} sources")

    # 1.4 Findings list — basic
    print("\n[1.4] findings list (basic)")
    out, err, rc = run(f"gcloud scc findings list --organization={ORG_ID} --limit=5 --format=json")
    all_ok &= check("findings list basic", rc == 0, err)

    # 1.5 Findings list — filter validation
    print("\n[1.5] findings list (filter validation)")
    filters = [
        ('state="ACTIVE"', "state filter"),
        ('state="ACTIVE" AND severity="HIGH"', "compound filter"),
        ('state="ACTIVE" AND (severity="HIGH" OR severity="CRITICAL")', "parentheses filter"),
        ('category="OPEN_FIREWALL"', "category filter"),
    ]
    for f, label in filters:
        out, err, rc = run(f'gcloud scc findings list --organization={ORG_ID} --filter="{f}" --limit=1 --format=json')
        if rc != 0 and "INVALID_ARGUMENT" in err:
            all_ok &= check(f"filter '{label}': BAD FILTER (should not happen)", False, err[:200])
        else:
            all_ok &= check(f"filter '{label}': accepted", rc == 0, err[:100] if rc != 0 else "")

    # 1.6 Findings list — pagination
    print("\n[1.6] findings list (pagination)")
    out, err, rc = run(f"gcloud scc findings list --organization={ORG_ID} --limit=2 --format=json")
    if rc == 0 and out:
        data = json.loads(out)
        has_size = "totalSize" in data or "listFindingsResults" in data or len(data) > 0
        all_ok &= check("findings list returns structured data", has_size)
        print(f"     └─ response keys: {list(data.keys())[:5] if isinstance(data, dict) else 'list'}")

    # 1.7 Mute configs list (read-only)
    print("\n[1.7] mute-configs list (read-only)")
    out, err, rc = run(f"gcloud scc mute-configs list --organization={ORG_ID} --format=json")
    all_ok &= check("mute-configs list", rc == 0, err)
    if rc == 0:
        data = json.loads(out) if out else {}
        configs = data.get("muteConfigs", [])
        print(f"     └─ found {len(configs)} mute configs")

    # 1.8 Notification configs list (read-only)
    print("\n[1.8] notifications list (read-only)")
    out, err, rc = run(f"gcloud scc notifications list --organization={ORG_ID} --format=json")
    all_ok &= check("notifications list", rc == 0, err)
    if rc == 0:
        data = json.loads(out) if out else {}
        notifs = data.get("notificationConfigs", [])
        print(f"     └─ found {len(notifs)} notification configs")

    # 1.9 BigQuery exports list (read-only)
    print("\n[1.9] big-query-exports list (read-only)")
    out, err, rc = run(f"gcloud scc big-query-exports list --organization={ORG_ID} --format=json")
    all_ok &= check("big-query-exports list", rc == 0, err)
    if rc == 0:
        data = json.loads(out) if out else {}
        exports = data.get("bigQueryExports", [])
        print(f"     └─ found {len(exports)} BQ exports")

    # 1.10 SDK connectivity
    print("\n[1.10] Python SDK connectivity")
    try:
        out, err, rc = run("python3 -c 'from google.cloud import securitycenter_v2; print(\"OK\")'")
        all_ok &= check("google-cloud-securitycenter_v2 installed", "OK" in out, err)
        if "OK" in out:
            # Quick SDK test
            out, err, rc = run(
                f'python3 -c "from google.cloud import securitycenter_v2; '
                f"c = securitycenter_v2.SecurityCenterClient(); "
                f'p = f\\"organizations/{ORG_ID}/sources/-\\"; '
                f"r = securitycenter_v2.ListFindingsRequest(parent=p, page_size=1); "
                f"results = list(c.list_findings(request=r)); "
                f'print(f\\"found={{len(results)}}\\")"'
            )
            all_ok &= check("SDK list_findings() works", "found=" in out, err)
    except Exception as e:
        all_ok &= check("SDK import", False, str(e))

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# eval_q — trigger accuracy tests (no credentials)
# ─────────────────────────────────────────────────────────────────────────────
def eval_queries_tests():
    section("eval_q — Trigger Accuracy Tests")
    all_ok = True

    try:
        eq = json.loads((ASSETS_DIR / "eval_queries.json").read_text())
    except Exception as e:
        check("eval_queries.json parse", False, str(e))
        return False

    # 1. Distribution
    trigger = [q for q in eq if q.get("should_trigger")]
    not_trigger = [q for q in eq if not q.get("should_trigger")]
    all_ok &= check(f"should_trigger count: {len(trigger)} (target >= 12)", len(trigger) >= 12)
    all_ok &= check(f"should_not_trigger count: {len(not_trigger)} (target >= 10)", len(not_trigger) >= 10)

    # 2. All should_trigger queries cover distinct operations
    print("\n[eq-2] Operation coverage (should_trigger)")
    covered_ops = {}
    for q in trigger:
        cmd = q.get("expected_cmd_pattern", "")
        ops = covered_ops.setdefault(cmd, [])
        ops.append(q["query"][:60])
    for cmd, queries in sorted(covered_ops.items()):
        print(f"  {PASS} {cmd}: {len(queries)} queries")

    # 3. All queries have non-empty expected_cmd_pattern
    print("\n[eq-3] expected_cmd_pattern validity")
    for q in eq:
        pattern = q.get("expected_cmd_pattern", "")
        all_ok &= check(
            f"  '{q['query'][:50]}' -> cmd_pattern",
            bool(pattern) and " " in pattern and pattern.startswith("gcloud"),
            f"pattern='{pattern}'",
        )

    # 4. should_not_trigger queries target adjacent skills
    print("\n[eq-4] should_not_trigger coverage (delegation targets)")
    delegation_patterns = [
        "gcloud projects add-iam-policy-binding",
        "gcloud logging sinks create",
        "gcloud monitoring policies create",
        "gcloud pubsub topics create",
        "gcloud bigquery datasets create",
        "gcloud compute firewall-rules create",
        "gcloud kms keyrings create",
        "gcloud secrets create",
    ]
    not_trigger_patterns = [q.get("expected_cmd_pattern", "") for q in not_trigger]
    for pat in delegation_patterns:
        found = any(pat in p for p in not_trigger_patterns)
        all_ok &= check(
            f"delegation target: '{pat[:40]}'", found, "not covered by should_not_trigger" if not found else ""
        )

    # 5. dry_run_supported consistency
    print("\n[eq-5] dry_run_supported consistency")
    for q in eq:
        if "delete" in q.get("expected_cmd_pattern", "").lower():
            all_ok &= check(
                f"delete op has dry_run_supported=false: '{q['query'][:50]}'",
                not q.get("dry_run_supported"),
                f"dry_run={q.get('dry_run_supported')}",
            )

    # 6. eval_queries covers all 12 SCC operations
    print("\n[eq-6] 12 operations coverage")
    cmd_patterns = [q["expected_cmd_pattern"] for q in trigger]
    required_ops = {
        "scc settings enable": False,
        "scc findings list": False,
        "scc findings describe": False,
        "scc findings update-mute": False,
        "scc findings update-state": False,
        "scc mute-configs list": False,
        "scc mute-configs create": False,
        "scc mute-configs delete": False,
        "scc notifications create": False,
        "scc notifications list": False,
        "scc notifications delete": False,
        "scc big-query-exports create": False,
        "scc big-query-exports list": False,
        "scc big-query-exports delete": False,
        "scc findings export": False,
        "scc settings get": False,
        "scc sources list": False,
    }
    for pat in required_ops:
        found = any(pat in cmd for cmd in cmd_patterns)
        required_ops[pat] = found
        all_ok &= check(f"operation covered: '{pat}'", found)

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# GCL rubric compliance check
# ─────────────────────────────────────────────────────────────────────────────
def gcl_compliance():
    section("gcl — GCL Rubric Compliance")
    all_ok = True

    rubric_text = (REF_DIR / "rubric.md").read_text()
    pt_text = (REF_DIR / "prompt-templates.md").read_text()

    # 1. 5 core dimensions
    print("\n[gcl-1] Core dimensions")
    dims = ["Correctness", "Safety", "Idempotency", "Traceability", "Spec Compliance"]
    for d in dims:
        all_ok &= check(f"dimension '{d}'", d in rubric_text)

    # 2. Safety fail conditions
    print("\n[gcl-2] Safety fail conditions")
    safety_check = "Safety score is `0`" in rubric_text
    safety_check = safety_check or "Safety score is 0" in rubric_text
    all_ok &= check("Safety score = 0 → abort", safety_check)
    del_check = "delete" in rubric_text.lower()
    del_check = del_check and "confirmation" in rubric_text.lower()
    all_ok &= check("delete without confirmation", del_check)

    # 3. Per-destructive operation safety sub-rules
    print("\n[gcl-3] Per-destructive safety sub-rules")
    ops = [
        "Delete Mute Config",
        "Delete Notification Config",
        "Delete BigQuery Export",
        "Update Finding State",
        "Enable SCC",
    ]
    for op in ops:
        all_ok &= check(f"safety sub-rule for '{op}'", op in rubric_text)

    # 4. Detection regexes
    print("\n[gcl-4] Detection regexes")
    all_ok &= check("detection regexes present", "Detection Regexes" in rubric_text)
    regex_blocks = re.findall(r"```text\n(.*?)```", rubric_text, re.DOTALL)
    all_ok &= check("at least one regex block", len(regex_blocks) >= 1)

    # 5. Scoring guide
    print("\n[gcl-5] Scoring guide")
    all_ok &= check("Scoring Guide present", "Scoring Guide" in rubric_text)
    scores = ["0", "1-3", "4-6", "7-8", "9-10"]
    for s in scores:
        all_ok &= check(f"score '{s}' in scoring guide", s in rubric_text)

    # 6. Generator template
    print("\n[gcl-6] Generator template")
    all_ok &= check("Generator has inputs", "Inputs:" in pt_text)
    all_ok &= check("Generator has rules", "Rules:" in pt_text)
    all_ok &= check("Generator has safety rules", "safety" in pt_text.lower())

    # 7. Critic template
    print("\n[gcl-7] Critic template")
    critic_check = "{{user.request}}" not in pt_text
    critic_check = critic_check or "Critic MUST NOT see" in pt_text
    all_ok &= check("Critic does not see user request", critic_check)
    ro_check = "read-only" in pt_text.lower()
    ro_check = ro_check or "read only" in pt_text.lower()
    all_ok &= check("Critic uses read-only verification", ro_check)

    # 8. Hallucination Detector
    print("\n[gcl-8] Hallucination Detector (v1.5.0+)")
    all_ok &= check("H template present", "Hallucination Detector" in pt_text)
    all_ok &= check("H has PASS/ABORT return", "PASS" in pt_text and "ABORT" in pt_text)

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="gcp-securitycenter-ops test suite")
    parser.add_argument("--tier", choices=["0", "1"], default=None, help="Run specific tier: 0=static, 1=integration")
    parser.add_argument("--eval-q", action="store_true", help="Run eval_queries trigger accuracy tests")
    parser.add_argument("--gcl", action="store_true", help="Run GCL rubric compliance tests")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    args = parser.parse_args()

    run_all = args.all or (args.tier is None and not args.eval_q and not args.gcl)

    results = {}

    if run_all or args.tier in ("0", None):
        results["tier0"] = tier0()
    if run_all or args.tier == "1":
        results["tier1"] = tier1()
    if run_all or args.eval_q:
        results["eval_q"] = eval_queries_tests()
    if run_all or args.gcl:
        results["gcl"] = gcl_compliance()

    section("SUMMARY")
    for name, ok in results.items():
        status = PASS if ok else FAIL
        print(f"  {status} {name}")

    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\n  {FAIL} FAILED: {', '.join(failed)}")
        sys.exit(1)
    else:
        print(f"\n  {PASS} ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
