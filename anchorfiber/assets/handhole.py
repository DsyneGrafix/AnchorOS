from dataclasses import dataclass

from anchorfiber.assets.asset import Asset


@dataclass
class Handhole(Asset):
    """Represents an underground fiber-access structure."""

    address: str = ""
    latitude: float | None = None
    longitude: float | None = None
    owner: str = ""
    route_id: str = ""
