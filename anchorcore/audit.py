from datetime import datetime, timezone
from typing import Any

from core.module import Module


class Audit(Module):
    """AnchorCore Audit Service."""

    def __init__(self) -> None:
        super().__init__("Audit Engine", "1.0.0")
        self.records: list[dict[str, str]] = []

    def log(
        self,
        source: str,
        event: str,
        message: str,
    ) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "event": event,
            "message": message,
        }

        self.records.append(record)

        print(
            f"✓ Audit: [{record['source']}] "
            f"{record['event']} — {record['message']}"
        )

    def handle_event(self, payload: dict[str, Any]) -> None:
        """Receive an Event Bus payload and preserve it as an audit record."""

        self.log(
            source=str(payload["source"]),
            event=str(payload["event"]),
            message=str(payload["message"]),
        )

    def get_records(self) -> list[dict[str, str]]:
        return self.records.copy()


def create_module(context: dict) -> Audit:
    """Create the AnchorCore Audit service."""

    return Audit()
