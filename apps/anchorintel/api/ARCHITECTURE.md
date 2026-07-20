# AnchorIntel API v1 Architecture

## Decision-operating-system boundary

The long-range operating loop is:

```text
Research → Evidence → Knowledge Modules → Opportunity → Assessment
         → Decision → Lifecycle → Revalidation → Learning → Knowledge Library
```

Sprint 2 changes only the Evidence → Opportunity boundary. It establishes a
production-oriented evidence record and file-storage interface while preserving
the existing Opportunity, assessment, reporting, lifecycle, and administration
services. Research acquisition, Knowledge Modules, new S.P.A.T.I.A.L. work, and
the Executive Opportunity Dossier remain outside this sprint.

## Layering

```text
Clients / AnchorFiber / Opportunity workspace
                    ↓ HTTP /v1 and server-rendered commands
AnchorIntel business services and lifecycle controls
                    ↓ stable adapter
S.P.A.T.I.A.L. assessment engine
                    ↓
SQLite metadata, external evidence files, assessment snapshots, audit events
                    ↑
AnchorOS register / start / stop / health
```

The API owns resource identity, revisions, evidence transitions, lifecycle events, persistence, audit, and reports. The Opportunity workspace calls the same business service as API clients, so edits and archives preserve identical validation, concurrency, and audit behavior. The engine owns validation, scoring, confidence, gates, warnings, and deterministic recommendation. Clients never call a public `calculate_score` function.

`OI-000001` is installed through an idempotent bootstrap. Bootstrap never
overwrites an existing active or archived record, protecting manual edits,
linked evidence, and audit history.

## Sprint 2 evidence boundary

Evidence has two deliberately separated persistence surfaces:

| Surface | Stored content | Location |
|---|---|---|
| SQLite | IDs, opportunity relationship, controlled metadata, revision, archive state, timestamps, original filename, storage name, size, type, SHA-256 | `data/anchorintel.db` |
| File store | Uploaded bytes only | `data/evidence-files/` |

Uploaded bytes are never SQLite blobs. The service rejects path-bearing or
control-character filenames, generates a UUID-based storage name, writes the
file exclusively, calculates SHA-256, and stores the original filename only as
metadata. The 10 MiB default upload limit is enforced for both the multipart
request and decoded file. File replacement is intentionally deferred so a
metadata revision cannot silently alter the bytes supporting an evidence
record.

The public evidence ID is sequential (`EV-000001`, `EV-000002`, ...). SQLite's
row ID is surfaced as the internal database ID but is not used in routes.
Metadata revisions use integer optimistic concurrency. Normal application
operations archive rather than delete evidence, and archived file bytes remain
available for review.

## Safe schema initialization

Repository startup creates current tables when absent and inspects
`PRAGMA table_info(evidence)` when upgrading Sprint 1. It adds only the missing
`archived` and `archived_at` columns and the active-evidence index. Existing
opportunity, evidence, assessment, lifecycle, and audit rows are not rewritten.
The process is idempotent and is covered by a migration regression test.

Because SQLite cannot remove columns through this migration, the installation
procedure requires a database backup before first Sprint 2 startup. Sprint 1
code ignores the two additive columns, but the backup remains the authoritative
rollback point.

## Resource invariants

| Resource | Invariant |
|---|---|
| Opportunity | May be saved as an incomplete draft; must satisfy the engine contract before assessment |
| Evidence | Belongs to one active opportunity; managed metadata uses controlled values; files live outside SQLite; promotion to S or V remains on the inherited verification interface |
| Assessment | Immutable snapshot of the opportunity and all current evidence plus engine result |
| Report | Projection of a stored assessment, so later record edits cannot rewrite history |
| Lifecycle event | Records prior state, resulting state, triggering assessment, reason, and time |
| Audit entry | Application actor/action record for mutations and assessment runs; no tamper-evidence or independent verification is claimed |

## Opportunity workflow derivation

The Opportunity Service queries persisted evidence every time it assembles an
opportunity detail record. `Attach Evidence` is complete when the opportunity
has one or more non-archived evidence rows and pending otherwise. The rule
contains no OI-000001 special case. Knowledge review, assessment, dossier, and
archive steps remain unchanged and incomplete in the reference workflow.

## Evidence audit events

Sprint 2 records `evidence.created`, `evidence.file_uploaded`,
`evidence.metadata_updated`, and `evidence.archived`. Each event includes the
evidence ID, opportunity ID, resulting revision, timestamp supplied by the audit
row, and a relevant change summary. The audit log is application-level SQLite
history, not an immutable ledger.

## Lifecycle state

An opportunity begins `Unassessed`. A successful assessment sets its operational queue to the engine recommendation: `Pursue`, `Validate`, `Monitor`, `Hold`, or `Reject`. The v1 dashboard-oriented endpoints expose Hold, Monitor, Pursue, and due-review queues. Validate and Reject remain visible through the opportunity resource and can receive dedicated routes without changing stored state.

Archive sets the lifecycle state to `Archived` and excludes the opportunity from normal collections. Revalidation requires a prior assessment, optionally updates lifecycle controls, and creates an immutable successor assessment.

## AnchorOS separation

- **AnchorOS** supplies process lifecycle, authenticated gateway concerns, shared operational services, and module registration.
- **AnchorIntel** supplies opportunity, evidence, assessment, reporting, revalidation, and learning-oriented service contracts.
- **S.P.A.T.I.A.L.** supplies the methodology and deterministic assessment framework.
- **AnchorFiber and future applications** consume the service and contribute domain records; they do not own the platform or engine lifecycle.

This keeps platform, framework, and application responsibilities explicit while allowing the engine to evolve behind `/v1/assessments/run`.
