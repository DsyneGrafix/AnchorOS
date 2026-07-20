# AnchorIntel API v1 Architecture

## Sprint 5 boundary

```text
Opportunity → Evidence → Knowledge Review → S.P.A.T.I.A.L. Assessment → Executive Dossier
 OI-*          EV-*          KR-*                    AS-*                  ED-*
```

Sprint 5 implements only the persisted Assessment → Dossier seam. It preserves
Sprint 1–4 services, adds no Knowledge Modules, does not redesign or rerun the
S.P.A.T.I.A.L. engine during reporting, and does not implement Archive Results.

## Layering

```text
Browser / API clients / future domain applications
                         ↓
AnchorIntel dossier readiness and continuation-validity service
                         ↓
Persisted opportunity + evidence + Knowledge Review + assessment
                         ↓
Pure dossier renderer v1.0.0
                 ↙       ↓       ↘
          canonical JSON  HTML  PDF
                         ↓
SQLite ED record + immutable snapshot + hashes + audit
```

AnchorOS supplies platform lifecycle and future gateway services. AnchorIntel
owns resource contracts and provenance. S.P.A.T.I.A.L. remains the sole owner of
its recommendation, score, confidence, gate, and risk semantics. The reporting
layer copies those values exactly and never calculates a new decision.

## Readiness

Generation fails closed unless:

- the opportunity exists and is active;
- active evidence exists;
- a current completed Knowledge Review is linked by the assessment;
- the selected operational assessment exists and is lifecycle-eligible; and
- all assessment continuation-validity rules still pass.

An optional `assessment_id` may be supplied, but stale assessments are rejected.
The default is the current lifecycle-eligible operational assessment.

## Immutable dossier snapshot

Each `ED-*` row stores:

| Surface | Stored content |
|---|---|
| Opportunity | ID, business summary, revision, created/updated timestamps |
| Evidence | Sorted active IDs, titles, status, confidence, revision, source, file hash |
| Knowledge Review | ID, revision, module/version/hash, output hash, bounded summaries |
| Assessment | ID, revision, exact result subset, engine/adapter versions, hashes, execution time |
| Canonical report | Executive, opportunity, evidence, review, assessment, trace, replay, footer |
| Exports | Standalone HTML and PDF bytes; JSON derives exactly from the stored canonical report |
| Identity | Input hash, replay hash, format version, predecessor link, timestamps |

Generation time is stored as row metadata and is excluded from report identity.
The report-state timestamp is the maximum relevant persisted input timestamp.
Identical inputs therefore produce identical JSON, HTML, PDF, input hashes, and
replay hashes.

## Idempotency and replay

`(opportunity_id, input_hash)` is unique. Repeating generation over identical
records returns the existing dossier instead of creating a time-dependent copy.

Replay reads `input_snapshot_json`, invokes only the pure report renderer, and
compares:

- canonical document and JSON;
- exact HTML text;
- exact PDF bytes;
- input hash; and
- dossier replay hash.

It records `dossier.replayed` and does not rerun upstream logic or advance state.

## Continuation validity

An `ED-*` artifact remains lifecycle-eligible only while:

| Condition | Stale when |
|---|---|
| Opportunity | Archived or revision differs |
| Evidence | Active trace changes through the source assessment |
| Review | Missing, incomplete, superseded, stale, or provenance differs |
| Assessment | Missing, superseded, stale, or no longer lifecycle-eligible |
| Dossier | A successor explicitly supersedes it |

Stale dossiers remain durable exports. A current Knowledge Review, assessment,
and dossier are the recovery path; prior artifacts are never overwritten.

## Lifecycle derivation

The Opportunity Service derives state from persisted records on every read:

- Attach Evidence: at least one active evidence row;
- Knowledge Module Review: a current completed review;
- Run S.P.A.T.I.A.L.: a current operational assessment;
- Generate Executive Opportunity Dossier: a current `ED-*` row; and
- Archive Results: pending in Sprint 5.

There is no `OI-000001` special case in lifecycle calculation. Reference seeding
uses the same public services. A real `KR-000002 → AS-000001` relationship is
preserved in the dossier instead of being rewritten to the fresh-database example.

## Additive schema migration

Repository initialization creates `executive_dossiers` with foreign keys to
opportunity, Knowledge Review, assessment, and optional predecessor. A unique
input-hash constraint enforces idempotency. Initialization is idempotent and
drops or rewrites no existing records.

Sprint 4 source cannot read this table as a business resource, so safe rollback
restores the complete pre-install source and SQLite/evidence backup together.

## Security boundary

The SQLite audit log and hashes are application records, not tamper-evident
proof. The reference server lacks production identity, authorization, isolation,
encryption, gateway, availability, and load controls. No dossier establishes
source truth, external verification, professional advice, or customer approval.
