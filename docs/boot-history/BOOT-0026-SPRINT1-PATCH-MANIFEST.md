# BOOT-0026 Sprint 1 Patch Manifest

## Package type

Patch package. Merge the enclosed `AnchorOS/` directory into an AnchorOS repository that already contains BOOT-0025 Phase 1.

## Prerequisites

The target repository must contain:

- `core/infrastructure_registry/models.py`
- `core/infrastructure_registry/repository.py`
- `core/infrastructure_registry/database.py`
- BOOT-0025 Phase 1 schema and repository implementation

## Added files

- `core/infrastructure_registry/exceptions.py`
- `core/infrastructure_registry/lifecycle.py`
- `core/infrastructure_registry/validators.py`
- `core/infrastructure_registry/services/__init__.py`
- `core/infrastructure_registry/services/organization_service.py`
- `tests/infrastructure_registry/test_organization_service.py`
- `scripts/verify_boot_0026_sprint1.py`
- `docs/boot-history/BOOT-0026-S1.md`

## Modified files

- `core/infrastructure_registry/__init__.py`

## Verification

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/verify_boot_0026_sprint1.py
python app.py
```
