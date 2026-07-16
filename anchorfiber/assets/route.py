from dataclasses import dataclass, field

from anchorfiber.assets.asset import Asset


@dataclass
class Route(Asset):
    """Represents a logical path through a fiber network."""

    origin_site_id: str = ""
    destination_site_id: str = ""
    length_km: float = 0.0
    conduit_ids: list[str] = field(default_factory=list)
    fiber_cable_ids: list[str] = field(default_factory=list)
    splice_ids: list[str] = field(default_factory=list)
    handhole_ids: list[str] = field(default_factory=list)

    def add_conduit(self, conduit_id: str) -> None:
        if conduit_id not in self.conduit_ids:
            self.conduit_ids.append(conduit_id)

    def add_fiber_cable(self, cable_id: str) -> None:
        if cable_id not in self.fiber_cable_ids:
            self.fiber_cable_ids.append(cable_id)

    def add_splice(self, splice_id: str) -> None:
        if splice_id not in self.splice_ids:
            self.splice_ids.append(splice_id)

    def add_handhole(self, handhole_id: str) -> None:
        if handhole_id not in self.handhole_ids:
            self.handhole_ids.append(handhole_id)
