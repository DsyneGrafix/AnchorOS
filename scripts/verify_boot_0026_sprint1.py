"""Independent BOOT-0026 Sprint 1 verification."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.infrastructure_registry.database import RegistryDatabase
from core.infrastructure_registry.exceptions import DuplicateEntityError, InvalidLifecycleTransitionError
from core.infrastructure_registry.lifecycle import ACTIVE, ARCHIVED, RETIRED
from core.infrastructure_registry.repository import InfrastructureRegistryRepository
from core.infrastructure_registry.services import OrganizationService


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"PASS: {label}")


def main() -> None:
    print("=" * 58)
    print("AnchorOS BOOT-0026")
    print("Infrastructure Registry — Sprint 1 Organization Service")
    print("=" * 58)
    with tempfile.TemporaryDirectory() as temp_dir:
        database = RegistryDatabase(Path(temp_dir) / "registry.db", "1")
        database.initialize_schema()
        repository = InfrastructureRegistryRepository(database)
        service = OrganizationService(repository)

        organization = service.create("Sirius Logic Systems", external_id="SLS")
        check("Organization creation", service.get(organization.id).id == organization.id)
        check("Organization retrieval", len(service.list()) == 1)

        renamed = service.rename(organization.id, "Sirius Logic Systems LLC")
        check("Organization rename", renamed.name == "Sirius Logic Systems LLC")

        try:
            service.create("Sirius Logic Systems LLC")
        except DuplicateEntityError:
            duplicate_rejected = True
        else:
            duplicate_rejected = False
        check("Duplicate prevention", duplicate_rejected)

        active = service.activate(organization.id)
        check("Organization activation", active.status == ACTIVE)
        retired = service.retire(organization.id)
        check("Organization retirement", retired.status == RETIRED)
        archived = service.archive(organization.id)
        check("Organization archival", archived.status == ARCHIVED)

        try:
            service.activate(organization.id)
        except InvalidLifecycleTransitionError:
            invalid_transition_rejected = True
        else:
            invalid_transition_rejected = False
        check("Lifecycle enforcement", invalid_transition_rejected)

    print("-" * 58)
    print("Organization Service Status: OPERATIONAL")
    print("BOOT-0026 Sprint 1 Verification: PASS")


if __name__ == "__main__":
    main()
