# AOS-140 Infrastructure Registry

This package is the BOOT-0025 Phase 1 foundation for the canonical AnchorOS Infrastructure Registry.

## Included

- Canonical registry models: Organization, Facility, AssetType, Asset, Relationship
- SQLite schema creation and verification
- Persistence-only CRUD repository
- Centralized environment-driven configuration
- Bootstrap lifecycle and health state

## Deferred

REST APIs, authorization, advanced validation, event publication, graph traversal, GIS, and full-text search are intentionally outside Phase 1.

## Configuration

- `ANCHOROS_REGISTRY_DB`: SQLite database path
- `ANCHOROS_REGISTRY_SCHEMA_VERSION`: expected schema version
- `ANCHOROS_REGISTRY_VERSION`: service version
- `ANCHOROS_REGISTRY_LOG_LEVEL`: logging level
