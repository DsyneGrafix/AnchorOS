from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Callable

from services.event import AnchorEvent

SnapshotProvider = Callable[[], dict[str, Any]]


class MissionControlRuntime:
    """Thread-safe platform snapshot and event cache for Mission Control."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._snapshot_provider: SnapshotProvider | None = None
        self._events: list[dict[str, Any]] = []
        self._sequence = 0

    def set_snapshot_provider(self, provider: SnapshotProvider) -> None:
        with self._lock:
            self._snapshot_provider = provider

    def handle_event(self, event: AnchorEvent) -> None:
        record = {
            "sequence": self._sequence + 1,
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "source": event.source,
            "event_type": event.event_type,
            "severity": event.severity,
            "message": event.message,
            "payload": deepcopy(event.payload),
        }
        with self._lock:
            self._sequence += 1
            record["sequence"] = self._sequence
            self._events.append(record)
            self._events = self._events[-250:]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            provider = self._snapshot_provider
        data = provider() if provider is not None else {}
        data["recent_events"] = self.events(limit=25)
        return data

    def events(self, *, after: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            records = [event for event in self._events if event["sequence"] > after]
            return deepcopy(records[-limit:])
