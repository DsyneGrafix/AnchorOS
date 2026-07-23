from __future__ import annotations

from typing import Any

from core.module import Module
from core.service_registry import ServiceRegistry
from services.audit import Audit
from services.event import AnchorEvent
from services.eventbus import EventBus

from .runtime import MissionControlRuntime
from .web import MissionControlServer


class MissionControl(Module):
    """The operational face of AnchorOS."""

    EVENT_TYPES = (
        "service.started",
        "framework.started",
        "application.started",
        "application.stopped",
        "audit.recorded",
        "health.updated",
        "pipeline.completed",
    )

    def __init__(
        self,
        *,
        event_bus: EventBus,
        audit: Audit,
        host: str = "127.0.0.1",
        port: int = 8080,
    ) -> None:
        super().__init__("Mission Control", "0.1.0")
        self.event_bus = event_bus
        self.audit = audit
        self.runtime = MissionControlRuntime()
        self.server = MissionControlServer(self.runtime, host, port)
        for event_type in self.EVENT_TYPES:
            self.event_bus.subscribe(event_type, self.runtime.handle_event)

    @property
    def url(self) -> str:
        return self.server.url

    def set_snapshot_provider(self, provider: Any) -> None:
        self.runtime.set_snapshot_provider(provider)

    def start(self) -> None:
        self.server.start()
        super().start()
        event = AnchorEvent(
            source=self.name,
            event_type="application.started",
            message=f"Mission Control is running at {self.url}.",
            payload={"url": self.url, "version": self.version, "status": self.status},
        )
        self.event_bus.publish(event)

    def stop(self) -> None:
        event = AnchorEvent(
            source=self.name,
            event_type="application.stopped",
            message="Mission Control is stopping.",
            payload={"url": self.url},
        )
        self.event_bus.publish(event)
        self.server.stop()
        super().stop()

    def health(self) -> dict[str, str]:
        data = super().health()
        data["url"] = self.url
        return data


def create_module(registry: ServiceRegistry) -> MissionControl:
    event_bus = registry.require("Event Bus")
    audit = registry.require("Audit Engine")
    if not isinstance(event_bus, EventBus) or not isinstance(audit, Audit):
        raise RuntimeError("Mission Control requires the Event Bus and Audit Engine.")
    return MissionControl(event_bus=event_bus, audit=audit)
