# AnchorIntel Sprint 3 Change Summary

## Outcome

Sprint 3 adds the first bounded Knowledge Service to the installed AnchorIntel
application. `OI-000001` retains `EV-000001`, applies
`AKM-GEO-FL-001`, and generates `KR-000001` from persisted records through the
same service used for future opportunities.

## Added

- version-controlled, integrity-checked Knowledge Module JSON registry;
- deterministic local executor for Florida infrastructure geographic context;
- additive `knowledge_reviews` SQLite table and sequential `KR-######` IDs;
- persisted findings, assumptions, unknowns, risks, missing evidence, confidence,
  input/output hashes, module trace, evidence trace, revisions, and supersession;
- module list/detail, review run/detail, complete, supersede, and list APIs;
- browser module library, run form, review output, evidence trace, and rerun UI;
- dynamic staleness after opportunity/evidence/module changes;
- lifecycle eligibility derived from current persisted conditions;
- audit events for load, start, complete, fail, supersede, rerun, and staleness;
- reference `KR-000001` generation and explicit `EV-000001` limitations;
- Sprint 3 format, module, verification, installation, rollback, and BOOT-0020
  documentation.

## Preserved

Sprint 1 opportunity list/detail/edit/archive, Sprint 2 evidence metadata/files,
SQLite revision controls, audit history, S.P.A.T.I.A.L. assessment endpoints,
reports, queues, and AnchorOS lifecycle adapter remain in place.

## Explicitly not added

- external AI or internet-backed Knowledge Review;
- a new S.P.A.T.I.A.L. assessment workflow;
- Executive Opportunity Dossier generation;
- TA-14 integration;
- authentication, authorization, immutable audit storage, or independent
  evidence verification.

## Database change

Startup adds only the `knowledge_reviews` table and index when absent. Existing
tables and rows are not rewritten. A pre-installation source/database backup is
still mandatory for reliable Sprint 2 rollback.
