#!/usr/bin/env python3
"""Operational verification for BOOT-0026 Sprint 2 Facility Service."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.infrastructure_registry.database import RegistryDatabase
from core.infrastructure_registry.exceptions import (
    DuplicateEntityError,
    InvalidLifecycleTransitionError,
)
from core.infrastructure_registry.lifecycle import ACTIVE, ARCHIVED
from core.infrastructure_registry.models import Facility
from core.infrastructure_registry.repository import InfrastructureRegistryRepository
from core.infrastructure_registry.services import FacilityService, OrganizationService


def passed(label: str) -> None:
    print(f"PASS: {label}")


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        database = RegistryDatabase(Path(temp_dir) / "registry.db", "1")
        database.initialize_schema()
        repository = InfrastructureRegistryRepository(database)
        organizations = OrganizationService(repository)
        facilities = FacilityService(repository)

        source = organizations.create("Sirius Logic Systems", external_id="SLS")
        target = organizations.create("Anchor Operations", external_id="AOPS")

        facility = facilities.create(
            source.id,
            "Tampa Operations Center",
            external_id="FAC-TAMPA",
            location="Tampa, Florida",
        )
        assert facility.organization_id == source.id
        passed("Facility creation")

        assert facilities.get(facility.id).id == facility.id
        passed("Facility retrieval")

        assert facilities.list() == [facility]
        assert facilities.list_by_organization(source.id) == [facility]
        passed("Facility listing")

        try:
            facilities.create("missing-organization", "Orphan Facility")
        except LookupError:
            passed("Organization validation")
        else:
            raise AssertionError("Missing parent organization was accepted")

        try:
            facilities.create(source.id, "tampa operations center")
        except DuplicateEntityError:
            passed("Duplicate prevention")
        else:
            raise AssertionError("Duplicate facility name was accepted")

        moved = facilities.move(facility.id, target.id)
        assert moved.organization_id == target.id
        assert facilities.list_by_organization(source.id) == []
        assert facilities.list_by_organization(target.id) == [moved]
        passed("Facility relocation")

        moved = facilities.activate(moved.id)
        assert moved.status == ACTIVE
        moved = facilities.retire(moved.id)
        moved = facilities.archive(moved.id)
        assert moved.status == ARCHIVED
        try:
            facilities.activate(moved.id)
        except InvalidLifecycleTransitionError:
            passed("Lifecycle enforcement")
        else:
            raise AssertionError("Archived facility returned to service")

        persisted = repository.require(Facility, moved.id)
        assert persisted.id == moved.id
        assert persisted.organization_id == target.id
        assert persisted.version == moved.version
        passed("Repository persistence")

    print("Facility Service Status: OPERATIONAL")
    print("BOOT-0026 Sprint 2 Verification: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
