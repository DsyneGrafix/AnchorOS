from anchorcore.event import AnchorEvent
from anchorcore.eventbus import EventBus
from core.framework_identity import FrameworkIdentity
from core.module import Module
from core.service_registry import ServiceRegistry


class AnchorStack(Module):
    """AnchorStack governance framework."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__("AnchorStack", "1.0.0")

        self.event_bus = event_bus

        self.identity = FrameworkIdentity(
            name=self.name,
            description="Operational Governance Framework",
            motto=(
                "Execution must never outlive the conditions "
                "that justified it."
            ),
            version=self.version,
            status="Operational",
        )

    def start(self) -> None:
        super().start()

        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type="framework.started",
                message="AnchorStack entered the Running state.",
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
                message="AnchorStack is leaving the Running state.",
                severity="INFO",
            )
        )

        super().stop()


def create_module(
    registry: ServiceRegistry,
) -> AnchorStack:
    """Create AnchorStack using registered platform services."""

    event_bus = registry.require("Event Bus")

    if not isinstance(event_bus, EventBus):
        raise RuntimeError(
            "Registered Event Bus has an invalid type."
        )

    return AnchorStack(event_bus=event_bus)
