# AnchorIntel API

AnchorIntel API v0.5.0 is the AnchorOS-facing service for the persisted
S.P.A.T.I.A.L. opportunity lifecycle. Sprint 5 adds the first Executive
Opportunity Dossier: a deterministic, replayable `ED-*` artifact rendered as
HTML, PDF, and JSON entirely from persisted AnchorIntel records.

Sprint 1–4 behavior remains intact. Dossier generation does not browse the
internet, invoke an external AI model, create or regenerate evidence, rerun a
Knowledge Module, rerun S.P.A.T.I.A.L., or reinterpret its recommendation.

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

Open <http://127.0.0.1:8080/opportunities/OI-000001>. The launcher is safe for
parent paths containing spaces and idempotently seeds the bounded reference
chain when its prerequisites are current:

- `OI-000001` — Florida Power & Light Asset Intelligence Opportunity;
- `EV-000001` — Sirius Logic Systems reference analysis;
- `KR-000001` on a fresh database, or the existing current review;
- `AS-000001` on a fresh database, or the existing current assessment; and
- `ED-000001` on a fresh database, or the existing dossier.

Existing active, edited, archived, or superseded records are never overwritten.
The sample assessment currently returns `Hold`, `33.2/100`, and `Low` engine
evidence confidence. Those are bounded engine outputs, not claims about or an
endorsement by Florida Power & Light.

Manual start from `apps/anchorintel/api`:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m anchorintel_api --database data/anchorintel.db --seed-reference
```

## Sprint 5 workflow

```text
OI-000001 → EV-000001 → KR-000002 → AS-000001 → ED-000001
Opportunity   Evidence    Review       Assessment    Dossier
```

IDs are not hard-coded into report logic. The example above is preserved when
those records exist; a fresh reference database naturally uses its current
`KR-000001`. Every dossier follows the assessment's persisted review link.

## Dossier API and workspace

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/opportunities/{id}/dossiers/new` | Readiness and bounded-generation screen |
| `POST` / `GET` | `/opportunities/{id}/dossiers` | Generate or list dossiers |
| `GET` | `/opportunities/{id}/dossiers/{dossier_id}` | View canonical dossier and traceability |
| `POST` | `/opportunities/{id}/dossiers/{dossier_id}/replay` | Re-render the stored snapshot and compare all artifacts |
| `GET` | `/opportunities/{id}/dossiers/{dossier_id}/html` | Download standalone HTML |
| `GET` | `/opportunities/{id}/dossiers/{dossier_id}/pdf` | Download deterministic letter-size PDF |
| `GET` | `/opportunities/{id}/dossiers/{dossier_id}/json` | Download canonical JSON |

The OpenAPI 3.1 contract is at `/v1/openapi.json`.

## Persisted report boundary

An `ED-*` record consumes exactly:

1. current opportunity fields, revision, and timestamps;
2. sorted active evidence summaries and revisions;
3. the persisted Knowledge Review identified by the assessment;
4. the persisted S.P.A.T.I.A.L. assessment result and provenance; and
5. dossier format version `1.0.0`.

The report includes executive, opportunity, evidence, Knowledge Review, and
assessment summaries; exact gate results and recommendation; traceability; input,
assessment, engine-input, and dossier replay hashes; versions; and explicit
bounded-use statements. Evidence is summarized rather than duplicated.

The richer HTML export is print-friendly. The PDF is a dependency-free,
deterministic, paginated text report. JSON is canonical business content. All
three survive repository restart.

## Determinism, replay, and staleness

The input hash covers the selected persisted snapshot. Report-state time is
derived from persisted timestamps, not the generation clock. Repeating a
generation request for the same opportunity and input hash idempotently returns
the existing dossier. Replay rebuilds JSON, HTML, and PDF from the stored snapshot
and compares each artifact plus the input and replay hashes.

SHA-256 is used for reproducibility and integrity comparison. It is not proof of
source truth, independent verification, digital-signature identity,
cryptographic immutability, or a tamper-evident database.

A dossier becomes stale if its opportunity, active evidence, Knowledge Review,
or assessment ceases to be current, or a successor dossier supersedes it. Stale
artifacts remain viewable, downloadable, and replayable, but no longer complete
the dossier lifecycle step.

## Storage and migration

Sprint 5 creates one additive SQLite table, `executive_dossiers`, containing the
input snapshot, canonical document, HTML, PDF bytes, identifiers, hashes,
versions, and timestamps. No existing table or row is removed or rewritten.
Uploaded evidence remains outside SQLite. Runtime databases and customer files
are excluded from the ZIP.

Back up source, SQLite DB/WAL/SHM files, and the evidence store before
installation. See `INSTALL-SPRINT5.md` for the exact file inventory, schema,
staging procedure, and complete Sprint 4 restoration steps.

## Verification

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v

cd ../spatial-opportunity-engine
python3 -m unittest discover -s tests -v
```

The source build is verified with 32 API tests and the unchanged eight engine
tests. PDF exports are also checked with Poppler (`pdfinfo`, `pdftotext`, and
`pdftoppm`). See `VERIFICATION.md` and `SPRINT5-VERIFICATION-CHECKLIST.md`.

## Production boundary

This remains a loopback-bound reference service. It does not provide production
authentication, authorization, TLS termination, tenant isolation, rate limits,
database encryption, high availability, tamper-evident audit storage, or load
qualification. Do not expose it directly to an untrusted network. Output is not
legal, regulatory, engineering, environmental, financial, procurement, or
investment advice and is not a claim of independent verification.
