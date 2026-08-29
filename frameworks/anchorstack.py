from collections.abc import Mapping

from services.event import AnchorEvent
from services.eventbus import EventBus
from services.framework_identity import FrameworkIdentity
from core.module import Module
from core.service_registry import ServiceRegistry
from frameworks.anchorstack_validity import (
    ContinuationDetermination,
    ContinuationEvaluator,
    ContinuationSnapshot,
    Validity,
)


class AnchorStack(Module):
    """AnchorStack governance framework."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__("AnchorStack", "1.0.0")

        self.event_bus = event_bus
        self.continuation_evaluator = ContinuationEvaluator()

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

    def determine_continuation(
        self,
        *,
        execution_id: str,
        observed_at: str,
        dimensions: Mapping[str, str],
        safe_exit_available: bool,
        evidence_ids: tuple[str, ...] = (),
    ) -> ContinuationDetermination:
        """Determine and publish validity without selecting a response action."""

        snapshot = ContinuationSnapshot(
            execution_id=execution_id,
            observed_at=observed_at,
            dimensions={
                name: Validity(value)
                for name, value in dimensions.items()
            },
            safe_exit_available=safe_exit_available,
            evidence_ids=evidence_ids,
        )
        determination = self.continuation_evaluator.evaluate(snapshot)

        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type="anchorstack.continuation_validity.determined",
                message=(
                    "Continuation validity determined: "
                    f"{determination.state.value}."
                ),
                severity=(
                    "INFO"
                    if determination.continuation_valid
                    else "WARNING"
                ),
                payload=determination.to_payload(),
            )
        )

        return determination


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
