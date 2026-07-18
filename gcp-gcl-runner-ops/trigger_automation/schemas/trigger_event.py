"""
Pydantic models for trigger events.

Defines the schema for different trigger types:
- SCHEDULED: Cloud Scheduler triggered events
- PUB_SUB: Cloud Pub/Sub message events
- WEBHOOK: HTTP webhook triggered events
- MANUAL: Manually triggered events
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    """Enumeration of supported trigger types."""

    SCHEDULED = "SCHEDULED"
    PUB_SUB = "PUB_SUB"
    WEBHOOK = "WEBHOOK"
    MANUAL = "MANUAL"


class TriggerEvent(BaseModel):
    """
    Base model for all trigger events.

    This class should not be instantiated directly - use concrete subclasses.
    """

    trigger_type: TriggerType
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    model_config = {"extra": "forbid"}

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """Serialize to dict with trigger_type as string value."""
        data = super().model_dump(**kwargs)
        data["trigger_type"] = self.trigger_type.value
        return data


class ScheduledTriggerEvent(TriggerEvent):
    """Trigger event for Cloud Scheduler."""

    trigger_type: TriggerType = TriggerType.SCHEDULED
    job_name: str = Field(..., description="Name of the Cloud Scheduler job")
    schedule: str = Field(..., description="Cron schedule expression")
    time_zone: str = Field(default="UTC", description="Time zone for the schedule")


class PubSubTriggerEvent(TriggerEvent):
    """Trigger event for Cloud Pub/Sub."""

    trigger_type: TriggerType = TriggerType.PUB_SUB
    subscription: str = Field(..., description="Full Pub/Sub subscription path")
    message_id: str = Field(..., description="Unique message identifier")
    publish_time: str = Field(..., description="Message publish timestamp (ISO 8601)")
    attributes: dict[str, str] = Field(default_factory=dict, description="Message attributes")


class WebhookTriggerEvent(TriggerEvent):
    """Trigger event for webhook triggers."""

    trigger_type: TriggerType = TriggerType.WEBHOOK
    source_ip: str = Field(..., description="Source IP address of the webhook request")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    payload: dict[str, Any] = Field(default_factory=dict, description="Request payload")


class ManualTriggerEvent(TriggerEvent):
    """Trigger event for manual triggers."""

    trigger_type: TriggerType = TriggerType.MANUAL
    triggered_by: str = Field(..., description="Email of the user who triggered manually")


# Aliases for backward compatibility
ScheduledTriggerData = ScheduledTriggerEvent
PubSubTriggerData = PubSubTriggerEvent
ManualTriggerData = ManualTriggerEvent
WebhookTriggerData = WebhookTriggerEvent
