# AnchorIntel Knowledge Module Format

## Purpose

A Knowledge Module is version-controlled, human-readable decision context. It
asks bounded questions of persisted opportunity and evidence records and emits
structured review material for later assessment. It does not make the final
commercial recommendation or silently convert assumptions into facts.

## Required JSON fields

| Field | Contract |
|---|---|
| `module_id` | `AKM-{DOMAIN}-{JURISDICTION}-{NNN}` uppercase identifier |
| `name` | Human-readable module name |
| `version` | Immutable definition version |
| `purpose`, `scope`, `description` | Bounded intent and coverage |
| `domain`, `jurisdiction`, `publisher` | Ownership and applicability context |
| `applicability_criteria` | Array of criteria; never proof by itself |
| `required_evidence_categories` | Array of desired evidence classes |
| `review_questions` | Non-empty array of `{question_id, question}` objects |
| `assumptions` | Declared module-level assumptions |
| `known_limitations` | Explicit exclusions and cautions |
| `output_schema` | Named output collections and confidence field |
| `effective_date`, `review_date` | ISO `YYYY-MM-DD` dates |
| `status` | `Active`, `Inactive`, or `Retired` |
| `integrity_hash` | SHA-256 of canonical JSON excluding this field |

## Canonical integrity rule

The loader removes `integrity_hash`, serializes the remaining object as UTF-8
JSON with sorted keys and compact separators, and computes SHA-256. The stored
hash must match exactly. A missing field, malformed date, duplicate ID, invalid
question, or hash mismatch prevents registry construction.

Changing any definition content requires:

1. a new module version;
2. a recomputed integrity hash;
3. review of compatibility and limitations; and
4. rerun of affected opportunities.

Existing review rows retain their original module version and hash and become
stale when the available definition no longer matches.

## Executor boundary

Definitions are data, not executable code. A separately installed local
executor must explicitly support the module ID. Unsupported modules fail closed,
produce an `Incomplete` persisted review, and generate a failure audit event.
Sprint 3 installs only the deterministic executor for `AKM-GEO-FL-001`.

## Review output

Outputs use dispositions `Supported`, `Partially Supported`, `Unsupported`,
`Unknown`, or `Not Applicable` where relevant, and confidence `Unknown`, `Low`,
`Moderate`, or `High`. `Verified` is reserved for a future defined verification
basis and is not produced by the Sprint 3 executor.

Every review records the module trace, opportunity revision, sorted evidence
trace, input hash, output hash, reviewer/execution source, status, revision,
timestamps, and supersession link. The hashes support comparison and replay;
they are not a claim of source authenticity or immutable storage.
