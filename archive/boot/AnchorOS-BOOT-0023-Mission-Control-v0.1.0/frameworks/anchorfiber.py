from services.event import AnchorEvent
from services.eventbus import EventBus
from services.framework_identity import FrameworkIdentity
from core.module import Module
from core.service_registry import ServiceRegistry


class AnchorFiber(Module):
    """AnchorFiber infrastructure framework."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__("AnchorFiber", "0.1.0")

        self.event_bus = event_bus

        self.identity = FrameworkIdentity(
            name=self.name,
            description="Fiber Infrastructure Intelligence",
            motto="Know the Network. Trust the Route.",
            version=self.version,
            status="Operational Skeleton",
        )

    def start(self) -> None:
        super().start()

        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type="framework.started",
                message="AnchorFiber entered the Running state.",
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
                message="AnchorFiber is leaving the Running state.",
                severity="INFO",
            )
        )

        super().stop()


def create_module(
    registry: ServiceRegistry,
) -> AnchorFiber:
    """Create AnchorFiber using registered platform services."""

    event_bus = registry.require("Event Bus")

    if not isinstance(event_bus, EventBus):
        raise RuntimeError(
            "Registered Event Bus has an invalid type."
        )

    return AnchorFiber(event_bus=event_bus)
