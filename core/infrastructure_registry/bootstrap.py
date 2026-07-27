"""Bootstrap lifecycle for the AOS-140 Infrastructure Registry."""

from __future__ import annotations

from dataclasses import dataclass

from core.infrastructure_registry.config import RegistryConfig
from core.infrastructure_registry.database import RegistryDatabase
from core.infrastructure_registry.repository import InfrastructureRegistryRepository


@dataclass(slots=True)
class RegistryBootstrapResult:
    database_connected: bool
    schema_verified: bool
    repository_initialized: bool
    status: str


class InfrastructureRegistryBootstrap:
    """Initializes and verifies the registry foundation."""

    def __init__(self, config: RegistryConfig | None = None) -> None:
        self.config = config or RegistryConfig.from_environment()
        self.database = RegistryDatabase(
            self.config.database_path,
            self.config.schema_version,
        )
        self.repository: InfrastructureRegistryRepository | None = None
        self.status = "OFFLINE"

    def start(self) -> RegistryBootstrapResult:
        self.database.initialize_schema()
        schema_verified = self.database.verify_schema()
        if not schema_verified:
            self.status = "FAILED"
            raise RuntimeError("Infrastructure Registry schema verification failed.")
        self.repository = InfrastructureRegistryRepository(self.database)
        self.status = "ONLINE"
        return RegistryBootstrapResult(True, True, True, self.status)

    def stop(self) -> None:
        self.repository = None
        self.status = "OFFLINE"
