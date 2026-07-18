"""
Trigger Automation - GCP Cloud Functions trigger handling.

This module provides trigger event schemas and Cloud Functions for handling
various GCP trigger types (Scheduler, Pub/Sub, Webhook, Manual).
"""

from trigger_automation.schemas.trigger_event import (
    ManualTriggerData,
    ManualTriggerEvent,
    PubSubTriggerData,
    PubSubTriggerEvent,
    ScheduledTriggerData,
    ScheduledTriggerEvent,
    TriggerEvent,
    TriggerType,
    WebhookTriggerData,
    WebhookTriggerEvent,
)

__all__ = [
    "TriggerEvent",
    "TriggerType",
    "ScheduledTriggerData",
    "PubSubTriggerData",
    "ManualTriggerData",
    "WebhookTriggerData",
    "ScheduledTriggerEvent",
    "PubSubTriggerEvent",
    "WebhookTriggerEvent",
    "ManualTriggerEvent",
]
