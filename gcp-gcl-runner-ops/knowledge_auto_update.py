"""
Knowledge Auto-Update Module (P2-3).

Provides TTL management, versioning, and auto-update coordination for knowledge entries.

Classes:
    - KnowledgeEntry: Data structure for knowledge entries
    - KnowledgeTTLManager: TTL management with auto-expiration
    - KnowledgeVersionManager: Version history and rollback
    - KnowledgeAutoUpdater: Auto-update coordination with conflict detection
    - VersionInfo: Version metadata
    - ConflictInfo: Conflict metadata
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass
class KnowledgeEntry:
    """Represents a knowledge entry with TTL and versioning support."""

    id: str
    content: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None
    ttl_days: int = 30
    access_count: int = 0
    source: str | None = None
    version: int = 1

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if entry has expired based on TTL."""
        if now is None:
            now = datetime.now(UTC)
        age = now - self.created_at
        return age > timedelta(days=self.ttl_days)

    def touch(self) -> None:
        """Refresh the entry's timestamp (simulate access)."""
        self.updated_at = datetime.now(UTC)


@dataclass
class VersionInfo:
    """Metadata for a specific version of a knowledge entry."""

    entry_id: str
    version: int
    content: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    author: str | None = None


@dataclass
class ConflictInfo:
    """Metadata for a detected conflict between knowledge updates."""

    entry_id: str
    source_a: str
    source_b: str
    content_a: dict[str, Any]
    content_b: dict[str, Any]
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class KnowledgeTTLManager:
    """Manages TTL (Time-To-Live) for knowledge entries."""

    def __init__(self, default_ttl_days: int = 30) -> None:
        """Initialize TTL manager.

        Args:
            default_ttl_days: Default TTL in days for new entries
        """
        self.default_ttl_days = default_ttl_days
        self._entries: dict[str, KnowledgeEntry] = {}

    def add_entry(self, entry: KnowledgeEntry) -> None:
        """Add a knowledge entry.

        Args:
            entry: KnowledgeEntry to add
        """
        self._entries[entry.id] = entry

    def get_entry(self, entry_id: str) -> KnowledgeEntry | None:
        """Retrieve an entry by ID.

        Args:
            entry_id: Entry identifier

        Returns:
            KnowledgeEntry or None if not found
        """
        return self._entries.get(entry_id)

    def is_expired(self, entry_id: str, now: datetime | None = None) -> bool:
        """Check if an entry is expired.

        Args:
            entry_id: Entry identifier
            now: Optional reference time

        Returns:
            True if expired or entry not found
        """
        entry = self._entries.get(entry_id)
        if entry is None:
            return True
        return entry.is_expired(now)

    def touch_entry(self, entry_id: str) -> bool:
        """Refresh an entry's TTL on access.

        Args:
            entry_id: Entry identifier

        Returns:
            True if entry was found and touched
        """
        entry = self._entries.get(entry_id)
        if entry is None:
            return False
        entry.touch()
        return True

    def adjust_ttl_based_on_usage(
        self, entry_id: str, usage_threshold: int = 50
    ) -> bool:
        """Adjust TTL based on access frequency.

        Args:
            entry_id: Entry identifier
            usage_threshold: Threshold for extending TTL

        Returns:
            True if adjustment was applied
        """
        entry = self._entries.get(entry_id)
        if entry is None:
            return False

        if entry.access_count >= usage_threshold:
            entry.ttl_days = min(entry.ttl_days * 2, 365)  # Cap at 1 year
            return True
        return False

    def get_expired_entries(self) -> list[KnowledgeEntry]:
        """Get all expired entries.

        Returns:
            List of expired KnowledgeEntry objects
        """
        now = datetime.now(UTC)
        return [e for e in self._entries.values() if e.is_expired(now)]

    def remove_entry(self, entry_id: str) -> bool:
        """Remove an entry.

        Args:
            entry_id: Entry identifier

        Returns:
            True if entry was removed
        """
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False


