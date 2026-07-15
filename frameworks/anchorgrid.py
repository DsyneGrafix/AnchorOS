from anchorcore.event import AnchorEvent
from anchorcore.eventbus import EventBus
from core.framework_identity import FrameworkIdentity
from core.module import Module
from core.service_registry import ServiceRegistry


class AnchorGrid(Module):
    """AnchorGrid critical-infrastructure framework."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__("AnchorGrid", "0.1.0")
        self.event_bus = event_bus

        self.identity = FrameworkIdentity(
            name=self.name,
            description="Critical Grid Infrastructure Intelligence",
            motto="Protect the Grid. Preserve Continuity.",
            version=self.version,
            status="Commissioned Skeleton",
        )

    def start(self) -> None:
        super().start()

        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type="framework.started",
                message="AnchorGrid entered the Running state.",
                severity="INFO",
                payload={
                    "framework_version": self.version,
                    "status": self.status,
                },
            )
        )

        self.identity.display()

    def stop(self) -> None:
        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type="framework.stopping",
                message="AnchorGrid is leaving the Running state.",
                severity="INFO",
            )
        )

        super().stop()


def create_module(
    registry: ServiceRegistry,
) -> AnchorGrid:
    """Create AnchorGrid using registered platform services."""

    event_bus = registry.require("Event Bus")

    if not isinstance(event_bus, EventBus):
        raise RuntimeError(
            "Registered Event Bus has an invalid type."
        )

    return AnchorGrid(event_bus=event_bus)
