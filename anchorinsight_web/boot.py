"""BOOT-0028 — Observable boot-event model for the AnchorInsight web adapter."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from threading import RLock
from typing import Any, Mapping


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BootEventStatus(StrEnum):
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class BootOverallStatus(StrEnum):
    INITIALIZING = "INITIALIZING"
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True, slots=True)
class BootEvent:
    sequence: int
    component: str
    stage: str
    status: BootEventStatus
    message: str
    occurred_at: str = field(default_factory=utc_now)
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "component": self.component,
            "stage": self.stage,
            "status": self.status.value,
            "message": self.message,
            "occurred_at": self.occurred_at,
            "details": dict(self.details),
        }


class BootStatusService:
    """Thread-safe recorder for real initialization events.

    The service records work that actually occurred. It does not synthesize
    progress events for presentation purposes.
    """

    VERSION = "1.0.0"

    def __init__(self) -> None:
        self._lock = RLock()
        self._events: list[BootEvent] = []
        self._started_at: str | None = None
        self._completed_at: str | None = None
        self._overall_status = BootOverallStatus.INITIALIZING

    def start(self) -> None:
        with self._lock:
            self._events.clear()
            self._started_at = utc_now()
            self._completed_at = None
            self._overall_status = BootOverallStatus.INITIALIZING

    def record(
        self,
        *,
        component: str,
        stage: str,
        status: BootEventStatus,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> BootEvent:
        with self._lock:
            event = BootEvent(
                sequence=len(self._events) + 1,
                component=component,
                stage=stage,
                status=status,
                message=message,
                details=dict(details or {}),
            )
            self._events.append(event)
            if status == BootEventStatus.FAILED:
                self._overall_status = BootOverallStatus.DEGRADED
            return event

    def complete(self) -> None:
        with self._lock:
            self._completed_at = utc_now()
            if any(event.status == BootEventStatus.FAILED for event in self._events):
                self._overall_status = BootOverallStatus.DEGRADED
            else:
                self._overall_status = BootOverallStatus.ONLINE

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            events = tuple(self._events)
            passed = sum(event.status == BootEventStatus.PASSED for event in events)
            failed = sum(event.status == BootEventStatus.FAILED for event in events)
            running = sum(event.status == BootEventStatus.RUNNING for event in events)
            return {
                "boot": "BOOT-0028",
                "service_version": self.VERSION,
                "status": self._overall_status.value,
                "started_at": self._started_at,
                "completed_at": self._completed_at,
                "summary": {
                    "events": len(events),
                    "passed": passed,
                    "failed": failed,
                    "running": running,
                },
                "events": [event.to_dict() for event in events],
            }
