"""Tests for GCL Grafana dashboard JSON."""

import json
import os
from pathlib import Path


# Path to the dashboard JSON
DASHBOARD_PATH = Path(__file__).parent.parent / "grafana" / "gcl_observability_dashboard.json"

# Required metric names from log_metrics_config.yaml
REQUIRED_METRICS = [
    "gcl_error_rate",
    "gcl_execution_latency",
    "gcl_safety_failures",
    "gcl_autonomy_ratio",
]

# Expected panel titles (6 required panels)
EXPECTED_PANELS = [
    "GCL Error Rate",
    "Execution Latency",
    "Safety Failures Over Time",
    "Autonomy Ratio",
    "Operations by Skill",
    "Results Breakdown",
]


def load_dashboard() -> dict:
    """Load the dashboard JSON file."""
    assert DASHBOARD_PATH.exists(), f"Dashboard not found at {DASHBOARD_PATH}"
    with open(DASHBOARD_PATH, "r") as f:
        return json.load(f)


def test_dashboard_json_is_valid():
    """Validate that the dashboard JSON is valid and parseable."""
    dashboard = load_dashboard()
    assert isinstance(dashboard, dict), "Dashboard should be a dictionary"
    assert "panels" in dashboard, "Dashboard should have a 'panels' field"


def test_all_six_required_panels_exist():
    """Verify all 6 required panels exist."""
    dashboard = load_dashboard()
    panels = dashboard.get("panels", [])

    panel_titles = [panel.get("title") for panel in panels]
    panel_titles_set = set(panel_titles)

    missing_panels = []
    for expected in EXPECTED_PANELS:
        if expected not in panel_titles_set:
            missing_panels.append(expected)

    assert len(panels) == 6, (
        f"Expected 6 panels, got {len(panels)}. "
        f"Missing: {missing_panels}"
    )

    for expected in EXPECTED_PANELS:
        assert expected in panel_titles_set, f"Missing panel: {expected}"


def test_panel_queries_reference_correct_metrics():
    """Verify panel queries reference correct metric names from log_metrics_config.yaml."""
    dashboard = load_dashboard()
    panels = dashboard.get("panels", [])

    # Build a map of panel title -> panel
    panel_map = {panel.get("title"): panel for panel in panels}

    errors = []

    # Panel 1: GCL Error Rate should reference gcl_error_rate
    if "GCL Error Rate" in panel_map:
        targets = panel_map["GCL Error Rate"].get("targets", [])
        found_metric = False
        for target in targets:
            expr = target.get("expr", "")
            if "gcl_error_rate" in expr:
                found_metric = True
                break
        if not found_metric:
            errors.append("Panel 'GCL Error Rate' does not reference 'gcl_error_rate' metric")

    # Panel 2: Execution Latency should reference gcl_execution_latency
    if "Execution Latency" in panel_map:
        targets = panel_map["Execution Latency"].get("targets", [])
        found_metric = False
        for target in targets:
            expr = target.get("expr", "")
            if "gcl_execution_latency" in expr:
                found_metric = True
                break
        if not found_metric:
            errors.append("Panel 'Execution Latency' does not reference 'gcl_execution_latency' metric")

    # Panel 3: Safety Failures should reference gcl_safety_failures
    if "Safety Failures Over Time" in panel_map:
        targets = panel_map["Safety Failures Over Time"].get("targets", [])
        found_metric = False
        for target in targets:
            expr = target.get("expr", "")
            if "gcl_safety_failures" in expr:
                found_metric = True
                break
        if not found_metric:
            errors.append("Panel 'Safety Failures Over Time' does not reference 'gcl_safety_failures' metric")

    # Panel 4: Autonomy Ratio should reference gcl_autonomy_ratio
    if "Autonomy Ratio" in panel_map:
        targets = panel_map["Autonomy Ratio"].get("targets", [])
        found_metric = False
        for target in targets:
            expr = target.get("expr", "")
            if "gcl_autonomy_ratio" in expr:
                found_metric = True
                break
        if not found_metric:
            errors.append("Panel 'Autonomy Ratio' does not reference 'gcl_autonomy_ratio' metric")

    assert not errors, "Metric reference errors:\n" + "\n".join(errors)


def test_templating_has_project_id():
    """Verify dashboard has proper templating for project_id."""
    dashboard = load_dashboard()
    templating = dashboard.get("templating", {})

    assert "list" in templating, "Templating should have a 'list' field"

    variables = templating["list"]
    project_vars = [v for v in variables if v.get("name") == "project_id"]

    assert len(project_vars) == 1, "Dashboard should have exactly one variable named 'project_id'"

    project_var = project_vars[0]
    assert project_var.get("type") == "query", "project_id should be a query variable"
    assert project_var.get("query", {}).get("queryType") == "projects", (
        "project_id query type should be 'projects'"
    )


def test_autonomy_ratio_gauge_panel():
    """Verify the Autonomy Ratio panel is configured as a gauge with 0-1 range."""
    dashboard = load_dashboard()
    panels = dashboard.get("panels", [])

    autonomy_panel = None
    for panel in panels:
        if panel.get("title") == "Autonomy Ratio":
            autonomy_panel = panel
            break

    assert autonomy_panel is not None, "Autonomy Ratio panel not found"

    # Check it's a gauge type
    assert autonomy_panel.get("type") == "gauge", (
        f"Autonomy Ratio should be a gauge, got {autonomy_panel.get('type')}"
    )

    # Check field config has min=0 and max=1
    field_config = autonomy_panel.get("fieldConfig", {})
    defaults = field_config.get("defaults", {})

    assert defaults.get("min") == 0, "Autonomy Ratio gauge should have min=0"
    assert defaults.get("max") == 1, "Autonomy Ratio gauge should have max=1"


def test_results_breakdown_has_color_overrides():
    """Verify Results Breakdown panel has color overrides for PASS/MAX_ITER/SAFETY_FAIL."""
    dashboard = load_dashboard()
    panels = dashboard.get("panels", [])

    results_panel = None
    for panel in panels:
        if panel.get("title") == "Results Breakdown":
            results_panel = panel
            break

    assert results_panel is not None, "Results Breakdown panel not found"

    field_config = results_panel.get("fieldConfig", {})
    overrides = field_config.get("overrides", [])

    override_targets = set()
    for override in overrides:
        matcher = override.get("matcher", {})
        # options is a string like "PASS", "MAX_ITER", etc.
        options = matcher.get("options", "")
        if options in ["PASS", "MAX_ITER", "SAFETY_FAIL", "ERROR"]:
            override_targets.add(options)

    assert "PASS" in override_targets, "Results Breakdown should have green override for PASS"
    assert "MAX_ITER" in override_targets, "Results Breakdown should have yellow override for MAX_ITER"
    assert "SAFETY_FAIL" in override_targets, "Results Breakdown should have red override for SAFETY_FAIL"
    assert "ERROR" in override_targets, "Results Breakdown should have orange override for ERROR"


def test_dashboard_has_description():
    """Verify the dashboard has a meaningful description."""
    dashboard = load_dashboard()
    assert dashboard.get("description"), "Dashboard should have a description"
    assert "GCL" in dashboard.get("description", ""), (
        "Dashboard description should mention GCL"
    )
