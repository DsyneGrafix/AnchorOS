# AnchorIntel API

AnchorIntel API v0.3.0 is the AnchorOS-facing service for the S.P.A.T.I.A.L.
opportunity lifecycle. Sprint 3 adds a bounded Knowledge Service: versioned
local Knowledge Modules, deterministic Knowledge Reviews, persisted findings,
evidence traceability, replay hashes, supersession, dynamic staleness, audit
events, and lifecycle derivation.

Sprint 1 Opportunity Service and Sprint 2 Evidence Service behavior remain
intact. Sprint 3 does **not** add a new S.P.A.T.I.A.L. assessment flow, dossier
generation, internet research, external AI execution, or TA-14 integration.

## Quick start

Expected AnchorOS layout:

```text
AnchorOS/
└── apps/
    └── anchorintel/
        ├── api/
        └── spatial-opportunity-engine/
```

From the AnchorOS repository root:

```bash
./apps/anchorintel/api/start-anchorintel.sh
```

Open <http://127.0.0.1:8080/opportunities/OI-000001>. The path-safe launcher
works when parent directories contain spaces. It idempotently seeds:

- `OI-000001` — Florida Power & Light Asset Intelligence Opportunity;
- `EV-000001` — bounded Sirius Logic Systems reference evidence; and
- `KR-000001` — a generated `AKM-GEO-FL-001` review over persisted inputs.

Existing active or archived records are never overwritten.

Manual start from `apps/anchorintel/api`:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m anchorintel_api --database data/anchorintel.db --seed-reference
```

## Service boundary

| Service | Sprint 3 capability |
|---|---|
| Opportunity | List, view, edit, revision-control, and archive opportunities |
| Evidence | Metadata, file hashing/storage, editing, traceable archive, and controlled classification |
| Knowledge | Load versioned modules; run, retrieve, complete, supersede, and detect stale reviews |
| Assessment | Preserve the existing deterministic S.P.A.T.I.A.L. interface |
| Reporting | Preserve stored JSON and Markdown assessment reports |
| Lifecycle | Derive Evidence and Knowledge completion from persisted current state |
| Administration | Record application audit events |

## Knowledge Module contract

`AKM-GEO-FL-001` is a Git-versioned JSON definition with a canonical SHA-256
integrity hash. Its executor uses only the current persisted opportunity and
non-archived evidence. Given the same module version/hash, opportunity revision,
and evidence trace, it produces the same structured output and output hash.

The output records findings, assumptions, unknowns, risks, missing evidence,
confidence, consumed evidence IDs, excluded archived evidence IDs, limitations,
and a disclaimer. It never makes the final Pursue/Monitor/Reject decision.

`EV-000001` is explicitly described as Sirius Logic Systems reference analysis.
It is not an official Florida Power & Light record and does not establish
endorsement, procurement intent, ownership, service territory, funding
availability, or regulatory approval.

See `KNOWLEDGE-MODULE-FORMAT.md` and `AKM-GEO-FL-001.md`.

## Knowledge API and workspace

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/knowledge-modules` | List active modules (JSON or browser view) |
| `GET` | `/knowledge-modules/{module_id}` | Retrieve definition, version, questions, and hash |
| `GET` | `/opportunities/{id}/knowledge-reviews/new` | Browser run form |
| `POST` / `GET` | `/opportunities/{id}/knowledge-reviews` | Run or list persisted reviews |
| `GET` | `/opportunities/{id}/knowledge-reviews/{review_id}` | Review output, hashes, and evidence trace |
| `POST` | `/opportunities/{id}/knowledge-reviews/{review_id}/complete` | Complete a current draft review |
| `POST` | `/opportunities/{id}/knowledge-reviews/{review_id}/supersede` | Rerun over current inputs and preserve the prior review |

The complete OpenAPI 3.1 contract is at `/v1/openapi.json`.

## Lifecycle and staleness

Knowledge Module Review becomes complete only when an active `Completed` review:

- references an available Active module with the same version and hash;
- references the current opportunity revision;
- contains the exact current active-evidence trace; and
- has not been superseded.

Opportunity edits, evidence edits, evidence archive, module version changes, or
module hash changes make the prior result stale. A stale result remains
retrievable but no longer completes the lifecycle. Rerun creates a successor;
it never overwrites the old record. The S.P.A.T.I.A.L. and dossier steps remain
pending.

## Storage and migration

Runtime review results live in the additive SQLite `knowledge_reviews` table.
Module definitions remain source-controlled JSON. Evidence files remain outside
SQLite under `data/evidence-files`. Runtime databases, uploads, backups, caches,
and ZIP files are ignored and excluded from the installation package.

Repository startup uses `CREATE TABLE IF NOT EXISTS`; it does not rewrite
existing opportunity, evidence, assessment, lifecycle, or audit records. Back up
the database before first Sprint 3 startup. See `INSTALL-SPRINT3.md`.

## Audit boundary

The application records module loaded, review started, completed, failed,
superseded, rerun, and first detected stale events. Events include opportunity,
review, module version, opportunity revision, evidence trace, time, and a result
summary. This is an application audit trail, not immutable or independently
verified storage.

## Verification

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v

cd ../spatial-opportunity-engine
python3 -m unittest discover -s tests -v
```

See `VERIFICATION.md` and `SPRINT3-VERIFICATION-CHECKLIST.md`.

## Production boundary

This is a loopback-bound reference service. It does not yet provide
authentication, authorization, TLS termination, tenant isolation, rate limits,
database encryption, high availability, or tamper-evident audit storage. Do not
expose it directly to an untrusted network. Knowledge Review output is not legal,
regulatory, engineering, environmental, financial, or investment advice and is
not a claim of independent verification.
