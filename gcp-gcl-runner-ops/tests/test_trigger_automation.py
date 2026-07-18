#!/usr/bin/env python3
"""
Tests for Trigger Automation.

These tests define the expected schema and behavior for trigger events.
Run with: python -m pytest tests/test_trigger_automation.py -v
"""

from __future__ import annotations

from trigger_automation.schemas.trigger_event import (
    PubSubTriggerData,
    ScheduledTriggerData,
    TriggerEvent,
    TriggerType,
)


class TestTriggerEventSchemaValidation:
    """Test suite for TriggerEvent schema validation."""

    def test_trigger_event_base_fields(self) -> None:
        """Verify TriggerEvent base has required fields."""
        event = TriggerEvent(trigger_type=TriggerType.MANUAL)
        assert event.trigger_type == TriggerType.MANUAL
        assert event.event_id is not None
        assert event.timestamp is not None

    def test_scheduled_trigger_event(self) -> None:
        """Verify ScheduledTriggerEvent can be created with required fields."""
        from trigger_automation.schemas.trigger_event import ScheduledTriggerEvent

        event = ScheduledTriggerEvent(
            trigger_type=TriggerType.SCHEDULED,
            job_name="daily-health-check",
            schedule="0 2 * * *",  # 2 AM daily
            time_zone="America/New_York",
        )

        assert event.trigger_type == TriggerType.SCHEDULED
        assert event.job_name == "daily-health-check"
        assert event.schedule == "0 2 * * *"
        assert event.time_zone == "America/New_York"
        assert event.event_id is not None
        assert event.timestamp is not None

    def test_pubsub_trigger_event(self) -> None:
        """Verify PubSubTriggerEvent can be created with required fields."""
        from trigger_automation.schemas.trigger_event import PubSubTriggerEvent

        event = PubSubTriggerEvent(
            trigger_type=TriggerType.PUB_SUB,
            subscription="projects/my-project/subscriptions/gcl-trigger-sub",
            message_id="abc123",
            publish_time="2026-07-19T10:00:00Z",
            attributes={"source": "gcl-runner"},
        )

        assert event.trigger_type == TriggerType.PUB_SUB
        assert event.subscription == "projects/my-project/subscriptions/gcl-trigger-sub"
        assert event.message_id == "abc123"
        assert event.publish_time == "2026-07-19T10:00:00Z"
        assert event.attributes == {"source": "gcl-runner"}
        assert event.event_id is not None

    def test_webhook_trigger_event(self) -> None:
        """Verify WebhookTriggerEvent can be created with required fields."""
        from trigger_automation.schemas.trigger_event import WebhookTriggerEvent

        event = WebhookTriggerEvent(
            trigger_type=TriggerType.WEBHOOK,
            source_ip="192.168.1.1",
            headers={"Content-Type": "application/json"},
            payload={"action": "trigger"},
        )

        assert event.trigger_type == TriggerType.WEBHOOK
        assert event.source_ip == "192.168.1.1"
        assert event.headers == {"Content-Type": "application/json"}
        assert event.payload == {"action": "trigger"}
        assert event.event_id is not None

    def test_manual_trigger_event(self) -> None:
        """Verify ManualTriggerEvent can be created with required fields."""
        from trigger_automation.schemas.trigger_event import ManualTriggerEvent

        event = ManualTriggerEvent(
            trigger_type=TriggerType.MANUAL,
            triggered_by="user@example.com",
        )

        assert event.trigger_type == TriggerType.MANUAL
        assert event.triggered_by == "user@example.com"
        assert event.event_id is not None

    def test_scheduled_trigger_data_fields(self) -> None:
        """Verify ScheduledTriggerData has expected fields."""
        data = ScheduledTriggerData(
            job_name="test-job",
            schedule="0 0 * * *",
            time_zone="UTC",
        )
        assert data.job_name == "test-job"
        assert data.schedule == "0 0 * * *"
        assert data.time_zone == "UTC"

    def test_pubsub_trigger_data_fields(self) -> None:
        """Verify PubSubTriggerData has expected fields."""
        data = PubSubTriggerData(
            subscription="projects/test/subscriptions/test-sub",
            message_id="msg-123",
            publish_time="2026-07-19T00:00:00Z",
            attributes={"key": "value"},
        )
        assert data.subscription == "projects/test/subscriptions/test-sub"
        assert data.message_id == "msg-123"
        assert data.publish_time == "2026-07-19T00:00:00Z"
        assert data.attributes == {"key": "value"}

    def test_trigger_event_serialization(self) -> None:
        """Verify TriggerEvent can be serialized to dict."""
        from trigger_automation.schemas.trigger_event import ScheduledTriggerEvent

        event = ScheduledTriggerEvent(
            trigger_type=TriggerType.SCHEDULED,
            job_name="daily-health-check",
            schedule="0 2 * * *",
            time_zone="America/New_York",
        )

        serialized = event.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["trigger_type"] == "SCHEDULED"
        assert serialized["job_name"] == "daily-health-check"
        assert "event_id" in serialized
        assert "timestamp" in serialized

    def test_trigger_event_deserialization(self) -> None:
        """Verify TriggerEvent can be deserialized from dict."""
        from trigger_automation.schemas.trigger_event import PubSubTriggerEvent

        data = {
            "trigger_type": "PUB_SUB",
            "subscription": "projects/test/subscriptions/test-sub",
            "message_id": "msg-456",
            "publish_time": "2026-07-19T12:00:00Z",
            "attributes": {"env": "prod"},
        }

        event = PubSubTriggerEvent(**data)
        assert event.trigger_type == TriggerType.PUB_SUB
        assert event.subscription == "projects/test/subscriptions/test-sub"
        assert event.message_id == "msg-456"

    def test_trigger_type_enum_values(self) -> None:
        """Verify TriggerType enum has expected values."""
        assert TriggerType.SCHEDULED.value == "SCHEDULED"
        assert TriggerType.PUB_SUB.value == "PUB_SUB"
        assert TriggerType.WEBHOOK.value == "WEBHOOK"
        assert TriggerType.MANUAL.value == "MANUAL"


class TestTriggerFunctions:
    """Test suite for trigger Cloud Functions."""

    def test_hello_world_entry_point_exists(self) -> None:
        """Verify hello_world function exists and is callable."""
        from trigger_automation.functions import main

        assert hasattr(main, "hello_world")
        assert callable(main.hello_world)

    def test_scheduler_trigger_handler_exists(self) -> None:
        """Verify scheduler_trigger function exists and is callable."""
        from trigger_automation.functions import scheduler_trigger

        assert hasattr(scheduler_trigger, "handle_scheduler_event")
        assert callable(scheduler_trigger.handle_scheduler_event)

    def test_pubsub_trigger_handler_exists(self) -> None:
        """Verify pubsub_trigger function exists and is callable."""
        from trigger_automation.functions import pubsub_trigger

        assert hasattr(pubsub_trigger, "handle_pubsub_event")
        assert callable(pubsub_trigger.handle_pubsub_event)
