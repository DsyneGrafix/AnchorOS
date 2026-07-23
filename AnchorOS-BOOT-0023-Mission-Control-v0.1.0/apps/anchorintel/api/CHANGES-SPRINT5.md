# AnchorIntel Sprint 5 Change Summary

Release: `anchorintel-api 0.5.0`

## Added

- durable `ED-000001` Executive Opportunity Dossier identity;
- additive `executive_dossiers` SQLite table and repository operations;
- deterministic report snapshot, canonical document, input hash, and replay hash;
- persisted standalone HTML and PDF plus canonical JSON download;
- dossier readiness, idempotent generation, continuation validity, and replay;
- opportunity dossier list, generation page, detail page, downloads, and replay UI;
- dossier API paths and OpenAPI 3.1 schemas;
- `dossier.generated` and `dossier.replayed` audit events;
- lifecycle completion derived from a current persisted dossier; and
- reference seed support for `ED-000001`.

## Preserved

- Opportunity, Evidence, Knowledge Review, and Assessment services;
- all prior identifier, revision, archive, audit, and stale-input behavior;
- the existing S.P.A.T.I.A.L. engine and adapter outputs; and
- loopback default, SQLite, external evidence-file storage, and AnchorIntel UI.

## Explicitly not implemented

- Archive Results;
- new Knowledge Modules;
- dossier interpretation or recommendation rewriting;
- internet research, external AI, or evidence regeneration;
- authentication, tenant isolation, tamper-evident persistence, or HA; and
- production load or multi-process concurrency qualification.

## Verification

- 32 AnchorIntel API tests pass;
- 8 unchanged S.P.A.T.I.A.L. engine tests pass;
- Poppler validates and renders the deterministic PDF; and
- an isolated extracted-package verification is required before installation.
