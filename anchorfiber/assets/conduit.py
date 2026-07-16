from dataclasses import dataclass

from anchorfiber.assets.asset import Asset


@dataclass
class Conduit(Asset):
    """Represents conduit carrying fiber infrastructure."""

    material: str = ""
    diameter_inches: float = 0.0
    occupancy_percent: float = 0.0
    route_id: str = ""

    def update_occupancy(self, occupancy_percent: float) -> None:
        """Update conduit occupancy after validating the percentage."""

        if not 0.0 <= occupancy_percent <= 100.0:
            raise ValueError(
                "Conduit occupancy must be between 0 and 100 percent."
            )

        self.occupancy_percent = occupancy_percent
