"""
Cloud Pub/Sub trigger handler for Trigger Automation.

This module handles events delivered via Cloud Pub/Sub subscriptions,
used for event-driven GCL execution, async task processing,
and integration with external systems.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import UTC, datetime
from typing import Any

from trigger_automation.schemas.trigger_event import (
    PubSubTriggerData,
    PubSubTriggerEvent,
    TriggerType,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_pubsub_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    Handle a Cloud Pub/Sub trigger event.

    Args:
        event: The Pub/Sub event payload containing:
            - subscription: Full subscription path
            - message: The message data (base64 encoded or plain)
            - attributes: Optional message attributes

    Returns:
        A dict containing the processed event result.
    """
    logger.info(f"Received pubsub event: {event}")

    try:
        message = event.get("message", {})
        data_attr = message.get("data", "")
        attributes = message.get("attributes", {})

        if isinstance(data_attr, str):
            try:
                decoded_data = base64.b64decode(data_attr).decode("utf-8")
                payload = json.loads(decoded_data)
            except Exception:
                payload = {"raw": data_attr}
        else:
            payload = data_attr

        trigger_data = PubSubTriggerData(
            subscription=event.get("subscription", "unknown"),
            message_id=message.get("messageId", "unknown"),
            publish_time=message.get("publishTime", datetime.now(UTC).isoformat()),
            attributes=attributes,
        )

        trigger_event = PubSubTriggerEvent(
            trigger_type=TriggerType.PUB_SUB,
            data=trigger_data,
        )

        result = {
            "status": "processed",
            "event_id": trigger_event.event_id,
            "trigger_type": trigger_event.trigger_type.value,
            "subscription": trigger_event.subscription,
            "message_id": trigger_event.message_id,
            "publish_time": trigger_event.publish_time,
            "attributes": trigger_event.attributes,
            "payload": payload,
            "timestamp": trigger_event.timestamp,
        }

        logger.info(f"Successfully processed pubsub event: {trigger_event.event_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing pubsub event: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }


# Cloud Functions entry point wrapper
def cloud_function_entry_point(event, context) -> tuple[str, int]:
    """
    Cloud Functions entry point for Cloud Pub/Sub.

    Args:
        event: The event payload from Pub/Sub.
        context: The context object containing event metadata.

    Returns:
        A tuple of (response_body, status_code).
    """
    result = handle_pubsub_event(event)
    status_code = 200 if result.get("status") == "processed" else 500
    return (json.dumps(result), status_code)
