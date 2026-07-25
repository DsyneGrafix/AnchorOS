from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class AnchorEvent:
    """First-class AnchorOS platform event."""

    source: str
    event_type: str
    message: str
    severity: str = "INFO"
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(
        default_factory=lambda: str(uuid4())
    )
    timestamp: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )
