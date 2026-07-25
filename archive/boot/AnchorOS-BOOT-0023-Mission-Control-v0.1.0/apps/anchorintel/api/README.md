# AnchorIntel API

AnchorIntel API v0.6.0 is the AnchorOS-facing service for the complete persisted
S.P.A.T.I.A.L. opportunity lifecycle. Sprint 6 adds controlled `AR-*` archives,
deterministic ZIP packages, manifest and package hashes, replay verification,
and read-only terminal closure.

The archive service consumes only persisted records and existing dossier
exports. It does not browse the internet, invoke external AI, create evidence,
rerun a Knowledge Module, rerun S.P.A.T.I.A.L., or reinterpret a decision.

## Quick start

Expected layout:

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

Open <http://127.0.0.1:8080/opportunities/OI-000001>.

Manual start from `apps/anchorintel/api`:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m anchorintel_api --database data/anchorintel.db --seed-reference
```

Reference seeding remains idempotent and stops at the current dossier. It does
not automatically archive an opportunity or overwrite edited, archived, stale,
superseded, or existing records.

## BOOT-0020 workflow

```text
OI-000001 → EV-000001 → KR-000002 → AS-000001 → ED-000001 → AR-000001
Opportunity   Evidence    Review       Assessment    Dossier       Archive
```

The installed database determines the current review ID. A fresh reference
database naturally begins with `KR-000001`; the verified BOOT-0020 provenance
fixture intentionally supersedes it to `KR-000002`. IDs are never rewritten by
archive logic.

## Archive API and workspace

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/opportunities/{id}/archives/new` | Readiness, warnings, and confirmation page |
| `POST` | `/opportunities/{id}/archives` | Create the terminal archive package |
| `GET` | `/opportunities/{id}/archives` | List persisted archives |
| `GET` | `/opportunities/{id}/archives/{archive_id}` | View archive identity, hashes, manifest, and provenance |
| `GET` | `/opportunities/{id}/archives/{archive_id}/download` | Download the persisted ZIP |
| `POST` | `/opportunities/{id}/archives/{archive_id}/replay` | Verify package, member hashes, IDs, revisions, and provenance |

The OpenAPI 3.1 contract is at `/v1/openapi.json`.

## Archive preconditions

Creation fails closed unless the opportunity is active and has:

1. at least one active evidence record;
2. a current completed Knowledge Review;
3. a current S.P.A.T.I.A.L. assessment;
4. a current Executive Opportunity Dossier;
5. a consistent persisted provenance chain;
6. a passing dossier replay; and
7. all required dossier exports.

Duplicate current archives and stale upstream records are rejected. Successful
archival preserves every source record, stores the package outside SQLite under
`data/archives/`, and places the opportunity in read-only archived state without
changing the source revision or source `updated_at` used by replay.

## Package and replay boundary

Every archive contains exactly:

```text
manifest.json
opportunity.json
evidence.json
knowledge-review.json
assessment.json
dossier.json
dossier.html
dossier.pdf
audit-summary.json
replay-summary.json
```

ZIP member order, metadata, compression settings, JSON serialization, and file
hashes are deterministic for identical archive inputs. Replay verifies the
stored package SHA-256, exact manifest, safe member set, per-file hashes and
sizes, record IDs and revisions, dossier and assessment replay hashes, Knowledge
Module integrity hash, and complete provenance chain. Results are `PASS` or
`FAIL` with reasons.

SHA-256 demonstrates reproducibility and integrity comparison inside this
application. It is not a digital signature, source-truth determination,
independent verification, immutable storage, or a tamper-evident database.

## Storage and additive migration

Sprint 6 creates the `archives` table and indexes idempotently. Archive packages
are external files; only metadata, manifest, hashes, counts, provenance, and the
controlled location are stored in SQLite. No existing table, row, evidence file,
review, assessment, or dossier is removed. Runtime databases, uploaded evidence,
and generated archives are excluded from the installation ZIP and Git.

See `INSTALL-SPRINT6.md` before installing. It provides exact file inventory,
backup, migration, isolated verification, overlay, and complete Sprint 5 restore
commands.

## Verification

From `apps/anchorintel/api`:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v

PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s ../spatial-opportunity-engine/tests -v
```

The source build has 40 passing AnchorIntel tests and eight unchanged engine
tests. See `VERIFICATION.md` and `SPRINT6-VERIFICATION-CHECKLIST.md`.

## Production boundary

This remains a loopback-bound reference service. It does not provide production
authentication, authorization, TLS termination, tenant isolation, rate limits,
database encryption, high availability, immutable audit storage, or load
qualification. Do not expose it directly to an untrusted network. Its output is
not legal, regulatory, engineering, environmental, financial, procurement, or
investment advice.
