"""Managed Facility operations for AOS-140."""

from __future__ import annotations

from typing import Any

from core.infrastructure_registry.exceptions import (
    DuplicateEntityError,
    RegistryValidationError,
)
from core.infrastructure_registry.lifecycle import (
    ACTIVE,
    ARCHIVED,
    INACTIVE,
    PLANNED,
    RETIRED,
    normalize_state,
    validate_transition,
)
from core.infrastructure_registry.models import Facility, Organization
from core.infrastructure_registry.repository import InfrastructureRegistryRepository
from core.infrastructure_registry.validators import (
    normalize_optional_identifier,
    require_text,
)


_PARENT_ALLOWED_STATES = {PLANNED, ACTIVE, INACTIVE}


class FacilityService:
    """Owns Facility hierarchy, uniqueness, and lifecycle rules."""

    def __init__(self, repository: InfrastructureRegistryRepository) -> None:
        self.repository = repository

    def create(
        self,
        organization_id: str,
        name: str,
        *,
        external_id: str | None = None,
        location: str | None = None,
        status: str = PLANNED,
        metadata: dict[str, Any] | None = None,
    ) -> Facility:
        organization = self._require_valid_parent(organization_id)
        normalized_name = require_text(name, "Facility name")
        normalized_external_id = normalize_optional_identifier(external_id)
        normalized_location = self._normalize_optional_text(location, "Facility location")
        self._ensure_unique(
            organization.id,
            normalized_name,
            normalized_external_id,
        )
        facility = Facility(
            name=normalized_name,
            organization_id=organization.id,
            external_id=normalized_external_id,
            location=normalized_location,
            status=normalize_state(status),
            metadata=dict(metadata or {}),
        )
        return self.repository.create(facility)

    def get(self, facility_id: str) -> Facility:
        return self.repository.require(Facility, facility_id)

    def list(self) -> list[Facility]:
        return self.repository.list(Facility)

    def list_by_organization(self, organization_id: str) -> list[Facility]:
        self.repository.require(Organization, organization_id)
        return self.repository.list_facilities_by_organization(organization_id)

    def rename(self, facility_id: str, new_name: str) -> Facility:
        facility = self.get(facility_id)
        normalized_name = require_text(new_name, "Facility name")
        self._ensure_unique(
            facility.organization_id,
            normalized_name,
            facility.external_id,
            exclude_id=facility.id,
        )
        facility.name = normalized_name
        return self.repository.update(facility)

    def change_external_id(
        self, facility_id: str, external_id: str | None
    ) -> Facility:
        facility = self.get(facility_id)
        normalized_external_id = normalize_optional_identifier(external_id)
        self._ensure_unique(
            facility.organization_id,
            facility.name,
            normalized_external_id,
            exclude_id=facility.id,
        )
        facility.external_id = normalized_external_id
        return self.repository.update(facility)

    def move(self, facility_id: str, organization_id: str) -> Facility:
        facility = self.get(facility_id)
        target = self._require_valid_parent(organization_id)
        if facility.organization_id == target.id:
            return facility
        self._ensure_unique(
            target.id,
            facility.name,
            facility.external_id,
            exclude_id=facility.id,
        )
        facility.organization_id = target.id
        return self.repository.update(facility)

    def transition(self, facility_id: str, target_state: str) -> Facility:
        facility = self.get(facility_id)
        facility.status = validate_transition(facility.status, target_state)
        return self.repository.update(facility)

    def activate(self, facility_id: str) -> Facility:
        facility = self.get(facility_id)
        self._require_valid_parent(facility.organization_id)
        return self.transition(facility_id, ACTIVE)

    def deactivate(self, facility_id: str) -> Facility:
        return self.transition(facility_id, INACTIVE)

    def retire(self, facility_id: str) -> Facility:
        return self.transition(facility_id, RETIRED)

    def archive(self, facility_id: str) -> Facility:
        return self.transition(facility_id, ARCHIVED)

    def _require_valid_parent(self, organization_id: str) -> Organization:
        normalized_id = require_text(organization_id, "Organization identifier")
        organization = self.repository.require(Organization, normalized_id)
        state = normalize_state(organization.status)
        if state not in _PARENT_ALLOWED_STATES:
            raise RegistryValidationError(
                "Facility parent organization is not eligible for service: "
                f"{organization.id} ({state})"
            )
        return organization

    def _ensure_unique(
        self,
        organization_id: str,
        name: str,
        external_id: str | None,
        *,
        exclude_id: str | None = None,
    ) -> None:
        normalized_name = name.strip().casefold()
        normalized_external = external_id.casefold() if external_id else None
        for existing in self.repository.list(Facility):
            if existing.id == exclude_id:
                continue
            if (
                existing.organization_id == organization_id
                and existing.name.strip().casefold() == normalized_name
            ):
                raise DuplicateEntityError(
                    f"Facility name already exists in organization: {name}"
                )
            if (
                normalized_external is not None
                and existing.external_id is not None
                and existing.external_id.strip().casefold() == normalized_external
            ):
                raise DuplicateEntityError(
                    "Facility external identifier already exists: "
                    f"{external_id}"
                )

    @staticmethod
    def _normalize_optional_text(value: str | None, label: str) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise RegistryValidationError(f"{label} must not be blank")
        return normalized
