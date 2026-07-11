from datetime import datetime, timezone

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

    def get_records(self) -> list[dict[str, str]]:
        return self.records.copy()
