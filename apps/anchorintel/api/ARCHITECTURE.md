# AnchorIntel API v1 Architecture

## Decision-operating-system boundary

```text
Research → Evidence → Knowledge Modules → Opportunity → Assessment
         → Decision → Lifecycle → Revalidation → Learning → Knowledge Library
```

Sprint 3 implements only the Evidence → Knowledge Modules → Opportunity seam.
It preserves the Sprint 1 and Sprint 2 services and prepares structured output
for later assessment without changing S.P.A.T.I.A.L., reporting, or dossier
behavior.

## Layering

```text
Browser / API clients / future AnchorFiber applications
                         ↓
AnchorIntel business services and lifecycle derivation
                         ↓
Opportunity + active evidence snapshots
                         ↓
Versioned local Knowledge Module registry and deterministic executor
                         ↓
SQLite review records, evidence traces, replay hashes, audit events
                         ↓
Existing S.P.A.T.I.A.L. adapter (unchanged in Sprint 3)
```

AnchorOS supplies platform lifecycle and future authenticated gateway services.
AnchorIntel owns opportunity, evidence, knowledge-review, assessment, reporting,
and lifecycle contracts. S.P.A.T.I.A.L. owns its assessment methodology. Domain
applications consume these stable capabilities rather than importing internal
calculations.

## Source definitions versus runtime records

| Surface | Content | Location |
|---|---|---|
| Knowledge Module source | ID, version, scope, questions, criteria, evidence categories, limitations, dates, output schema, integrity hash | `anchorintel_api/knowledge_modules/*.json` |
| Knowledge Review runtime | Module/version/hash, opportunity revision, evidence trace, input/output hashes, output, confidence, status, revisions, supersession, timestamps | SQLite `knowledge_reviews` |
| Evidence metadata | Controlled metadata, revision, archive state, file metadata and hash | SQLite `evidence` |
| Evidence bytes | Uploaded file content | `data/evidence-files/` |

Module loading validates required fields, ID format, dates, status, question
shape, uniqueness, and canonical SHA-256 integrity. Invalid or modified modules
fail closed at registry construction.

## Deterministic execution

The `AKM-GEO-FL-001` executor accepts no network, model, or clock input. The
review snapshot consists of:

1. module ID, version, and integrity hash;
2. persisted opportunity fields and revision;
3. sorted active evidence records and revisions;
4. exact evidence trace; and
5. sorted IDs of archived evidence excluded from active inputs.

Canonical JSON produces an input snapshot hash. The structured result is also
canonicalized and hashed. Two executions over identical inputs produce equal
input hashes, output objects, and output hashes. Execution identity and time are
stored separately in the review row, so they do not introduce output variance.

## Review persistence and supersession

Public IDs are sequential (`KR-000001`, `KR-000002`, ...). Normal rerun creates
a new row linked by `supersedes_review_id`, changes the prior row to
`Superseded`, and records both supersession and rerun audit events. Prior output
is preserved. A failed executor creates an `Incomplete` review with `Unknown`
confidence and records a failure audit event.

## Dynamic staleness and continuation validity

A completed review is lifecycle-eligible only while the conditions that
justified it remain true:

| Condition | Stale when |
|---|---|
| Opportunity | Archived or revision differs |
| Evidence | Current active evidence trace differs by ID, revision, file hash, status, or confidence |
| Module | Missing, inactive, version differs, or integrity hash differs |
| Review | Not `Completed` or already superseded |

Stale records remain visible and traceable but cannot complete Knowledge Module
Review. The first detection is audited once. Rerun is the recovery mechanism.
This enforces a narrow continuation-validity rule: the review does not outlive
the persisted conditions that justified it.

## Additive schema initialization

Repository startup creates `knowledge_reviews` and its opportunity/date index
with `CREATE TABLE IF NOT EXISTS`. The existing Sprint 2 evidence-column checks
remain. No existing table is dropped or rewritten. The migration is idempotent,
but rollback still requires the pre-installation database backup because Sprint
2 code does not understand Sprint 3 review records.

## Lifecycle derivation

The opportunity service derives workflow state on every read:

- Attach Evidence: complete when at least one non-archived evidence row exists.
- Knowledge Module Review: complete when at least one current, active,
  lifecycle-eligible completed review exists.
- S.P.A.T.I.A.L., dossier, and archive: unchanged and pending unless their
  existing services change them outside Sprint 3.

There is no OI-000001 special case. Reference seeding calls the same review
service used by future opportunities.

## Security boundary

SHA-256 supports integrity comparison, replay identity, and module-change
detection. It does not establish source truth, legal authenticity, independent
verification, or immutable storage. The SQLite audit log is an application
record and is not tamper-evident. Production identity, authorization, isolation,
encryption, gateway, and availability controls remain outside this reference
build.
