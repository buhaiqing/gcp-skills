"""
Pytest configuration for GCL Runner tests.

This conftest.py sets up the Python path so that tests can import
from the scripts module correctly.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the gcp-gcl-runner-ops directory to sys.path so that
# 'scripts' can be imported as a module
GCL_RUNNER_OPS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(GCL_RUNNER_OPS_DIR))
