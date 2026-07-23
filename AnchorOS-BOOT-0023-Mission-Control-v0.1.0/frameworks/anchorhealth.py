from services.event import AnchorEvent
from services.eventbus import EventBus
from services.framework_identity import FrameworkIdentity
from core.module import Module
from core.service_registry import ServiceRegistry


class AnchorHealth(Module):
    """AnchorHealth healthcare-operations framework."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__("AnchorHealth", "0.1.0")
        self.event_bus = event_bus

        self.identity = FrameworkIdentity(
            name=self.name,
            description="Healthcare Operational Intelligence",
            motto="Protect the Patient. Validate the Decision.",
            version=self.version,
            status="Commissioned Skeleton",
        )

    def start(self) -> None:
        super().start()

        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type="framework.started",
                message="AnchorHealth entered the Running state.",
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
                message="AnchorHealth is leaving the Running state.",
                severity="INFO",
            )
        )

        super().stop()


def create_module(
    registry: ServiceRegistry,
) -> AnchorHealth:
    """Create AnchorHealth using registered platform services."""

    event_bus = registry.require("Event Bus")

    if not isinstance(event_bus, EventBus):
        raise RuntimeError(
            "Registered Event Bus has an invalid type."
        )

    return AnchorHealth(event_bus=event_bus)
