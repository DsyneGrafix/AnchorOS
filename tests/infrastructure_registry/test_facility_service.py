"""BOOT-0026 Sprint 2 tests for FacilityService."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.infrastructure_registry.database import RegistryDatabase
from core.infrastructure_registry.exceptions import (
    DuplicateEntityError,
    InvalidLifecycleTransitionError,
    RegistryValidationError,
)
from core.infrastructure_registry.lifecycle import ACTIVE, ARCHIVED, INACTIVE, PLANNED, RETIRED
from core.infrastructure_registry.models import Facility
from core.infrastructure_registry.repository import (
    EntityNotFoundError,
    InfrastructureRegistryRepository,
)
from core.infrastructure_registry.services import FacilityService, OrganizationService


class FacilityServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database = RegistryDatabase(Path(self.temp_dir.name) / "registry.db", "1")
        database.initialize_schema()
        self.repository = InfrastructureRegistryRepository(database)
        self.organizations = OrganizationService(self.repository)
        self.facilities = FacilityService(self.repository)
        self.organization = self.organizations.create("Sirius Logic Systems")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_get_list_and_persist(self) -> None:
        created = self.facilities.create(
            self.organization.id,
            "Tampa Operations Center",
            external_id="FAC-TAMPA",
            location="Tampa, Florida",
        )
        self.assertEqual(PLANNED, created.status)
        self.assertEqual(self.organization.id, created.organization_id)
        self.assertEqual(created, self.facilities.get(created.id))
        self.assertEqual([created], self.facilities.list())
        self.assertEqual(
            created,
            self.repository.require(Facility, created.id),
        )

    def test_missing_organization_is_rejected_without_persistence(self) -> None:
        with self.assertRaises(EntityNotFoundError):
            self.facilities.create("missing", "Orphan Facility")
        self.assertEqual(0, self.repository.count(Facility))

    def test_retired_parent_is_rejected_without_persistence(self) -> None:
        self.organizations.activate(self.organization.id)
        self.organizations.retire(self.organization.id)
        with self.assertRaises(RegistryValidationError):
            self.facilities.create(self.organization.id, "Invalid Facility")
        self.assertEqual(0, self.repository.count(Facility))

    def test_duplicate_name_is_rejected_within_same_organization(self) -> None:
        self.facilities.create(self.organization.id, "Main Campus")
        with self.assertRaises(DuplicateEntityError):
            self.facilities.create(self.organization.id, "  main campus  ")
        self.assertEqual(1, self.repository.count(Facility))

    def test_same_name_is_allowed_in_different_organizations(self) -> None:
        other = self.organizations.create("Second Organization")
        first = self.facilities.create(self.organization.id, "Main Campus")
        second = self.facilities.create(other.id, "Main Campus")
        self.assertNotEqual(first.id, second.id)

    def test_duplicate_external_identifier_is_rejected_globally(self) -> None:
        other = self.organizations.create("Second Organization")
        self.facilities.create(self.organization.id, "First", external_id="FAC-001")
        with self.assertRaises(DuplicateEntityError):
            self.facilities.create(other.id, "Second", external_id="fac-001")

    def test_rename_preserves_identity_and_parent(self) -> None:
        created = self.facilities.create(self.organization.id, "Old Name")
        renamed = self.facilities.rename(created.id, "New Name")
        self.assertEqual(created.id, renamed.id)
        self.assertEqual(self.organization.id, renamed.organization_id)
        self.assertEqual("New Name", renamed.name)
        self.assertEqual(2, renamed.version)

    def test_move_between_organizations(self) -> None:
        target = self.organizations.create("Target Organization")
        created = self.facilities.create(self.organization.id, "Mobile Facility")
        moved = self.facilities.move(created.id, target.id)
        self.assertEqual(created.id, moved.id)
        self.assertEqual(target.id, moved.organization_id)
        self.assertEqual([], self.facilities.list_by_organization(self.organization.id))
        self.assertEqual([moved], self.facilities.list_by_organization(target.id))

    def test_move_rejects_duplicate_name_at_target_and_preserves_parent(self) -> None:
        target = self.organizations.create("Target Organization")
        original = self.facilities.create(self.organization.id, "Shared Name")
        self.facilities.create(target.id, "Shared Name")
        with self.assertRaises(DuplicateEntityError):
            self.facilities.move(original.id, target.id)
        persisted = self.facilities.get(original.id)
        self.assertEqual(self.organization.id, persisted.organization_id)

    def test_valid_lifecycle_transitions(self) -> None:
        facility = self.facilities.create(self.organization.id, "Lifecycle Facility")
        facility = self.facilities.activate(facility.id)
        self.assertEqual(ACTIVE, facility.status)
        facility = self.facilities.deactivate(facility.id)
        self.assertEqual(INACTIVE, facility.status)
        facility = self.facilities.activate(facility.id)
        facility = self.facilities.retire(facility.id)
        self.assertEqual(RETIRED, facility.status)
        facility = self.facilities.archive(facility.id)
        self.assertEqual(ARCHIVED, facility.status)

    def test_invalid_lifecycle_transition_preserves_state(self) -> None:
        facility = self.facilities.create(self.organization.id, "Invalid Transition")
        with self.assertRaises(InvalidLifecycleTransitionError):
            self.facilities.retire(facility.id)
        self.assertEqual(PLANNED, self.facilities.get(facility.id).status)

    def test_archived_facility_cannot_return_to_service(self) -> None:
        facility = self.facilities.create(self.organization.id, "Archive Facility")
        facility = self.facilities.archive(facility.id)
        with self.assertRaises(InvalidLifecycleTransitionError):
            self.facilities.activate(facility.id)


if __name__ == "__main__":
    unittest.main()
