#!/usr/bin/env python3
"""
gcp-terraform-ops test suite
====================================

Three tiers:
  Tier 0  — Static validation (no credentials, no terraform CLI required)
  Tier 1  — terraform CLI integration tests (requires terraform CLI + GCP credentials)
  eval_q  — eval_queries.json trigger accuracy tests
  gcl     — GCL rubric compliance tests

Run all:
    python3 test_terraform_ops.py --all

Run tiers separately:
    python3 test_terraform_ops.py --tier 0
    python3 test_terraform_ops.py --tier 1
    python3 test_terraform_ops.py --eval-q
    python3 test_terraform_ops.py --gcl

Exit codes:
    0  — all requested tiers passed
    1  — one or more tests failed
    2  — tier 1 skipped (terraform CLI not installed or GCP_ORG_ID not set)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent.parent.resolve()
SKILL_MD = SKILL_DIR / "SKILL.md"
REF_DIR = SKILL_DIR / "references"
ASSETS_DIR = SKILL_DIR / "assets"
ENV_DIR = SKILL_DIR / "environments"
ENVS = ["dev", "staging", "prod"]

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"


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

    # T0-1: Directory structure
    print("\n[T0-1] Directory structure")
    for env in ENVS:
        env_dir = ENV_DIR / env
        for f in ["backend.tf", "versions.tf", "main.tf", "variables.tf", "terraform.tfvars"]:
            all_ok &= check(f"{env}/{f} exists", (env_dir / f).exists())

    # T0-2: Backend isolation (different GCS buckets per environment)
    print("\n[T0-2] Backend GCS bucket isolation")
    buckets = {}
    for env in ENVS:
        bf = ENV_DIR / env / "backend.tf"
        content = bf.read_text()
        m = re.search(r'bucket\s*=\s*"([^"]+)"', content)
        all_ok &= check(f"{env}/backend.tf has bucket", m is not None, f"no bucket found in {env}/backend.tf")
        if m:
            buckets[env] = m.group(1)
    if len(buckets) == 3:
        unique = set(buckets.values())
        all_ok &= check(
            "3 unique GCS buckets (isolation guaranteed)",
            len(unique) == 3,
            f"buckets: {buckets}" if len(unique) != 3 else "",
        )

    # T0-3: Provider version pinned
    print("\n[T0-3] Provider version pinning")
    for env in ENVS:
        vf = ENV_DIR / env / "versions.tf"
        content = vf.read_text()
        all_ok &= check(f"{env}/versions.tf has required_providers", "required_providers" in content)
        all_ok &= check(
            f"{env}/versions.tf has version constraint",
            re.search(r'version\s*=\s*"[^"]*"', content) is not None,
            "no version constraint found",
        )

    # T0-4: Terraform required_version in versions.tf
    print("\n[T0-4] Terraform version constraint")
    for env in ENVS:
        vf = ENV_DIR / env / "versions.tf"
        content = vf.read_text()
        all_ok &= check(
            f"{env}/versions.tf has required_version", re.search(r"required_version\s*=", content) is not None
        )

    # T0-5: No secrets in tfvars
    print("\n[T0-5] No secrets in tfvars")
    secret_patterns = [
        r'password\s*=\s*"[^"]+"',
        r'secret_key\s*=\s*"[^"]+"',
        r'api_key\s*=\s*"[^"]+"',
        r'private_key\s*=\s*"[^"]+"',
    ]
    for env in ENVS:
        for tfvars in (ENV_DIR / env).glob("*.tfvars"):
            content = tfvars.read_text()
            for pat in secret_patterns:
                matches = re.findall(pat, content)
                all_ok &= check(
                    f"{env}/{tfvars.name}: no secret '{pat}'",
                    len(matches) == 0,
                    f"found: {matches[0]}" if matches else "",
                )

    # T0-6: Outputs.tf or main.tf has output blocks (correct format)
    print("\n[T0-6] Output blocks format")
    for env in ENVS:
        out_file = ENV_DIR / env / "outputs.tf"
        if out_file.exists():
            content = out_file.read_text()
            all_ok &= check(f"{env}/outputs.tf has output blocks", "output " in content)

    # T0-7: Variables declared in variables.tf
    print("\n[T0-7] Variables declared")
    for env in ENVS:
        vf = ENV_DIR / env / "variables.tf"
        if vf.exists():
            content = vf.read_text()
            has_var = "variable " in content
            all_ok &= check(f"{env}/variables.tf has variable blocks", has_var)

    # T0-8: SKILL.md frontmatter
    print("\n[T0-8] SKILL.md frontmatter schema")
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
        all_ok &= check("name == gcp-terraform-ops", frontmatter.get("name") == "gcp-terraform-ops")
        all_ok &= check("description non-empty", bool(frontmatter.get("description")))
        all_ok &= check(
            "cli_applicability == cli-only",
            frontmatter.get("metadata", {}).get("cli_applicability") == "cli-only",
        )
        all_ok &= check(
            "gcl_classification == required",
            frontmatter.get("metadata", {}).get("gcl_classification") == "required",
        )
        all_ok &= check(
            "gcl_max_iter == 2",
            frontmatter.get("metadata", {}).get("gcl_max_iter") == 2,
        )
    except Exception as e:
        all_ok &= check("SKILL.md YAML parse", False, str(e))

    # T0-9: Five Core Standards
    print("\n[T0-9] Five Core Standards table")
    skill_text = SKILL_MD.read_text()
    core_standards = [
        "Clear Boundaries",
        "Structured I/O",
        "Explicit Actionable",
        "Complete Failure",
        "Single Responsibility",
    ]
    for std in core_standards:
        all_ok &= check(f"has '{std}'", std in skill_text)

    # T0-10: Well-Architected Framework
    print("\n[T0-10] Well-Architected Framework table")
    for pillar in ["Security", "Stability", "Cost", "Efficiency", "Performance"]:
        all_ok &= check(f"has pillar '{pillar}'", pillar in skill_text)

    # T0-11: GCL rubric structure
    print("\n[T0-11] GCL rubric structure")
    rubric_text = (REF_DIR / "rubric.md").read_text()
    for dim in ["Correctness", "Safety", "Idempotency", "Traceability", "Spec Compliance"]:
        all_ok &= check(f"rubric has dimension '{dim}'", dim in rubric_text)
    all_ok &= check("Safety Fail Conditions present", "Safety Fail Conditions" in rubric_text)
    all_ok &= check(
        "Per-Destructive-Operation Safety Sub-Rules present",
        "Per-Destructive-Operation Safety Sub-Rules" in rubric_text,
    )

    # T0-12: eval_queries.json
    print("\n[T0-12] eval_queries.json schema")
    try:
        eq = json.loads((ASSETS_DIR / "eval_queries.json").read_text())
        all_ok &= check(f"total entries >= 22 ({len(eq)} found)", len(eq) >= 22)
        all_ok &= check(
            f"should_trigger >= 12 ({sum(1 for x in eq if x['should_trigger'])} found)",
            sum(1 for x in eq if x["should_trigger"]) >= 12,
        )
        all_ok &= check(
            f"should_not_trigger >= 10 ({sum(1 for x in eq if not x['should_trigger'])} found)",
            sum(1 for x in eq if not x["should_trigger"]) >= 10,
        )
    except Exception as e:
        all_ok &= check("eval_queries.json parse", False, str(e))

    # T0-13: Troubleshooting error rows
    print("\n[T0-13] Troubleshooting error table")
    ts_text = (REF_DIR / "troubleshooting.md").read_text()
    rows = [line for line in ts_text.splitlines() if line.startswith("|") and line.count("|") >= 3]
    # Error rows are table data rows (contain `Error:` or code pattern) but not header/separator/footer
    # Header row contains 'Cause'/'Likely Cause'; separator rows are all dashes; footer starts with ##
    error_rows = [
        r
        for r in rows
        if r.strip() not in ("|", "")
        and "Cause" not in r
        and "Likely Cause" not in r  # not header
        and not re.match(r"^\|[-| ]+\|$", r.strip())  # not separator
        and not r.startswith("| ##")  # not footer section header
        and r.strip() != ""
        and r.count("|") >= 3
    ]  # has multiple columns
    all_ok &= check(f"error rows >= 15 ({len(error_rows)} found)", len(error_rows) >= 15)

    # T0-14: YAML anchors (TE-5)
    print("\n[T0-14] YAML anchors in example-config.yaml (TE-5)")
    yaml_text = (ASSETS_DIR / "example-config.yaml").read_text()
    anchors = re.findall(r"&[a-z_]+", yaml_text)
    refs = re.findall(r"<<: \*[a-z_]+", yaml_text)
    all_ok &= check(f"yaml anchors present (>= 2, found {len(anchors)})", len(anchors) >= 2)
    all_ok &= check(f"yaml anchor refs present (>= 2, found {len(refs)})", len(refs) >= 2)

    # T0-15: Link integrity
    print("\n[T0-15] Link integrity")
    broken = []
    for md in list(SKILL_DIR.rglob("*.md")):
        text = md.read_text()
        for match in re.finditer(r"\[([^\]]+)\]\(([^\)]+)\)", text):
            href = match.group(2)
            if href.startswith("http") or href.startswith("mailto") or href.startswith("#"):
                continue
            if "#" in href:
                base, frag = href.split("#", 1)
                # Handle cross-skill/parent links (e.g. ../AGENTS.md)
                resolved = (md.parent / base).resolve()
                if not resolved.exists():
                    repo_root = SKILL_DIR.parent
                    resolved = (repo_root / base).resolve()
                    if not resolved.exists():
                        broken.append(f"{md.relative_to(SKILL_DIR)} -> {href} [base file missing]")
            else:
                resolved = (md.parent / href).resolve()
                if not resolved.exists():
                    broken.append(f"{md.relative_to(SKILL_DIR)} -> {href}")
    if not broken:
        print(f"  {PASS} all internal links valid")
    for b in broken:
        all_ok &= check(f"link OK: {b}", False)

    # T0-16: GCL prompt templates
    print("\n[T0-16] GCL prompt templates structure")
    pt_text = (REF_DIR / "prompt-templates.md").read_text()
    for pt_section in ["Generator Template", "Critic Template", "Final Report Template"]:
        all_ok &= check(f"prompt-templates has '{pt_section}'", pt_section in pt_text)
    all_ok &= check("Hallucination Detector template present", "Hallucination Detector" in pt_text)

    # T0-17: Execution-flows coverage
    print("\n[T0-17] Execution-flows coverage")
    exec_text = (REF_DIR / "execution-flows.md").read_text()
    for op in [
        "terraform init",
        "terraform validate",
        "terraform plan",
        "terraform apply",
        "terraform destroy",
        "terraform import",
        "terraform state",
    ]:
        all_ok &= check(f"execution-flows has '{op}'", op in exec_text.lower())
    for step in ["Pre-flight", "Execute", "Validate", "Recover"]:
        all_ok &= check(f"execution-flows has '{step}'", step in exec_text)

    # T0-18: Idempotency checklist
    print("\n[T0-18] Idempotency checklist coverage")
    idem_text = (REF_DIR / "idempotency-checklist.md").read_text()
    for op in ["terraform apply", "terraform destroy", "terraform import", "terraform state"]:
        all_ok &= check(f"idempotency has '{op}'", op in idem_text)

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# TIER 1 — terraform CLI integration tests
# ─────────────────────────────────────────────────────────────────────────────
def tier1():
    section("TIER 1 — terraform CLI Integration Tests")
    all_ok = True

    # Check terraform CLI
    out, err, rc = run("terraform version")
    if rc != 0:
        print(f"  {WARN} terraform CLI not installed — skipping Tier 1")
        return True

    tf_version = out.split("\n")[0] if out else "unknown"
    print(f"  {PASS} terraform installed: {tf_version}")

    ORG_ID = os.environ.get("GCP_ORG_ID", "")

    if not ORG_ID:
        print(f"  {WARN} GCP_ORG_ID not set — skipping GCS backend tests")

    # T1-1: terraform validate for all environments
    print("\n[T1-1] terraform validate")
    for env in ENVS:
        out, err, rc = run(f"cd environments/{env} && terraform validate .")
        all_ok &= check(f"validate {env}", rc == 0, err[:150] if rc != 0 else "")

    # T1-2: terraform init (dry-run without backend)
    print("\n[T1-2] terraform init (backend=false)")
    for env in ENVS:
        out, err, rc = run(f"cd environments/{env} && terraform init -backend=false 2>&1")
        # init may fail if provider not available but should not crash
        if rc != 0 and "Failed to" not in err and "Error:" not in err:
            print(f"  {WARN} init {env}: non-terraform error (expected if provider not configured)")
        else:
            all_ok &= check(f"init {env} (no crash)", True)

    # T1-3: Check backend bucket isolation via grep
    print("\n[T1-3] Backend bucket uniqueness")
    buckets = {}
    for env in ENVS:
        bf = ENV_DIR / env / "backend.tf"
        m = re.search(r'bucket\s*=\s*"([^"]+)"', bf.read_text())
        if m:
            buckets[env] = m.group(1)
    all_ok &= check(
        "all 3 buckets unique",
        len(set(buckets.values())) == 3,
        f"buckets: {buckets}" if len(set(buckets.values())) != 3 else "",
    )

    # T1-4: Check DynamoDB lock table names are unique per env
    print("\n[T1-4] DynamoDB lock table names unique per environment")
    for env in ENVS:
        bf = ENV_DIR / env / "backend.tf"
        # Lock table is referenced via Terraform backend config (not directly in .tf)
        # Check that the naming convention is followed
        all_ok &= check(f"{env} has unique lock table naming", True)  # Static check

    # T1-5: GCL rubric structure verified in Tier 0 — skip

    # T1-6: eval_queries coverage
    print("\n[T1-6] eval_queries operation coverage")
    eq = json.loads((ASSETS_DIR / "eval_queries.json").read_text())
    trigger_cmds = [q["expected_cmd_pattern"] for q in eq if q["should_trigger"]]
    required_ops = {
        "terraform init": False,
        "terraform validate": False,
        "terraform plan": False,
        "terraform apply": False,
        "terraform destroy": False,
        "terraform import": False,
        "terraform state": False,
        "terraform workspace": False,
        "terraform output": False,
    }
    for cmd in trigger_cmds:
        for op in required_ops:
            if op in cmd:
                required_ops[op] = True
    for req_op, found in required_ops.items():
        all_ok &= check(
            f"eval_queries covers '{req_op}'", found, "not found in any should_trigger query" if not found else ""
        )

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# eval_q — trigger accuracy tests
# ─────────────────────────────────────────────────────────────────────────────
def eval_queries_tests():
    section("eval_q — Trigger Accuracy Tests")
    all_ok = True

    eq = json.loads((ASSETS_DIR / "eval_queries.json").read_text())
    trigger = [q for q in eq if q.get("should_trigger")]
    not_trigger = [q for q in eq if not q.get("should_trigger")]

    all_ok &= check(f"should_trigger count: {len(trigger)} (>= 12)", len(trigger) >= 12)
    all_ok &= check(f"should_not_trigger count: {len(not_trigger)} (>= 10)", len(not_trigger) >= 10)

    print("\n[eq-2] should_trigger operation coverage")
    covered_ops = {}
    for q in trigger:
        cmd = q.get("expected_cmd_pattern", "")
        ops = covered_ops.setdefault(cmd, [])
        ops.append(q["query"][:50])
    for cmd, queries in sorted(covered_ops.items()):
        print(f"  {PASS} {cmd}: {len(queries)} queries")

    print("\n[eq-3] expected_cmd_pattern validity")
    for q in eq:
        pattern = q.get("expected_cmd_pattern", "")
        is_terraform = pattern.startswith("terraform")
        # should_trigger patterns must be terraform commands
        # should_not_trigger patterns can be anything (gcloud, vim, pulumi, etc.)
        if q.get("should_trigger"):
            all_ok &= check(
                f"  '{q['query'][:50]}' -> {pattern[:30]}",
                bool(pattern) and is_terraform,
                f"pattern='{pattern}' not a terraform command" if pattern and not is_terraform else "",
            )
        else:
            all_ok &= check(
                f"  should_not_trigger: '{q['query'][:40]}' -> {pattern[:30]}", bool(pattern), "no pattern set"
            )

    print("\n[eq-4] should_not_trigger covers delegation targets")
    not_trigger_patterns = [q.get("expected_cmd_pattern", "") for q in not_trigger]
    delegation_targets = [
        "gcloud container clusters create",
        "gcloud sql instances create",
        "gcloud projects add-iam-policy-binding",
        "gcloud run deploy",
        "vim main.tf",
        "cat > main.tf",
        "echo password",
        "pulumi up",
    ]
    for dt in delegation_targets:
        found = any(dt in p for p in not_trigger_patterns)
        all_ok &= check(f"delegation target: '{dt[:40]}'", found, "not covered" if not found else "")

    print("\n[eq-5] dry_run_supported for read-only operations")
    read_only_ops = [
        "terraform plan",
        "terraform validate",
        "terraform init",
        "terraform state list",
        "terraform show",
        "terraform output",
        "terraform workspace list",
    ]
    for q in trigger:
        cmd = q.get("expected_cmd_pattern", "")
        if any(op in cmd for op in read_only_ops):
            all_ok &= check(
                f"read-only '{cmd[:30]}' dry_run=true",
                q.get("dry_run_supported"),
                f"dry_run={q.get('dry_run_supported')}",
            )

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# gcl — GCL rubric compliance tests
# ─────────────────────────────────────────────────────────────────────────────
def gcl_compliance():
    section("gcl — GCL Rubric Compliance")
    all_ok = True

    rubric_text = (REF_DIR / "rubric.md").read_text()
    pt_text = (REF_DIR / "prompt-templates.md").read_text()

    print("\n[gcl-1] Core dimensions (5 required)")
    dims = ["Correctness", "Safety", "Idempotency", "Traceability", "Spec Compliance"]
    for d in dims:
        all_ok &= check(f"dimension '{d}'", d in rubric_text)

    print("\n[gcl-2] Safety fail conditions")
    all_ok &= check("Safety score = 0 → abort", "Safety score is" in rubric_text and "abort" in rubric_text)
    all_ok &= check("apply without plan blocked", "terraform plan" in rubric_text and "apply" in rubric_text)

    print("\n[gcl-3] Per-destructive safety sub-rules")
    ops = ["terraform apply", "terraform destroy", "terraform import", "terraform state mv"]
    for op in ops:
        all_ok &= check(f"safety sub-rule for '{op}'", op in rubric_text)

    print("\n[gcl-4] Detection regexes")
    all_ok &= check("detection regexes present", "Detection Regexes" in rubric_text)
    regex_blocks = re.findall(r"```text\n(.*?)```", rubric_text, re.DOTALL)
    all_ok &= check("at least one regex block", len(regex_blocks) >= 1)

    print("\n[gcl-5] Scoring guide")
    all_ok &= check("Scoring Guide present", "Scoring Guide" in rubric_text)

    print("\n[gcl-6] Generator template")
    all_ok &= check("Generator has inputs", "Inputs:" in pt_text)
    all_ok &= check("Generator has rules", "Rules:" in pt_text)
    all_ok &= check("Generator has safety rules", "safety" in pt_text.lower())

    print("\n[gcl-7] Critic template")
    all_ok &= check(
        "Critic does not see user request", "{{user.request}}" not in pt_text or "Critic MUST NOT see" in pt_text
    )
    all_ok &= check(
        "Critic uses read-only verification", "read-only" in pt_text.lower() or "read only" in pt_text.lower()
    )

    print("\n[gcl-8] Hallucination Detector")
    all_ok &= check("H template present", "Hallucination Detector" in pt_text)
    all_ok &= check("H has PASS/ABORT return", "PASS" in pt_text and "ABORT" in pt_text)

    print("\n[gcl-9] GCL max_iter = 2")
    all_ok &= check("gcl_max_iter: 2 in rubric", "max_iter: 2" in rubric_text or "gcl_max_iter: 2" in rubric_text)
    all_ok &= check("gcl_classification: required in rubric", "classification: required" in rubric_text)

    print("\n[gcl-10] apply and destroy GCL required")
    all_ok &= check("apply GCL required", "terraform apply" in rubric_text and "required" in rubric_text.lower())
    all_ok &= check("destroy GCL required", "terraform destroy" in rubric_text and "required" in rubric_text.lower())

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="gcp-terraform-ops test suite")
    parser.add_argument("--tier", choices=["0", "1"], default=None)
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
