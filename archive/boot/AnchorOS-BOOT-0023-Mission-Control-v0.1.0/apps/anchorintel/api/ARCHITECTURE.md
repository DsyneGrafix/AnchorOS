# AnchorIntel API v1 Architecture

## Sprint 6 boundary

```text
Opportunity → Evidence → Knowledge Review → Assessment → Dossier → Archive
 OI-*          EV-*          KR-*             AS-*       ED-*       AR-*
```

Sprint 6 implements only Dossier → controlled Archive and terminal read-only
closure. It preserves Sprint 1–5 services, adds no commercial capability, does
not add Knowledge Modules, and does not rerun upstream analysis.

## Layering

```text
Browser and API clients
        ↓
Archive readiness and provenance validation
        ↓
Persisted OI + active EV + current KR + current AS + current ED
        ↓
Deterministic archive builder v1.0.0
        ↓
External ZIP in data/archives + SQLite AR metadata + audit
        ↓
Read-only opportunity and replay verifier
```

S.P.A.T.I.A.L. owns recommendation semantics. The dossier copies those semantics
exactly. The archive copies persisted records and existing dossier outputs; it
does not compute a decision.

## Archive record

Each `AR-*` row stores:

| Surface | Persisted value |
|---|---|
| Identity | Archive and opportunity IDs |
| Revisions | Opportunity, evidence trace, review, and assessment revisions |
| Provenance | Review, module/version/hash, assessment/engine/hash, dossier/version/hash |
| Control | Status, reason, execution source, archive timestamp |
| Package | Manifest, SHA-256, replay-summary SHA-256, counts, controlled location |
| Metadata | Created and updated timestamps |

The source opportunity revision and `updated_at` do not change during archive
closure. Archive state lives in the opportunity container columns and `archives`
row, preserving upstream replay identity.

## Deterministic package

The package builder uses sorted canonical JSON, fixed ZIP member order, fixed ZIP
timestamps and permissions, and fixed compression settings. `manifest.json`
contains the archive identity, record/file counts, provenance, boundary notice,
and SHA-256/size for every other member. The package hash covers the final ZIP.

Archive creation calls dossier replay but never assessment execution, Knowledge
Module execution, evidence acquisition, external AI, or internet access.

## Replay

Archive replay reads only the persisted ZIP and archive row. It verifies:

- package SHA-256;
- exact persisted manifest;
- safe, unique, complete member names;
- each included file hash and size;
- opportunity/evidence/review/assessment/dossier IDs;
- all stored revisions;
- manifest-to-database provenance equality;
- dossier and assessment replay hashes; and
- Knowledge Module integrity hash.

Replay records `archive.replayed` or `archive.replay_failed` and returns `PASS`
or `FAIL` with a reason summary. It does not silently repair or replace a package.

## Lifecycle derivation

The Opportunity Service derives every step from persisted records:

- Attach Evidence: active evidence exists;
- Knowledge Module Review: a current completed review exists;
- Run S.P.A.T.I.A.L.: a current assessment exists;
- Generate Executive Opportunity Dossier: a current dossier exists; and
- Archive Results: a persisted current `Archived` `AR-*` row exists.

There is no `OI-000001` lifecycle special case. Successful archive creation also
sets the opportunity container to archived/read-only. Upstream records remain
current because archival itself is not treated as upstream staleness.

## Additive schema migration

Repository initialization creates `archives`, an opportunity/date index, and a
partial unique index preventing multiple `Prepared`/`Archived` records for one
opportunity. Foreign keys reference the opportunity, review, assessment, and
dossier. Initialization is idempotent and drops or rewrites no prior data.

Generated ZIP files live outside SQLite. A database row without its corresponding
external file replays `FAIL`; backup and rollback must therefore preserve source,
SQLite, evidence storage, and archive storage together.

## Security boundary

Archive hashes and audit rows are integrity records, not immutable proof. The
reference server lacks production identity, authorization, tenant isolation,
encryption, gateway, HA, and load controls. No archive establishes source truth,
external verification, professional advice, or customer approval.
