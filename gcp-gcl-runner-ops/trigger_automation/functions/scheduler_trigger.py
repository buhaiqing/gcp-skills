"""
Cloud Scheduler trigger handler for Trigger Automation.

This module handles events triggered by Cloud Scheduler jobs,
typically used for periodic tasks like daily health checks,
periodic GCL runs, and scheduled maintenance tasks.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from trigger_automation.schemas.trigger_event import (
    ScheduledTriggerData,
    ScheduledTriggerEvent,
    TriggerType,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_scheduler_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    Handle a Cloud Scheduler trigger event.

    Args:
        event: The Cloud Scheduler event payload containing:
            - job_name: Name of the scheduler job
            - schedule: Cron schedule expression
            - time_zone: Time zone for the schedule
            - custom_data: Optional additional data

    Returns:
        A dict containing the processed event result.
    """
    logger.info(f"Received scheduler event: {event}")

    try:
        trigger_data = ScheduledTriggerData(
            job_name=event.get("job_name", "unknown"),
            schedule=event.get("schedule", "* * * * *"),
            time_zone=event.get("time_zone", "UTC"),
        )

        trigger_event = ScheduledTriggerEvent(
            trigger_type=TriggerType.SCHEDULED,
            data=trigger_data,
        )

        result = {
            "status": "processed",
            "event_id": trigger_event.event_id,
            "trigger_type": trigger_event.trigger_type.value,
            "job_name": trigger_event.job_name,
            "schedule": trigger_event.schedule,
            "time_zone": trigger_event.time_zone,
            "timestamp": trigger_event.timestamp,
        }

        logger.info(f"Successfully processed scheduler event: {trigger_event.event_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing scheduler event: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }


# Cloud Functions entry point wrapper
def cloud_function_entry_point(event, context) -> tuple[str, int]:
    """
    Cloud Functions entry point for Cloud Scheduler.

    Args:
        event: The event payload from Cloud Scheduler.
        context: The context object containing event metadata.

    Returns:
        A tuple of (response_body, status_code).
    """
    result = handle_scheduler_event(event)
    status_code = 200 if result.get("status") == "processed" else 500
    return (json.dumps(result), status_code)
