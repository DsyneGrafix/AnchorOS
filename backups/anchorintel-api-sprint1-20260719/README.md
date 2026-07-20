# AnchorIntel API

AnchorIntel API v0.1.0 is the AnchorOS-facing service interface for the complete S.P.A.T.I.A.L. infrastructure-opportunity assessment lifecycle. It exposes business capabilities—opportunities, evidence, assessments, reports, lifecycle queues, and revalidation—without exposing scoring functions as public endpoints.

The service uses the deterministic `spatial-opportunity-engine` as its assessment framework and SQLite for durable local records. It requires Python 3.10 or newer and has no third-party runtime dependencies beyond the sibling engine package.

## Implemented v1 boundary

| Service | Capabilities |
|---|---|
| Opportunity | Create, list, retrieve, replace, and archive opportunity records; browser list/detail/edit/archive workspace |
| Evidence | Create, retrieve, reclassify, and promote evidence through controlled A → S → V transitions |
| Assessment | Hydrate an opportunity with its evidence, run the engine, and preserve an immutable input/result snapshot |
| Reporting | Return the stored assessment as JSON or Markdown |
| Lifecycle | List Hold, Monitor, and Pursue queues; find reviews due; run traceable revalidation |
| Administration | Read the append-only actor/action audit trail |

Knowledge Modules, identity and access management, organizations, notifications, dashboards, integrations, and PDF/DOCX rendering are intentionally deferred. The API is versioned under `/v1` so those capabilities can be added without coupling clients to the current engine implementation.

## Quick start

The canonical AnchorOS application layout is:

```text
AnchorOS/
└── apps/
    └── anchorintel/
        ├── api/
        └── spatial-opportunity-engine/
```

From the AnchorOS repository root, use the path-safe launcher:

```bash
./apps/anchorintel/api/start-anchorintel.sh
```

The service listens on `127.0.0.1:8080` by default. Open
`http://127.0.0.1:8080/opportunities` to use the Opportunity workspace.
`--seed-reference` idempotently creates `OI-000001` without overwriting an
existing or archived record. The launcher resolves its own absolute path, so
spaces in the parent directory name do not require special handling. Server
arguments may be appended, for example
`./apps/anchorintel/api/start-anchorintel.sh --port 8081`.

The equivalent manual command from the `api` directory is:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m anchorintel_api --database data/anchorintel.db --seed-reference
```

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/v1/openapi.json
```

Optional editable installation:

```bash
python -m pip install -e ../spatial-opportunity-engine -e .
anchorintel-api --database data/anchorintel.db
```

Configuration can be provided by flags or environment variables:

| Flag | Environment | Default |
|---|---|---|
| `--host` | `ANCHORINTEL_HOST` | `127.0.0.1` |
| `--port` | `ANCHORINTEL_PORT` | `8080` |
| `--database` | `ANCHORINTEL_DATABASE` | `data/anchorintel.db` |
| `--seed-reference` | `ANCHORINTEL_SEED_REFERENCE` | disabled |

## BOOT-0020 reference opportunity

`OI-000001` is the canonical implementation, test, demo, and presentation
record for AnchorIntel:

| Field | Value |
|---|---|
| Title | Florida Power & Light Asset Intelligence Opportunity |
| Organization | Florida Power & Light |
| Sector | Electric Utility |
| Status | New |
| Geography | Florida |
| Infrastructure class | Electric Utility |

The seed records the BOOT-0020 workflow from opportunity creation through
evidence, knowledge review, S.P.A.T.I.A.L. assessment, dossier generation, and
archive. Sprint 1 marks Create and Save complete; later services advance the
remaining stages. The bundled `data/anchorintel.db` already contains the active
reference record at revision 1.

### Opportunity workspace

| Route | Purpose |
|---|---|
| `GET /opportunities` | Active opportunity list |
| `GET /opportunities?include_archived=true` | Active and archived records |
| `GET /opportunities/{id}` | Opportunity detail and workflow |
| `GET /opportunities/{id}/edit` | Revision-controlled edit form |
| `POST /opportunities/{id}/edit` | Save profile changes |
| `POST /opportunities/{id}/archive` | Recoverably archive a record |

