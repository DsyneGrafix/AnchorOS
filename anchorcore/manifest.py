from core.module import Module
from version import (
    BOOT,
    BUILD,
    CODENAME,
    PRODUCT,
    STAGE,
    VERSION,
)


class PlatformManifest(Module):
    """Authoritative description of the running AnchorOS platform."""

    def __init__(self) -> None:
        super().__init__("Platform Manifest", "1.0.0")

        self.product = PRODUCT
        self.version = VERSION
        self.codename = CODENAME
        self.stage = STAGE
        self.boot = BOOT
        self.build = BUILD

        self.kernel: list[str] = [
            "Module Manager",
            "Service Registry",
        ]

        self.services: list[str] = []
        self.frameworks: list[str] = []
        self.applications: list[str] = []

    def register_service(self, name: str) -> None:
        if name not in self.services:
            self.services.append(name)

    def register_framework(self, name: str) -> None:
        if name not in self.frameworks:
            self.frameworks.append(name)

    def register_application(self, name: str) -> None:
        if name not in self.applications:
            self.applications.append(name)

    def describe(self) -> dict[str, object]:
        return {
            "product": self.product,
            "version": self.version,
            "codename": self.codename,
            "stage": self.stage,
            "boot": self.boot,
            "build": self.build,
            "kernel": self.kernel.copy(),
            "services": sorted(self.services),
            "frameworks": sorted(self.frameworks),
            "applications": sorted(self.applications),
        }


def create_module(context: object = None) -> PlatformManifest:
    """Create the AnchorOS Platform Manifest."""

    return PlatformManifest()
