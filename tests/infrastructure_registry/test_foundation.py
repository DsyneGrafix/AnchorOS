from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.infrastructure_registry.bootstrap import InfrastructureRegistryBootstrap
from core.infrastructure_registry.config import RegistryConfig
from core.infrastructure_registry.database import RegistryDatabase
from core.infrastructure_registry.models import Asset, AssetType, Facility, Organization, Relationship
from core.infrastructure_registry.repository import InfrastructureRegistryRepository
from services.infrastructure_registry import InfrastructureRegistry


class InfrastructureRegistryFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "registry.db"
        self.config = RegistryConfig(database_path=self.database_path)
        self.database = RegistryDatabase(self.database_path, "1")
        self.database.initialize_schema()
        self.repository = InfrastructureRegistryRepository(self.database)

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_schema_creation_and_verification(self) -> None:
        self.assertTrue(self.database.verify_schema())

    def test_model_defaults(self) -> None:
        organization = Organization(name="Sirius Logic Systems")
        self.assertTrue(organization.id)
        self.assertEqual(organization.status, "ACTIVE")
        self.assertEqual(organization.version, 1)

    def test_repository_crud(self) -> None:
        organization = self.repository.create(Organization(name="SLS"))
        self.assertEqual(self.repository.require(Organization, organization.id).name, "SLS")
        organization.name = "Sirius Logic Systems"
        updated = self.repository.update(organization)
        self.assertEqual(updated.version, 2)
        self.assertEqual(self.repository.count(Organization), 1)
        self.repository.delete(Organization, organization.id)
        self.assertIsNone(self.repository.get(Organization, organization.id))

    def test_foreign_key_integrity(self) -> None:
        facility = Facility(name="Unbound Facility", organization_id="missing")
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create(facility)

    def test_canonical_entity_persistence(self) -> None:
        organization = self.repository.create(Organization(name="SLS"))
        facility = self.repository.create(Facility(name="Tampa Site", organization_id=organization.id))
        asset_type = self.repository.create(AssetType(name="Fiber Cabinet"))
        asset = self.repository.create(Asset(name="CAB-001", asset_type_id=asset_type.id, facility_id=facility.id))
        relationship = self.repository.create(Relationship(name="Cabinet location", source_id=asset.id, target_id=facility.id, relationship_type="LOCATED_IN"))
        self.assertEqual(self.repository.count(Facility), 1)
        self.assertEqual(self.repository.count(AssetType), 1)
        self.assertEqual(self.repository.count(Asset), 1)
        self.assertEqual(self.repository.count(Relationship), 1)
        self.assertEqual(self.repository.require(Asset, asset.id).metadata, {})

    def test_bootstrap_success(self) -> None:
        bootstrap = InfrastructureRegistryBootstrap(self.config)
        result = bootstrap.start()
        self.assertTrue(result.schema_verified)
        self.assertEqual(result.status, "ONLINE")
        self.assertIsNotNone(bootstrap.repository)
        bootstrap.stop()
        self.assertEqual(bootstrap.status, "OFFLINE")

    def test_discoverable_service_lifecycle(self) -> None:
        service = InfrastructureRegistry(self.config)
        service.start()
        health = service.health()
        self.assertEqual(health["status"], "Running")
        self.assertEqual(health["schema"], "VERIFIED")
        self.assertEqual(health["registry_status"], "ONLINE")
        service.stop()
        self.assertEqual(service.status, "Stopped")


if __name__ == "__main__":
    unittest.main()
