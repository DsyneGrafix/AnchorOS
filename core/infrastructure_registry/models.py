"""Canonical domain models for the AOS-140 Infrastructure Registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid4())


@dataclass(slots=True)
class RegistryEntity:
    """Fields shared by every canonical registry entity."""

    name: str
    id: str = field(default_factory=new_id)
    status: str = "ACTIVE"
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Organization(RegistryEntity):
    external_id: str | None = None


@dataclass(slots=True)
class Facility(RegistryEntity):
    organization_id: str = ""
    location: str | None = None
    external_id: str | None = None


@dataclass(slots=True)
class AssetType(RegistryEntity):
    description: str | None = None


@dataclass(slots=True)
class Asset(RegistryEntity):
    asset_type_id: str = ""
    facility_id: str | None = None
    external_id: str | None = None


@dataclass(slots=True)
class Relationship(RegistryEntity):
    source_id: str = ""
    target_id: str = ""
    relationship_type: str = "RELATED_TO"