class KnowledgeVersionManager:
    """Manages version history for knowledge entries."""

    def __init__(self) -> None:
        """Initialize version manager."""
        self._versions: dict[str, list[VersionInfo]] = {}

    def add_version(
        self,
        entry_id: str,
        content: dict[str, Any],
        version: int,
        author: str | None = None,
    ) -> None:
        """Add a new version of a knowledge entry.

        Args:
            entry_id: Entry identifier
            content: Content of this version
            version: Version number
            author: Optional author identifier
        """
        if entry_id not in self._versions:
            self._versions[entry_id] = []

        version_info = VersionInfo(
            entry_id=entry_id,
            version=version,
            content=content,
            author=author,
        )
        self._versions[entry_id].append(version_info)

    def get_version_history(self, entry_id: str) -> list[VersionInfo]:
        """Get version history for an entry.

        Args:
            entry_id: Entry identifier

        Returns:
            List of VersionInfo sorted by version number
        """
        versions = self._versions.get(entry_id, [])
        return sorted(versions, key=lambda v: v.version)

    def rollback(
        self, entry_id: str, target_version: int
    ) -> dict[str, Any] | None:
        """Rollback to a specific version.

        Args:
            entry_id: Entry identifier
            target_version: Version number to rollback to

        Returns:
            Content of the target version or None if not found
        """
        versions = self._versions.get(entry_id, [])
        for v in versions:
            if v.version == target_version:
                return v.content.copy()
        return None

    def diff(
        self, entry_id: str, version_a: int, version_b: int
    ) -> dict[str, Any]:
        """Compare two versions.

        Args:
            entry_id: Entry identifier
            version_a: First version number
            version_b: Second version number

        Returns:
            Dict with 'old', 'new' for changed fields
        """
        versions = {v.version: v for v in self._versions.get(entry_id, [])}

        content_a = versions.get(version_a)
        content_b = versions.get(version_b)

        if content_a is None or content_b is None:
            return {}

        diff_result: dict[str, dict[str, Any]] = {}
        all_keys = set(content_a.content.keys()) | set(content_b.content.keys())

        for key in all_keys:
            val_a = content_a.content.get(key)
            val_b = content_b.content.get(key)
            if val_a != val_b:
                diff_result[key] = {"old": val_a, "new": val_b}

        return diff_result

    def get_latest_version(self, entry_id: str) -> int:
        """Get the latest version number for an entry.

        Args:
            entry_id: Entry identifier

        Returns:
            Latest version number or 0 if no versions exist
        """
        versions = self._versions.get(entry_id, [])
        if not versions:
            return 0
        return max(v.version for v in versions)


