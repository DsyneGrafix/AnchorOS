# AnchorIntel API

AnchorIntel API v0.4.0 is the AnchorOS-facing service for the S.P.A.T.I.A.L.
opportunity lifecycle. Sprint 4 connects the existing S.P.A.T.I.A.L. engine to
persisted opportunity, evidence, and Knowledge Review records. It adds stable
`AS-000001` identifiers, immutable execution snapshots, deterministic replay,
stale-input rejection, assessment audit events, and lifecycle derivation.

Sprint 1–3 behavior remains intact. Sprint 4 does **not** generate an Executive
Opportunity Dossier, add Knowledge Modules, browse the internet, invoke an LLM,
create evidence during assessment, or modify the scoring engine.

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
parent paths containing spaces and idempotently seeds:

- `OI-000001` — Florida Power & Light Asset Intelligence Opportunity;
- `EV-000001` — bounded Sirius Logic Systems reference evidence;
- `KR-000001` — a generated `AKM-GEO-FL-001` review; and
- `AS-000001` — a generated S.P.A.T.I.A.L. assessment of that persisted chain.

The reference assessment currently returns `Hold`, `33.2/100`, and `Low`
engine evidence confidence. Those are bounded engine outputs, not claims about
Florida Power & Light. Existing active or archived records are never overwritten.

Manual start from `apps/anchorintel/api`:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m anchorintel_api --database data/anchorintel.db --seed-reference
```

## Sprint 4 workflow

```text
OI-000001 → EV-000001 → KR-000001 → AS-000001
Opportunity   Evidence    Review       Assessment
```

An operational assessment consumes exactly:

1. the current opportunity and revision;
2. sorted active evidence and revisions;
3. a completed current Knowledge Review and revision;
4. the reviewed Knowledge Module version and integrity hash;
5. S.P.A.T.I.A.L. engine version `0.1.0`; and
6. AnchorIntel adapter version `1.0.0`.

No network, model, clock, or mutable external input participates in the result.
Execution time is stored separately and is excluded from replay identity.

## Assessment API and workspace

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/opportunities/{id}/assessments/new` | Readiness screen and bounded-run notice |
| `POST` / `GET` | `/opportunities/{id}/assessments` | Run or list operational assessments |
| `GET` | `/opportunities/{id}/assessments/{assessment_id}` | Decision, gates, explanation, trace, and hash |
| `POST` | `/opportunities/{id}/assessments/{assessment_id}/replay` | Re-execute the immutable stored snapshot and compare hashes |

The earlier `/v1/assessments/run` endpoint remains available for direct engine
profiles and backward compatibility. The new opportunity-scoped endpoint is the
strict lifecycle interface and requires a current completed Knowledge Review.
The complete OpenAPI 3.1 contract is at `/v1/openapi.json`.

## Explicit adapter boundary

The S.P.A.T.I.A.L. engine contract requires eight dimensions, six gates, and
lifecycle controls. When those are already persisted on the opportunity, the
adapter passes them through. Otherwise adapter v1.0.0 supplies documented,
conservative values from the bounded records. Unsupported domains—such as a
funding path not covered by the geographic module—remain low or failed rather
than being inferred as facts.

The exact adapter payload, derivation basis, opportunity snapshot, evidence
snapshot, Knowledge Review, and module identity are stored with every
assessment. The engine package under `spatial-opportunity-engine` is unchanged.

## Provenance, replay, and staleness

Every operational assessment persists:

- recommendation, score, confidence, risk profile, gates, assumptions,
  explanation, and evidence trace;
- opportunity, evidence, Knowledge Review, module, engine, and adapter identity;
- the exact engine input snapshot; and
- a canonical SHA-256 replay hash.

Replay re-executes the stored snapshot and compares both the structured result
and hash. SHA-256 is an integrity comparison mechanism; it is not proof of
source truth, independent verification, cryptographic immutability, or a
tamper-evident database.

An assessment becomes stale when the opportunity revision, active evidence
trace, source Knowledge Review, module, adapter, or engine version changes, or
the opportunity is archived. Stale results remain retrievable but no longer
complete `Run S.P.A.T.I.A.L.` in the lifecycle. The dossier step remains pending.

## Storage and migration

Sprint 4 extends the existing SQLite `assessments` table additively with kind,
Knowledge Review link, engine and adapter versions, replay hash, provenance,
revision, and update timestamp fields. Existing rows are retained as `legacy`.
No runtime database or uploaded evidence is included in the ZIP.

Back up source, SQLite database/WAL/SHM files, and the evidence file store before
installation. See `INSTALL-SPRINT4.md` for the exact changed-file inventory,
migration, installation, and Sprint 3 restoration procedure.

## Verification

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v

cd ../spatial-opportunity-engine
python3 -m unittest discover -s tests -v
```

The packaged build is verified with 27 API tests and the unchanged eight engine
tests. See `VERIFICATION.md` and `SPRINT4-VERIFICATION-CHECKLIST.md`.

## Production boundary

This is a loopback-bound reference service. It does not yet provide production
authentication, authorization, TLS termination, tenant isolation, rate limits,
database encryption, high availability, tamper-evident audit storage, or load
qualification. Do not expose it directly to an untrusted network. Assessment
output is not legal, regulatory, engineering, environmental, financial, or
investment advice and is not a claim of independent verification.
