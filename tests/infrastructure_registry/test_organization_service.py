"""BOOT-0026 Sprint 1 tests for OrganizationService."""

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
from core.infrastructure_registry.repository import InfrastructureRegistryRepository
from core.infrastructure_registry.services import OrganizationService


class OrganizationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database = RegistryDatabase(Path(self.temp_dir.name) / "registry.db", "1")
        database.initialize_schema()
        self.repository = InfrastructureRegistryRepository(database)
        self.service = OrganizationService(self.repository)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_get_and_list(self) -> None:
        created = self.service.create("Sirius Logic Systems", external_id="SLS")
        self.assertEqual(PLANNED, created.status)
        self.assertEqual(created, self.service.get(created.id))
        self.assertEqual([created], self.service.list())

    def test_rejects_blank_name(self) -> None:
        with self.assertRaises(RegistryValidationError):
            self.service.create("   ")

    def test_rejects_duplicate_name_case_insensitively(self) -> None:
        self.service.create("Sirius Logic Systems")
        with self.assertRaises(DuplicateEntityError):
            self.service.create("  sirius logic systems  ")

    def test_rejects_duplicate_external_identifier_case_insensitively(self) -> None:
        self.service.create("Sirius Logic Systems", external_id="SLS")
        with self.assertRaises(DuplicateEntityError):
            self.service.create("Another Company", external_id="sls")

    def test_rename_updates_version_and_preserves_identity(self) -> None:
        created = self.service.create("Sirius Logic")
        renamed = self.service.rename(created.id, "Sirius Logic Systems")
        self.assertEqual(created.id, renamed.id)
        self.assertEqual("Sirius Logic Systems", renamed.name)
        self.assertEqual(2, renamed.version)

    def test_valid_lifecycle_transitions(self) -> None:
        organization = self.service.create("Lifecycle Test")
        organization = self.service.activate(organization.id)
        self.assertEqual(ACTIVE, organization.status)
        organization = self.service.deactivate(organization.id)
        self.assertEqual(INACTIVE, organization.status)
        organization = self.service.activate(organization.id)
        organization = self.service.retire(organization.id)
        self.assertEqual(RETIRED, organization.status)
        organization = self.service.archive(organization.id)
        self.assertEqual(ARCHIVED, organization.status)

    def test_rejects_invalid_lifecycle_transition(self) -> None:
        organization = self.service.create("Invalid Transition")
        with self.assertRaises(InvalidLifecycleTransitionError):
            self.service.retire(organization.id)

    def test_archived_organization_cannot_return_to_service(self) -> None:
        organization = self.service.create("Archive Test")
        organization = self.service.archive(organization.id)
        with self.assertRaises(InvalidLifecycleTransitionError):
            self.service.activate(organization.id)


if __name__ == "__main__":
    unittest.main()
