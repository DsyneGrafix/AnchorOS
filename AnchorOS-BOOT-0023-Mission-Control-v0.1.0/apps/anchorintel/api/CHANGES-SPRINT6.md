# AnchorIntel Sprint 6 Change Summary

Release: `anchorintel-api 0.6.0`

## Added

- durable `AR-000001` controlled archive identity;
- additive `archives` SQLite table, indexes, repository operations, and audit;
- deterministic 10-member ZIP package with canonical JSON and fixed ZIP metadata;
- external `data/archives/` storage with safe generated names and SHA-256;
- archive readiness and stale-provenance rejection;
- package preflight, persisted manifest, package hash, replay-summary hash, and counts;
- archive list, confirmation, detail, download, replay, and read-only UI;
- archive API paths and OpenAPI 3.1 documentation;
- `archive.prepared`, `.completed`, `.failed`, `.downloaded`, `.replayed`, and
  `.replay_failed` events;
- terminal lifecycle completion derived from persisted archive state; and
- comprehensive Sprint 6 integrity, restart, tamper, and rollback tests.

## Preserved

- Opportunity, Evidence, Knowledge Review, Assessment, and Dossier services;
- all upstream artifact IDs, revisions, outputs, exports, and replay behavior;
- external evidence-file storage and existing SQLite data;
- current UI language and OpenAPI behavior; and
- the unchanged S.P.A.T.I.A.L. engine.

## Explicitly not implemented

- restore/reopen workflow;
- billing, payments, discounts, TA-14, or new Knowledge Modules;
- internet research, external AI, or upstream analysis regeneration;
- immutable/WORM storage, digital signatures, or independent verification;
- production authentication, tenant isolation, HA, or load qualification; and
- automatic creation of Git tag `boot-0020`.

## Verification

- 40 AnchorIntel API tests pass;
- eight unchanged S.P.A.T.I.A.L. engine tests pass;
- the reference BOOT chain creates `AR-000001` and replays `PASS`;
- tampered archive bytes replay `FAIL`; and
- independent extracted-package verification is performed before delivery.
