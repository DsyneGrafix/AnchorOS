# AnchorIntel Sprint 4 Change Summary

Release: `anchorintel-api 0.4.0`

## Added

- Opportunity-scoped S.P.A.T.I.A.L. readiness, run, list, detail, and replay
  capabilities.
- Stable sequential `AS-000001` assessment identifiers.
- Deterministic adapter v1.0.0 between persisted AnchorIntel records and the
  unchanged S.P.A.T.I.A.L. v0.1.0 engine contract.
- Immutable opportunity/evidence/review/module/engine-input snapshots.
- Assessment provenance, replay hashes, engine/adapter versions, risk profile,
  explanation, assumptions, gates, and evidence trace.
- Dynamic assessment staleness and lifecycle eligibility.
- Reference `AS-000001` generation from `OI-000001 → EV-000001 → KR-000001`.
- Assessment run/detail browser screens consistent with the existing workspace.
- Audit events for completed execution, replay, and first stale detection.
- Additive Sprint 3 database migration and rollback documentation.

## Preserved

- Opportunity, Evidence, Knowledge, legacy Assessment, Reporting, Lifecycle,
  Administration, and AnchorOS adapter behavior.
- Existing S.P.A.T.I.A.L. engine source and eight-test suite.
- Existing records, revisions, audit history, evidence files, and runtime data.

## Explicitly deferred

- Executive Opportunity Dossier generation (`ED-*`).
- Additional Knowledge Modules.
- Internet research, external AI/LLM execution, and evidence creation during
  assessment.
- Engine methodology changes.
- Production authentication, authorization, encryption, tenancy, availability,
  and tamper-evident audit controls.

## Verified reference output

With the bundled bounded reference records, `AS-000001` returns:

```text
Recommendation: Hold
Score: 33.2/100
Engine evidence confidence: Low
Risk profile: High
```

This output follows the conservative adapter mapping and current persisted
reference evidence. It is not an official Florida Power & Light assessment,
endorsement, finding, or independently verified conclusion.
