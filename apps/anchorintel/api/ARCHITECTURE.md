# AnchorIntel API v1 Architecture

## Sprint 4 boundary

```text
Opportunity → Evidence → Knowledge Review → S.P.A.T.I.A.L. Assessment
 OI-*          EV-*          KR-*                    AS-*
```

Sprint 4 implements only the Knowledge Review → Assessment seam. It preserves
Sprint 1–3 services, does not generate an Executive Dossier (`ED-*`), does not
add Knowledge Modules, and does not change the S.P.A.T.I.A.L. engine.

## Layering

```text
Browser / API clients / future domain applications
                         ↓
AnchorIntel readiness and continuation-validity service
                         ↓
Persisted opportunity + active evidence + current Knowledge Review
                         ↓
AnchorIntel deterministic adapter v1.0.0
                         ↓
Existing S.P.A.T.I.A.L. engine v0.1.0 (unchanged)
                         ↓
SQLite AS record + immutable snapshot + provenance + replay hash + audit
```

AnchorOS supplies platform lifecycle and future gateway services. AnchorIntel
owns operational resource contracts and persisted provenance. S.P.A.T.I.A.L.
owns scoring, evidence confidence, gates, fatal-constraint precedence, and the
recommendation taxonomy. Applications request an assessment capability rather
than invoking internal score calculations.

## Readiness and strict execution

The opportunity-scoped assessment service fails closed unless:

- the opportunity exists and is active;
- at least one active evidence record exists;
- a selected Knowledge Review exists, is `Completed`, and is not superseded;
- its opportunity revision and evidence trace still match;
- its module remains Active with the same version and integrity hash; and
- the explicit adapter output satisfies the unchanged engine contract.

A selected stale review returns HTTP 409. The legacy `/v1/assessments/run`
route remains available for pre-existing full engine profiles and does not
participate in the Sprint 4 lifecycle state.

## Adapter contract

The engine requires eight dimension assessments, six mandatory gates, evidence,
and lifecycle controls. The adapter follows two rules:

1. complete persisted dimension/gate/lifecycle structures pass through; and
2. absent structures receive conservative, documented values based only on the
   persisted opportunity, active evidence, current review, and module dates.

The geographic module is not stretched into a funding, commercial, or delivery
finding. Uncovered domains remain low, provisional, or failed. Adapter
derivation text is stored and shown beside the engine explanation. This mapping
is versioned independently as `1.0.0` and participates in staleness.

## Immutable assessment snapshot

Each `AS-*` row stores:

| Surface | Stored content |
|---|---|
| Opportunity | Exact business fields and revision |
| Evidence | Sorted active records, revisions, classifications, and file hashes |
| Knowledge Review | Full persisted review output and replay identifiers |
| Knowledge Module | ID, version, integrity hash, effective date, review date |
| Engine input | Exact payload supplied to S.P.A.T.I.A.L. |
| Derivation | Adapter version and field-basis explanations |
| Provenance | IDs, revisions, hashes, engine version, adapter version, input hash |
| Decision | Recommendation, score, confidence, risk, gates, assumptions, explanation, trace |

Execution timestamp and assessment ID are stored outside deterministic replay
material. Identical persisted inputs, review, engine version, and adapter
version therefore produce identical results and replay hashes.

## Replay

Replay reads the immutable snapshot rather than current mutable records,
re-executes the installed engine, reconstructs the operational result, and
compares canonical structured output plus SHA-256 hash. It records an
`assessment.replayed` audit event. It creates no new evidence, review, or
assessment and does not advance lifecycle state.

The replay hash supports integrity comparison. It does not establish source
truth, independent verification, digital-signature identity, cryptographic
immutability, or tamper-evident persistence.

## Continuation validity

An operational assessment remains lifecycle-eligible only while:

| Condition | Stale when |
|---|---|
| Opportunity | Archived or revision differs |
| Evidence | Active trace differs by ID, revision, file hash, status, or confidence |
| Review | Missing, incomplete, superseded, stale, revised, or output hash differs |
| Module | Missing, inactive, version differs, or integrity hash differs |
| Engine | Installed version differs |
| Adapter | Installed version differs |

Stale `AS-*` records remain visible. First detection is audited once. A new
Knowledge Review and assessment are the recovery path; prior artifacts are not
overwritten.

## Lifecycle derivation

The opportunity service derives state from persisted records on every read:

- Attach Evidence: at least one active evidence row;
- Knowledge Module Review: at least one current completed review;
- Run S.P.A.T.I.A.L.: at least one current lifecycle-eligible operational
  assessment; and
- Executive Dossier and Archive Results: pending in Sprint 4.

There is no OI-000001 lifecycle special case. Reference seeding uses the same
services and produces the provenance chain `OI-000001 → EV-000001 → KR-000001
→ AS-000001`.

## Additive schema migration

Repository initialization retains the existing `assessments` table and adds
missing columns with idempotent `ALTER TABLE` statements:

```text
assessment_kind, knowledge_review_id, engine_version, adapter_version,
replay_hash, provenance_json, revision, updated_at
```

Existing rows receive safe defaults and remain readable as `legacy`. No table
or row is dropped. The migration is forward-safe but not a substitute for a
rollback backup because Sprint 3 source does not understand Sprint 4 columns.

## Security boundary

The SQLite audit log is an application record and is not tamper-evident. The
reference server is loopback-bound and lacks production identity, authorization,
isolation, encryption, gateway, availability, and load controls. No result
should be treated as independently verified or as professional advice.
