# AnchorIntel Archive Package Format 1.0.0

## Purpose

An `AR-*` package is a deterministic, portable closure snapshot of one completed
AnchorIntel lifecycle. It is not a database backup, source-code bundle, evidence
truth certification, digital signature, or immutable-storage claim.

## Members

| Member | Content |
|---|---|
| `manifest.json` | Identity, provenance, counts, boundary, file hashes/sizes |
| `opportunity.json` | Persisted opportunity at the archived revision |
| `evidence.json` | Sorted active evidence records and revisions |
| `knowledge-review.json` | Persisted current Knowledge Review |
| `assessment.json` | Persisted current assessment and immutable input snapshot |
| `dossier.json` | Persisted canonical dossier record |
| `dossier.html` | Exact stored HTML export |
| `dossier.pdf` | Exact stored PDF export |
| `audit-summary.json` | Relevant pre-closure audit events |
| `replay-summary.json` | Passing dossier replay and upstream hash identities |

No uploaded evidence bytes, SQLite databases, unrelated opportunities, source
code, backups, temporary files, or generated runtime caches are included.

## Determinism

- JSON is UTF-8, sorted by key, indented by two spaces, and newline-terminated.
- Evidence is sorted by evidence ID.
- ZIP member order is fixed to the table above.
- ZIP timestamps are fixed to `1980-01-01T00:00:00`.
- File permissions and compression parameters are fixed.
- Each non-manifest member has SHA-256 and byte size in the manifest.
- The final ZIP has a package SHA-256 stored in SQLite.

Identical arguments to the pure builder produce identical bytes. An archive ID
and archive timestamp are part of the manifest, so a different archive identity
is intentionally a different package.

## Provenance object

The manifest and database row contain matching provenance for:

- opportunity ID and revision;
- evidence IDs, revisions, and file hashes when present;
- Knowledge Review ID/revision and module ID/version/integrity/output hashes;
- assessment ID/revision, engine version, and replay hash; and
- dossier ID/revision, format version, input hash, and replay hash.

## Verification

Replay first compares the final package hash, then validates ZIP safety, exact
member set, manifest equality, per-member hashes and sizes, record identities,
revisions, provenance, dossier/assessment replay hashes, and Knowledge Module
integrity hash. Any failed check yields `FAIL` and records a reason. Replay never
browses the internet, invokes external AI, or reruns upstream analysis.
