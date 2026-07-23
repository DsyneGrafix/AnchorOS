# AnchorIntel Sprint 2 Change Summary

Sprint 2 adds the first managed Evidence Service while preserving Sprint 1.

## Added

- Opportunity-scoped evidence create, list, retrieve, patch, archive, and file routes.
- Metadata-only and optional multipart file evidence.
- Sequential `EV-000001` public IDs and internal SQLite IDs.
- Controlled evidence type, status, confidence, and ISO date validation.
- External file storage with generated names, 10 MiB limit, path controls, and SHA-256.
- Evidence list, Add, Detail, Edit, and Archive user interfaces.
- Active/file-backed/metadata-only/archived visual distinctions.
- Additive Sprint 1 evidence-schema migration.
- Audit events for evidence creation, file upload, metadata update, and archive.
- Persisted `Attach Evidence` workflow derivation.
- Idempotent EV-000001 reference seed with an explicit non-FPL disclaimer.
- OpenAPI documentation, migration instructions, rollback instructions, and verification checklist.

## Preserved

- Opportunity list, detail, edit, archive, revision, SQLite, and audit behavior.
- Existing `/v1` opportunity, legacy evidence classification, assessment, reporting, lifecycle, revalidation, and administration routes.
- Existing AnchorIntel visual design and AnchorOS adapter boundary.

## Deliberately deferred

- Knowledge Module Review implementation.
- New S.P.A.T.I.A.L. assessment work.
- Executive Opportunity Dossier.
- File replacement, evidence restoration, authentication, authorization, tenant isolation, and tamper-evident storage.

