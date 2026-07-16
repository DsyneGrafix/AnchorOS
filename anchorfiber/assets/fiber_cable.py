from dataclasses import dataclass
from datetime import date

from anchorfiber.assets.asset import Asset


@dataclass
class FiberCable(Asset):
    """Represents a fiber-optic cable in the network."""

    fiber_count: int = 0
    cable_type: str = ""
    owner: str = ""
    installed_date: date | None = None
    route_id: str = ""