## API surface

| Method | Route | Purpose |
|---|---|---|
| `POST` / `GET` | `/v1/opportunities` | Create or list opportunities |
| `GET` / `PUT` / `DELETE` | `/v1/opportunities/{id}` | Retrieve, replace, or archive an opportunity |
| `POST` / `GET` | `/v1/evidence` | Create or list evidence |
| `GET` / `PATCH` | `/v1/evidence/{id}` | Retrieve or reclassify evidence |
| `POST` | `/v1/evidence/{id}/verify` | Promote A → S or S → V with a source and verification note |
| `POST` | `/v1/assessments/run` | Run an assessment from current stored records |
| `GET` | `/v1/assessments/{id}` | Retrieve an immutable assessment result |
| `POST` | `/v1/reports/json` | Return the stored JSON decision record |
| `POST` | `/v1/reports/markdown` | Return the stored Markdown decision record |
| `GET` | `/v1/lifecycle/reviews/due` | List review dates at or before `as_of` |
| `POST` | `/v1/lifecycle/revalidate` | Create a new assessment that supersedes the prior one |
| `GET` | `/v1/lifecycle/holds` | List Hold opportunities |
| `GET` | `/v1/lifecycle/monitors` | List Monitor opportunities |
| `GET` | `/v1/lifecycle/pursue` | List Pursue opportunities |
| `GET` | `/v1/admin/audit` | Read audit events |

The live OpenAPI 3.1 contract is available at `/v1/openapi.json`.

## Typical lifecycle

1. Create an opportunity without embedded evidence.
2. Create evidence records associated with the opportunity.
3. Reclassify evidence with `PATCH`; use `/verify` for promotion to Supported or Verified.
4. Run an assessment. The service snapshots the current opportunity and evidence before invoking the engine.
5. Generate reports from the stored result, not from mutable live records.
6. Work the Hold, Monitor, Pursue, and due-review queues.
7. Revalidate after material evidence or lifecycle changes. The new assessment references the assessment it supersedes.

The bundled `examples/load_and_assess.py` client loads a complete engine profile through the HTTP service and runs this flow.

## Control behavior

- Evidence states are `V` (Verified), `S` (Supported), `A` (Assumption), `U` (Unknown), and `D` (Disputed).
- Promotion is limited to A → S → V and requires both a source and verification note.
- `PATCH /evidence/{id}` may correct or downgrade classification, but cannot bypass promotion controls.
- Assessments and their input snapshots are immutable.
- Revalidation creates a new assessment linked by `supersedes_assessment_id`.
- Opportunity deletion is a recoverable archive operation; no record is physically deleted.
- Responses carry `X-Request-ID`. Mutable resources carry integer revisions as `ETag`; clients may send `If-Match` to detect conflicting writes.
- `X-Actor` supplies the audit actor in this reference build.
- Browser edits use the same Opportunity Service and SQLite repository as the
  `/v1` API; the workspace is not a parallel persistence path.

## AnchorOS integration

`anchoros-service.json` declares the stable service capabilities and entrypoint. `AnchorIntelAnchorOSService` provides `register`, `start`, `stop`, and `health` lifecycle methods so an AnchorOS module adapter can manage the service without importing assessment internals.

This is an adapter-ready boundary, not a claim that it has been registered against a specific AnchorOS runtime build. The manifest may be translated into the repository's final module-registration format when that contract is fixed.

## Security and production boundary

This release is a local reference service. It binds to loopback by default and does not implement authentication, authorization, TLS termination, tenant isolation, rate limits, secrets management, or database encryption. Do not expose it to an untrusted network. Production deployment should place an authenticated AnchorOS gateway in front of it and replace the caller-supplied `X-Actor` with verified identity context.

The service supports decision intelligence; it does not certify source truth, engineering design, safety, legal compliance, funding eligibility, procurement status, financial returns, or commercial success.

## Verification

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python -m unittest discover -s tests -v
```

See `VERIFICATION.md` for the tested behaviors and release evidence.
