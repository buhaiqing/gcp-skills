"""
Main entry point for Trigger Automation Cloud Functions.

This module provides the hello_world function for basic testing
and health verification of the Cloud Functions deployment.
"""

from __future__ import annotations

import json
from typing import Any


def hello_world(request) -> tuple[Any, int]:
    """
    Hello World entry point for Trigger Automation.

    This function serves as a basic health check and can be used
    to verify the Cloud Functions deployment is working correctly.

    Args:
        request: The HTTP request object.

    Returns:
        A tuple of (response_body, status_code).
    """
    try:
        request_json = request.get_json(silent=True)
    except Exception:
        request_json = None

    response = {
        "status": "ok",
        "message": "Hello from Trigger Automation",
        "function": "hello_world",
        "version": "1.0.0",
    }

    if request_json:
        response["received_payload"] = request_json

    return (json.dumps(response), 200)
