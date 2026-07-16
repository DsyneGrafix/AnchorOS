from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def generate_asset_id() -> str:
    """Generate a unique AnchorFiber asset identifier."""

    return str(uuid4())


def current_timestamp() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


@dataclass
class Asset:
    """Base class for every asset represented by AnchorFiber."""

    name: str
    asset_id: str = field(default_factory=generate_asset_id)
    status: str = "Active"
    created_at: datetime = field(default_factory=current_timestamp)
    updated_at: datetime = field(default_factory=current_timestamp)

    def update_status(self, new_status: str) -> None:
        """Update the asset status and modification timestamp."""

        self.status = new_status
        self.updated_at = current_timestamp()