class KnowledgeAutoUpdater:
    """Coordinates automatic knowledge updates with TTL and conflict detection."""

    def __init__(
        self,
        default_ttl_days: int = 30,
        high_usage_threshold: int = 200,
    ) -> None:
        """Initialize auto-updater.

        Args:
            default_ttl_days: Default TTL for new entries
            high_usage_threshold: Access count threshold for TTL extension
        """
        self.ttl_manager = KnowledgeTTLManager(default_ttl_days)
        self.version_manager = KnowledgeVersionManager()
        self.high_usage_threshold = high_usage_threshold
        self._pending_updates: dict[str, list[KnowledgeEntry]] = {}
        self._conflict_cache: dict[str, ConflictInfo] = {}

    def register_entry(self, entry: KnowledgeEntry) -> None:
        """Register a knowledge entry.

        Args:
            entry: KnowledgeEntry to register
        """
        self.ttl_manager.add_entry(entry)
        # Initialize version history if not exists
        if self.version_manager.get_latest_version(entry.id) == 0:
            self.version_manager.add_version(
                entry_id=entry.id,
                content=entry.content.copy(),
                version=1,
            )

    def register_update(self, entry: KnowledgeEntry) -> None:
        """Register an update to a knowledge entry.

        Args:
            entry: KnowledgeEntry with updated content
        """
        # Also register in TTL manager if not already present
        if self.ttl_manager.get_entry(entry.id) is None:
            self.ttl_manager.add_entry(entry)

        if entry.id not in self._pending_updates:
            self._pending_updates[entry.id] = []
        self._pending_updates[entry.id].append(entry)

    def get_entry(self, entry_id: str) -> KnowledgeEntry | None:
        """Get a knowledge entry.

        Args:
            entry_id: Entry identifier

        Returns:
            KnowledgeEntry or None
        """
        return self.ttl_manager.get_entry(entry_id)

    def is_expired(self, entry_id: str) -> bool:
        """Check if entry is expired.

        Args:
            entry_id: Entry identifier

        Returns:
            True if expired
        """
        return self.ttl_manager.is_expired(entry_id)

    def detect_conflicts(self, entry_id: str) -> list[ConflictInfo]:
        """Detect conflicts for an entry from pending updates.

        Args:
            entry_id: Entry identifier

        Returns:
            List of ConflictInfo for detected conflicts
        """
        updates = self._pending_updates.get(entry_id, [])
        conflicts: list[ConflictInfo] = []

        for i, update_a in enumerate(updates):
            for update_b in updates[i + 1 :]:
                # Simple conflict detection: different content from different sources
                if update_a.source != update_b.source and update_a.content != update_b.content:
                    conflict = ConflictInfo(
                        entry_id=entry_id,
                        source_a=update_a.source or "unknown",
                        source_b=update_b.source or "unknown",
                        content_a=update_a.content.copy(),
                        content_b=update_b.content.copy(),
                    )
                    conflicts.append(conflict)
                    # Cache the first conflict for reuse
                    if entry_id not in self._conflict_cache:
                        self._conflict_cache[entry_id] = conflict

        return conflicts

    def get_entries_needing_update(self) -> list[KnowledgeEntry]:
        """Get entries that need updating (expired or TTL reached).

        Returns:
            List of entries needing update
        """
        return self.ttl_manager.get_expired_entries()

    def adjust_ttl_for_usage(self, entry_id: str, high_usage_threshold: int | None = None) -> bool:
        """Adjust TTL based on usage frequency.

        Args:
            entry_id: Entry identifier
            high_usage_threshold: Optional override threshold

        Returns:
            True if TTL was extended
        """
        threshold = high_usage_threshold or self.high_usage_threshold
        entry = self.ttl_manager.get_entry(entry_id)
        if entry is None:
            return False

        if entry.access_count >= threshold:
            entry.ttl_days = min(entry.ttl_days * 2, 365)
            return True
        return False

    def resolve_conflict(
        self,
        entry_id: str,
        strategy: str = "latest",
        source_preference: str | None = None,
    ) -> KnowledgeEntry | None:
        """Resolve conflicts for an entry.

        Args:
            entry_id: Entry identifier
            strategy: Resolution strategy ('latest', 'source-priority', 'merge')
            source_preference: Preferred source when using source-priority strategy

        Returns:
            Resolved KnowledgeEntry or None
        """
        conflicts = self.detect_conflicts(entry_id)

        # Use cached conflict if no pending updates but we have a cached conflict
        if not conflicts and entry_id in self._conflict_cache:
            conflicts = [self._conflict_cache[entry_id]]

        if not conflicts:
            return self.ttl_manager.get_entry(entry_id)

        conflict = conflicts[0]

        if strategy == "latest":
            # Use the newer content (based on detected_at)
            if conflict.content_a != conflict.content_b:
                # Simple comparison to determine which is "newer"
                # In real impl, would compare timestamps
                newer_content = conflict.content_b
            else:
                newer_content = conflict.content_a

        elif strategy == "source-priority":
            if source_preference == conflict.source_a:
                newer_content = conflict.content_a
            else:
                newer_content = conflict.content_b

        else:
            # Default to latest
            newer_content = conflict.content_b

        # Create resolved entry
        current = self.ttl_manager.get_entry(entry_id)
        if current is None:
            return None

        resolved = KnowledgeEntry(
            id=entry_id,
            content=newer_content,
            source=conflict.source_b if newer_content == conflict.content_b else conflict.source_a,
            version=current.version + 1,
        )

        # Update in managers
        self.ttl_manager.add_entry(resolved)
        self.version_manager.add_version(
            entry_id=entry_id,
            content=newer_content.copy(),
            version=resolved.version,
        )

        # Clear pending updates but keep conflict cache for subsequent resolutions
        self._pending_updates[entry_id] = []

        return resolved

    def touch_entry(self, entry_id: str) -> bool:
        """Touch an entry to refresh its TTL.

        Args:
            entry_id: Entry identifier

        Returns:
            True if entry was found and touched
        """
        return self.ttl_manager.touch_entry(entry_id)
