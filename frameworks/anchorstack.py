from typing import Any

from anchorcore.event import AnchorEvent
from anchorcore.eventbus import EventBus
from core.module import Module


class AnchorStack(Module):
    """AnchorStack governance framework."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__("AnchorStack", "1.0.0")
        self.event_bus = event_bus

    def start(self) -> None:
        super().start()

        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type="framework.started",
                message=(
                    "AnchorStack entered the Running state."
                ),
                severity="INFO",
                payload={
                    "framework_version": self.version,
                    "status": self.status,
                },
            )
        )

    def stop(self) -> None:
        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type="framework.stopping",
                message=(
                    "AnchorStack is leaving the Running state."
                ),
                severity="INFO",
            )
        )

        super().stop()


def create_module(
    context: dict[str, Any],
) -> AnchorStack:
    event_bus = context.get("Event Bus")

    if not isinstance(event_bus, EventBus):
        raise RuntimeError(
            "AnchorStack requires the AnchorCore Event Bus."
        )

    return AnchorStack(event_bus=event_bus)
