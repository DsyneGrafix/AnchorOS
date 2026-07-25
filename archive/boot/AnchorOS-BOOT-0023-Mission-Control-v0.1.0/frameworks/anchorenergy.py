from services.event import AnchorEvent
from services.eventbus import EventBus
from services.framework_identity import FrameworkIdentity
from core.module import Module
from core.service_registry import ServiceRegistry


class AnchorEnergy(Module):
    """AnchorEnergy energy-infrastructure framework."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__("AnchorEnergy", "0.1.0")
        self.event_bus = event_bus

        self.identity = FrameworkIdentity(
            name=self.name,
            description="Energy Infrastructure Intelligence",
            motto="Understand the System. Sustain the Flow.",
            version=self.version,
            status="Commissioned Skeleton",
        )

    def start(self) -> None:
        super().start()

        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type="framework.started",
                message="AnchorEnergy entered the Running state.",
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
                message="AnchorEnergy is leaving the Running state.",
                severity="INFO",
            )
        )

        super().stop()


def create_module(
    registry: ServiceRegistry,
) -> AnchorEnergy:
    """Create AnchorEnergy using registered platform services."""

    event_bus = registry.require("Event Bus")

    if not isinstance(event_bus, EventBus):
        raise RuntimeError(
            "Registered Event Bus has an invalid type."
        )

    return AnchorEnergy(event_bus=event_bus)
