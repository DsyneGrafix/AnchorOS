"""Managed Organization operations for AOS-140."""

from __future__ import annotations

from typing import Any

from core.infrastructure_registry.exceptions import DuplicateEntityError
from core.infrastructure_registry.lifecycle import (
    ACTIVE,
    ARCHIVED,
    INACTIVE,
    PLANNED,
    RETIRED,
    normalize_state,
    validate_transition,
)
from core.infrastructure_registry.models import Organization
from core.infrastructure_registry.repository import InfrastructureRegistryRepository
from core.infrastructure_registry.validators import (
    normalize_optional_identifier,
    require_text,
)


class OrganizationService:
    """Owns Organization business rules and lifecycle behavior."""

    def __init__(self, repository: InfrastructureRegistryRepository) -> None:
        self.repository = repository

    def create(
        self,
        name: str,
        *,
        external_id: str | None = None,
        status: str = PLANNED,
        metadata: dict[str, Any] | None = None,
    ) -> Organization:
        normalized_name = require_text(name, "Organization name")
        normalized_external_id = normalize_optional_identifier(external_id)
        self._ensure_unique(normalized_name, normalized_external_id)
        organization = Organization(
            name=normalized_name,
            external_id=normalized_external_id,
            status=normalize_state(status),
            metadata=dict(metadata or {}),
        )
        return self.repository.create(organization)

    def get(self, organization_id: str) -> Organization:
        return self.repository.require(Organization, organization_id)

    def list(self) -> list[Organization]:
        return self.repository.list(Organization)

    def rename(self, organization_id: str, new_name: str) -> Organization:
        organization = self.get(organization_id)
        normalized_name = require_text(new_name, "Organization name")
        self._ensure_unique(
            normalized_name,
            organization.external_id,
            exclude_id=organization.id,
        )
        organization.name = normalized_name
        return self.repository.update(organization)

    def change_external_id(
        self, organization_id: str, external_id: str | None
    ) -> Organization:
        organization = self.get(organization_id)
        normalized_external_id = normalize_optional_identifier(external_id)
        self._ensure_unique(
            organization.name,
            normalized_external_id,
            exclude_id=organization.id,
        )
        organization.external_id = normalized_external_id
        return self.repository.update(organization)

    def transition(self, organization_id: str, target_state: str) -> Organization:
        organization = self.get(organization_id)
        organization.status = validate_transition(organization.status, target_state)
        return self.repository.update(organization)

    def activate(self, organization_id: str) -> Organization:
        return self.transition(organization_id, ACTIVE)

    def deactivate(self, organization_id: str) -> Organization:
        return self.transition(organization_id, INACTIVE)

    def retire(self, organization_id: str) -> Organization:
        return self.transition(organization_id, RETIRED)

    def archive(self, organization_id: str) -> Organization:
        return self.transition(organization_id, ARCHIVED)

    def _ensure_unique(
        self,
        name: str,
        external_id: str | None,
        *,
        exclude_id: str | None = None,
    ) -> None:
        normalized_name = name.casefold()
        normalized_external = external_id.casefold() if external_id else None
        for existing in self.repository.list(Organization):
            if existing.id == exclude_id:
                continue
            if existing.name.strip().casefold() == normalized_name:
                raise DuplicateEntityError(
                    f"Organization name already exists: {name}"
                )
            if (
                normalized_external is not None
                and existing.external_id is not None
                and existing.external_id.strip().casefold() == normalized_external
            ):
                raise DuplicateEntityError(
                    f"Organization external identifier already exists: {external_id}"
                )
