from dataclasses import dataclass

from anchorfiber.assets.asset import Asset


@dataclass
class Splice(Asset):
    """Represents a fiber splice or splice enclosure."""

    location_asset_id: str = ""
    splice_type: str = ""
    fiber_count: int = 0
    route_id: str = ""
