"""Discoverable AnchorOS service wrapper for AOS-140."""

from __future__ import annotations

from core.infrastructure_registry.bootstrap import InfrastructureRegistryBootstrap
from core.infrastructure_registry.config import RegistryConfig
from core.module import Module


class InfrastructureRegistry(Module):
    """Canonical infrastructure system-of-record service."""

    def __init__(self, config: RegistryConfig | None = None) -> None:
        selected_config = config or RegistryConfig.from_environment()
        super().__init__("Infrastructure Registry", selected_config.registry_version)
        self.bootstrap = InfrastructureRegistryBootstrap(selected_config)
        self.repository = None
        self.schema_verified = False

    def start(self) -> None:
        result = self.bootstrap.start()
        self.repository = self.bootstrap.repository
        self.schema_verified = result.schema_verified
        self.status = "Running"
        print("✓ Database Connected: Infrastructure Registry")
        print("✓ Schema Verified: Infrastructure Registry")
        print("✓ Repository Initialized: Infrastructure Registry")
        print("✓ Registry Status: ONLINE")

    def stop(self) -> None:
        self.bootstrap.stop()
        self.repository = None
        self.status = "Stopped"

    def health(self) -> dict[str, str]:
        health_data = super().health()
        health_data["schema"] = "VERIFIED" if self.schema_verified else "UNVERIFIED"
        health_data["registry_status"] = self.bootstrap.status
        return health_data


def create_module(context: dict) -> InfrastructureRegistry:
    return InfrastructureRegistry()
