from dataclasses import dataclass

from anchorfiber.assets.asset import Asset


@dataclass
class Site(Asset):
    """Represents a physical location in a fiber network."""

    site_type: str = ""
    address: str = ""
    latitude: float | None = None
    longitude: float | None = None
