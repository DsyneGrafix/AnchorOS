from typing import Any

from anchorcore.eventbus import EventBus
from core.module import Module


class AnchorStack(Module):
    """AnchorStack governance framework."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__("AnchorStack", "1.0.0")
        self.event_bus = event_bus

    def start(self) -> None:
        """Start AnchorStack and publish its lifecycle event."""

        super().start()

        self.event_bus.publish(
            event_name="framework.started",
            payload={
                "source": self.name,
                "event": "framework.started",
                "message": (
                    "AnchorStack entered the Running state."
                ),
            },
        )

    def stop(self) -> None:
        """Publish shutdown intent and stop AnchorStack."""

        self.event_bus.publish(
            event_name="framework.stopping",
            payload={
                "source": self.name,
                "event": "framework.stopping",
                "message": (
                    "AnchorStack is leaving the Running state."
                ),
            },
        )

        super().stop()


def create_module(context: dict[str, Any]) -> AnchorStack:
    """Create AnchorStack using AnchorCore messaging."""

    event_bus = context.get("Event Bus")

    if not isinstance(event_bus, EventBus):
        raise RuntimeError(
            "AnchorStack requires the AnchorCore Event Bus."
        )

    return AnchorStack(event_bus=event_bus)
