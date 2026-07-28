# BOOT-0026 Sprint 2 — Facility Service Patch Manifest

## Scope

This patch implements the AOS-140 Facility Service only.

## Changed Files

- `core/infrastructure_registry/repository.py`
- `core/infrastructure_registry/services/__init__.py`
- `core/infrastructure_registry/services/facility_service.py`
- `tests/infrastructure_registry/test_facility_service.py`
- `scripts/verify_boot_0026_sprint2.py`
- `docs/boot-history/BOOT-0026-S2.md`

## Prerequisites

The target AnchorOS repository must already contain:

- BOOT-0025 Infrastructure Registry foundation
- BOOT-0026 Sprint 1 Organization Service
- `core/infrastructure_registry/database.py`
- `core/infrastructure_registry/models.py`
- `core/infrastructure_registry/exceptions.py`
- `core/infrastructure_registry/lifecycle.py`
- `core/infrastructure_registry/validators.py`
- `core/infrastructure_registry/services/organization_service.py`

## Integrity Rules Implemented

- Every Facility has exactly one parent Organization.
- Missing, retired, or archived parents are rejected.
- Facility identity remains immutable.
- Facility names are unique within a parent Organization, case-insensitively.
- Facility external identifiers are globally unique, case-insensitively.
- Facility relocation preserves identity and rejects target collisions.
- Lifecycle transitions use the shared registry lifecycle policy.
