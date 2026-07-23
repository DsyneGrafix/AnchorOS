from core.module import Module


class ServiceRegistry:
    """
    AnchorOS Service Registry

    Owns platform service discovery and lookup.
    """

    def __init__(self):
        self._services: dict[str, Module] = {}

    def register(self, service: Module):
        """Register a platform service."""

        self._services[service.name] = service

    def get(self, name: str):
        """Return a service or None."""

        return self._services.get(name)

    def require(self, name: str):
        """Return a required service."""

        service = self.get(name)

        if service is None:
            raise RuntimeError(
                f"Required service not found: {name}"
            )

        return service

    def contains(self, name: str):
        return name in self._services

    def list_services(self):
        return sorted(self._services.keys())
