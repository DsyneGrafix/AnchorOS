"""Independent BOOT-0025 Phase 1 verification routine."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.infrastructure_registry.bootstrap import InfrastructureRegistryBootstrap
from core.infrastructure_registry.config import RegistryConfig
from core.infrastructure_registry.models import Asset, AssetType, Facility, Organization, Relationship


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        config = RegistryConfig(database_path=Path(directory) / "verification.db")
        bootstrap = InfrastructureRegistryBootstrap(config)

        print("=" * 58)
        print("AnchorOS BOOT-0025")
        print("Infrastructure Registry — Phase 1 Foundation")
        print("=" * 58)
        print("Initializing registry...")
        result = bootstrap.start()
        repository = bootstrap.repository
        assert repository is not None

        organization = repository.create(Organization(name="Sirius Logic Systems"))
        facility = repository.create(Facility(name="Verification Facility", organization_id=organization.id))
        asset_type = repository.create(AssetType(name="Verification Asset Type"))
        asset = repository.create(Asset(name="Verification Asset", asset_type_id=asset_type.id, facility_id=facility.id))
        repository.create(Relationship(name="Verification relationship", source_id=asset.id, target_id=facility.id, relationship_type="LOCATED_IN"))

        checks = {
            "Database connection": result.database_connected,
            "Schema verification": result.schema_verified,
            "Repository initialization": result.repository_initialized,
            "Organization CRUD": repository.count(Organization) == 1,
            "Facility CRUD": repository.count(Facility) == 1,
            "Asset Type CRUD": repository.count(AssetType) == 1,
            "Asset CRUD": repository.count(Asset) == 1,
            "Relationship CRUD": repository.count(Relationship) == 1,
            "Registry online": result.status == "ONLINE",
        }

        for name, passed in checks.items():
            print(f"{'PASS' if passed else 'FAIL'}: {name}")

        verified = all(checks.values())
        print("-" * 58)
        print(f"Registry Status: {result.status}")
        print(f"BOOT-0025 Phase 1 Verification: {'PASS' if verified else 'FAIL'}")
        bootstrap.stop()
        return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
