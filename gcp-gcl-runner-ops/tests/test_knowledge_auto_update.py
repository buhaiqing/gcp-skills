"""
Tests for knowledge_auto_update module (P2-3).

TDD tests for:
- test_knowledge_ttl_expiration
- test_knowledge_version_rollback
- test_knowledge_conflict_detection
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from knowledge_auto_update import (
    ConflictInfo,
    KnowledgeAutoUpdater,
    KnowledgeEntry,
    KnowledgeTTLManager,
    KnowledgeVersionManager,
    VersionInfo,
)


class TestKnowledgeTTLManager:
    """Tests for KnowledgeTTLManager."""

    def test_knowledge_ttl_expiration(self) -> None:
        """Test that knowledge entries expire after TTL."""
        manager = KnowledgeTTLManager(default_ttl_days=30)

        # Add a knowledge entry
        entry = KnowledgeEntry(
            id="test-1",
            content={"key": "value"},
            created_at=datetime.now(UTC) - timedelta(days=31),
            ttl_days=30,
        )
        manager.add_entry(entry)

        # Should be expired
        assert manager.is_expired("test-1") is True

        # Add a fresh entry
        fresh_entry = KnowledgeEntry(
            id="test-2",
            content={"key": "value2"},
            created_at=datetime.now(UTC),
            ttl_days=30,
        )
        manager.add_entry(fresh_entry)

        # Should not be expired
        assert manager.is_expired("test-2") is False

    def test_ttl_refresh_on_access(self) -> None:
        """Test that accessing an entry refreshes its TTL."""
        manager = KnowledgeTTLManager(default_ttl_days=30)

        # Add an entry that's about to expire
        old_time = datetime.now(UTC) - timedelta(days=25)
        entry = KnowledgeEntry(
            id="test-3",
            content={"key": "value3"},
            created_at=old_time,
            ttl_days=30,
        )
        manager.add_entry(entry)

        # Not yet expired
        assert manager.is_expired("test-3") is False

        # Access the entry (this should refresh TTL if implemented)
        manager.touch_entry("test-3")

        # Should still not be expired after refresh
        assert manager.is_expired("test-3") is False

    def test_ttl_adjustment_based_on_usage(self) -> None:
        """Test that frequently used entries get extended TTL."""
        manager = KnowledgeTTLManager(default_ttl_days=30)

        entry = KnowledgeEntry(
            id="frequently-used",
            content={"key": "value"},
            created_at=datetime.now(UTC),
            ttl_days=30,
            access_count=100,
        )
        manager.add_entry(entry)

        # Adjust TTL based on usage
        manager.adjust_ttl_based_on_usage("frequently-used", usage_threshold=50)

        # TTL should be extended
        updated_entry = manager.get_entry("frequently-used")
        assert updated_entry is not None
        assert updated_entry.ttl_days == 60  # Doubled

    def test_get_expired_entries(self) -> None:
        """Test retrieval of all expired entries."""
        manager = KnowledgeTTLManager(default_ttl_days=30)

        # Add expired entry
        expired_entry = KnowledgeEntry(
            id="expired-1",
            content={"key": "value1"},
            created_at=datetime.now(UTC) - timedelta(days=60),
            ttl_days=30,
        )
        manager.add_entry(expired_entry)

        # Add fresh entry
        fresh_entry = KnowledgeEntry(
            id="fresh-1",
            content={"key": "value2"},
            created_at=datetime.now(UTC),
            ttl_days=30,
        )
        manager.add_entry(fresh_entry)

        expired = manager.get_expired_entries()
        assert len(expired) == 1
        assert expired[0].id == "expired-1"


class TestKnowledgeVersionManager:
    """Tests for KnowledgeVersionManager."""

    def test_knowledge_version_rollback(self) -> None:
        """Test rollback to a specific version."""
        manager = KnowledgeVersionManager()

        # Add initial version
        manager.add_version(
            entry_id="doc-1",
            content={"title": "Initial"},
            version=1,
        )

        # Add second version
        manager.add_version(
            entry_id="doc-1",
            content={"title": "Updated"},
            version=2,
        )

        # Add third version
        manager.add_version(
            entry_id="doc-1",
            content={"title": "Latest"},
            version=3,
        )

        # Rollback to version 1
        content = manager.rollback("doc-1", target_version=1)
        assert content == {"title": "Initial"}

        # Rollback to version 2
        content = manager.rollback("doc-1", target_version=2)
        assert content == {"title": "Updated"}

    def test_version_history(self) -> None:
        """Test retrieval of version history."""
        manager = KnowledgeVersionManager()

        # Add multiple versions
        for i in range(1, 4):
            manager.add_version(
                entry_id="doc-2",
                content={"version": i},
                version=i,
            )

        history = manager.get_version_history("doc-2")
        assert len(history) == 3
        assert history[0].version == 1
        assert history[-1].version == 3

    def test_version_diff(self) -> None:
        """Test comparison between versions."""
        manager = KnowledgeVersionManager()

        v1_content = {"title": "Hello", "body": "World"}
        v2_content = {"title": "Hello", "body": "Changed"}

        manager.add_version("doc-3", v1_content, version=1)
        manager.add_version("doc-3", v2_content, version=2)

        diff = manager.diff("doc-3", version_a=1, version_b=2)
        assert "body" in diff
        assert diff["body"]["old"] == "World"
        assert diff["body"]["new"] == "Changed"
        assert "title" not in diff  # Unchanged field


class TestKnowledgeAutoUpdater:
    """Tests for KnowledgeAutoUpdater."""

    def test_knowledge_conflict_detection(self) -> None:
        """Test detection of conflicting knowledge updates."""
        updater = KnowledgeAutoUpdater()

        # Simulate two concurrent updates to the same entry
        entry_id = "concurrent-doc"

        # First update from source A
        update_a = KnowledgeEntry(
            id=entry_id,
            content={"field": "value from A"},
            source="source-A",
            updated_at=datetime.now(UTC) - timedelta(seconds=10),
        )

        # Second update from source B (slightly later)
        update_b = KnowledgeEntry(
            id=entry_id,
            content={"field": "value from B"},
            source="source-B",
            updated_at=datetime.now(UTC),
        )

        # Register updates
        updater.register_update(update_a)
        updater.register_update(update_b)

        # Check for conflicts
        conflicts = updater.detect_conflicts(entry_id)
        assert len(conflicts) >= 1
        assert any(c.source_a == "source-A" and c.source_b == "source-B" for c in conflicts)

    def test_auto_update_with_ttl_check(self) -> None:
        """Test automatic update check includes TTL expiration."""
        updater = KnowledgeAutoUpdater()

        # Add an expired entry
        expired_entry = KnowledgeEntry(
            id="expired-doc",
            content={"key": "old value"},
            created_at=datetime.now(UTC) - timedelta(days=60),
            ttl_days=30,
        )
        updater.register_entry(expired_entry)

        # Check expired entries
        expired = updater.get_entries_needing_update()
        assert any(e.id == "expired-doc" for e in expired)

    def test_usage_based_ttl_adjustment(self) -> None:
        """Test that usage frequency affects TTL."""
        updater = KnowledgeAutoUpdater()

        # Add a high-usage entry
        high_usage_entry = KnowledgeEntry(
            id="popular-doc",
            content={"key": "popular content"},
            created_at=datetime.now(UTC) - timedelta(days=10),
            ttl_days=30,
            access_count=500,
        )
        updater.register_entry(high_usage_entry)

        # Trigger TTL adjustment based on usage
        updater.adjust_ttl_for_usage("popular-doc", high_usage_threshold=200)

        # Verify TTL was extended
        entry = updater.get_entry("popular-doc")
        assert entry is not None
        assert entry.ttl_days > 30

    def test_conflict_resolution_strategy(self) -> None:
        """Test different conflict resolution strategies."""
        updater = KnowledgeAutoUpdater()

        # Add conflicting entries
        entry1 = KnowledgeEntry(
            id="conflict-doc",
            content={"field": "value1"},
            source="source-1",
            updated_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        entry2 = KnowledgeEntry(
            id="conflict-doc",
            content={"field": "value2"},
            source="source-2",
            updated_at=datetime.now(UTC),
        )

        updater.register_update(entry1)
        updater.register_update(entry2)

        # Resolve with latest-wins strategy
        resolved = updater.resolve_conflict(
            "conflict-doc",
            strategy="latest",
        )
        assert resolved.content["field"] == "value2"

        # Resolve with source-priority strategy
        resolved = updater.resolve_conflict(
            "conflict-doc",
            strategy="source-priority",
            source_preference="source-1",
        )
        assert resolved.content["field"] == "value1"


class TestKnowledgeEntry:
    """Tests for KnowledgeEntry dataclass."""

    def test_entry_creation(self) -> None:
        """Test KnowledgeEntry creation with defaults."""
        entry = KnowledgeEntry(
            id="test-entry",
            content={"key": "value"},
        )

        assert entry.id == "test-entry"
        assert entry.content["key"] == "value"
        assert entry.created_at is not None
        assert entry.ttl_days == 30  # Default
        assert entry.access_count == 0  # Default

    def test_entry_with_all_fields(self) -> None:
        """Test KnowledgeEntry with all fields specified."""
        now = datetime.now(UTC)
        entry = KnowledgeEntry(
            id="full-entry",
            content={"key": "value"},
            created_at=now,
            updated_at=now,
            ttl_days=60,
            access_count=10,
            source="test-source",
            version=5,
        )

        assert entry.ttl_days == 60
        assert entry.access_count == 10
        assert entry.source == "test-source"
        assert entry.version == 5


class TestVersionInfo:
    """Tests for VersionInfo dataclass."""

    def test_version_info_creation(self) -> None:
        """Test VersionInfo creation."""
        info = VersionInfo(
            entry_id="doc-1",
            version=3,
            content={"key": "value3"},
            created_at=datetime.now(UTC),
            author="test",
        )

        assert info.entry_id == "doc-1"
        assert info.version == 3
        assert info.content["key"] == "value3"


class TestConflictInfo:
    """Tests for ConflictInfo dataclass."""

    def test_conflict_info_creation(self) -> None:
        """Test ConflictInfo creation."""
        info = ConflictInfo(
            entry_id="doc-1",
            source_a="source-A",
            source_b="source-B",
            content_a={"field": "valueA"},
            content_b={"field": "valueB"},
            detected_at=datetime.now(UTC),
        )

        assert info.entry_id == "doc-1"
        assert info.source_a == "source-A"
        assert info.source_b == "source-B"
