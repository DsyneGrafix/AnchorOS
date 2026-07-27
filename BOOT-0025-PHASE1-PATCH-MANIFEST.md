# BOOT-0025 Phase 1 Patch Manifest

## Package Type

Patch package. Merge the included paths into the root of the existing AnchorOS repository.

## Baseline Prerequisites

The target repository must already contain:

- `core/module.py`
- `core/module_manager.py`
- `core/service_registry.py`
- `services/` as a discoverable Python package
- `startup.py`
- `app.py`
- Python 3.11 or newer

No third-party dependency is added by this patch.

## Added or Replaced Files

- `core/infrastructure_registry/__init__.py`
- `core/infrastructure_registry/config.py`
- `core/infrastructure_registry/models.py`
- `core/infrastructure_registry/database.py`
- `core/infrastructure_registry/repository.py`
- `core/infrastructure_registry/bootstrap.py`
- `core/infrastructure_registry/README.md`
- `services/infrastructure_registry.py`
- `tests/infrastructure_registry/__init__.py`
- `tests/infrastructure_registry/test_foundation.py`
- `scripts/verify_boot_0025_phase1.py`
- `docs/boot-history/BOOT-0025.md`
- `evidence/BOOT-0025/MANIFEST.md`
- `evidence/BOOT-0025/test-output.txt`
- `evidence/BOOT-0025/verification-output.txt`
- `evidence/BOOT-0025/platform-boot-output.txt`

## Verification

From the AnchorOS repository root:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/verify_boot_0025_phase1.py
python app.py
```

Expected results:

- 7 tests pass
- Independent verification reports PASS
- Infrastructure Registry appears under Registered Services, Health Report, Platform Services, and Lifecycle Report
- Platform status remains HEALTHY
