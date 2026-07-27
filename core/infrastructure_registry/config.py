"""Configuration for the AOS-140 Infrastructure Registry."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RegistryConfig:
    """Centralized runtime configuration for the registry."""

    database_path: Path
    schema_version: str = "1"
    registry_version: str = "0.1.0"
    logging_level: str = "INFO"

    @classmethod
    def from_environment(cls) -> "RegistryConfig":
        project_root = Path(__file__).resolve().parents[2]
        default_database = project_root / "data" / "infrastructure_registry.db"
        configured_path = os.getenv("ANCHOROS_REGISTRY_DB")

        return cls(
            database_path=Path(configured_path).expanduser().resolve()
            if configured_path
            else default_database,
            schema_version=os.getenv("ANCHOROS_REGISTRY_SCHEMA_VERSION", "1"),
            registry_version=os.getenv("ANCHOROS_REGISTRY_VERSION", "0.1.0"),
            logging_level=os.getenv("ANCHOROS_REGISTRY_LOG_LEVEL", "INFO"),
        )
