from dataclasses import dataclass, field

from anchorfiber.assets.asset import Asset


@dataclass
class Network(Asset):
    """Represents an entire customer fiber network."""

    owner: str = ""
    description: str = ""
    site_ids: list[str] = field(default_factory=list)
    route_ids: list[str] = field(default_factory=list)

    def add_site(self, site_id: str) -> None:
        """Associate a site with this network."""

        if site_id not in self.site_ids:
            self.site_ids.append(site_id)

    def add_route(self, route_id: str) -> None:
        """Associate a route with this network."""

        if route_id not in self.route_ids:
            self.route_ids.append(route_id)
