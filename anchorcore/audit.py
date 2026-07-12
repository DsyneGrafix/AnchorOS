from anchorcore.event import AnchorEvent
from core.module import Module


class Audit(Module):
    """AnchorCore Audit Service."""

    def __init__(self) -> None:
        super().__init__("Audit Engine", "1.0.0")
        self.records: list[dict[str, object]] = []

    def handle_event(self, event: AnchorEvent) -> None:
        """Preserve a structured Anchor Event."""

        record = {
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "source": event.source,
            "event_type": event.event_type,
            "severity": event.severity,
            "message": event.message,
            "payload": event.payload.copy(),
        }

        self.records.append(record)

        print(
            f"✓ Audit: [{event.source}] "
            f"{event.event_type} — {event.message}"
        )

    def get_records(self) -> list[dict[str, object]]:
        return [record.copy() for record in self.records]


def create_module(context: dict) -> Audit:
    return Audit()
