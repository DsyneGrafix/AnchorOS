# BOOT-0020 AnchorIntel Implementation Notes

## Sprint progression

| Sprint | Working capability |
|---|---|
| 1 | OI-000001 Opportunity Service, SQLite persistence, browser workspace, edit, archive |
| 2 | EV-000001 Evidence Service, file hashing/storage, revisions, archive, lifecycle |
| 3 | AKM-GEO-FL-001 Knowledge Module and deterministic KR Knowledge Review |
| 4 | AS assessment integration, persisted provenance, staleness, deterministic replay |
| 5 | ED Executive Opportunity Dossier, HTML/PDF/JSON, replay, lifecycle |

## Current BOOT-0020 sequence

```text
Opportunity record
→ active evidence trace
→ versioned Knowledge Module
→ deterministic Knowledge Review
→ persisted S.P.A.T.I.A.L. assessment
→ deterministic Executive Opportunity Dossier
```

Every stage has a durable ID and consumes the persisted output of the previous
stage. The dossier copies assessment semantics exactly. Its hashes demonstrate
reproducibility within the application; they do not claim immutable audit,
source truth, independent verification, or customer endorsement.

## Verification evidence

- AnchorIntel API tests: 32 passing.
- Existing S.P.A.T.I.A.L. engine tests: 8 passing.
- Reference artifact: `ED-000001`, HTML/PDF/JSON, replay match.
- Alternate provenance test: `OI-000001 → EV-000001 → KR-000002 → AS-000001 → ED-000001`.
- Extracted-package results: recorded in `VERIFICATION.md` and the Sprint 5 manifest.

## Known limitations and future work

- Archive Results remains incomplete;
- only one local Knowledge Module executor is installed;
- no live research, current-data acquisition, or external AI execution;
- no authentication, authorization, multi-tenant isolation, or tamper-evident audit;
- no production concurrency, availability, or load qualification; and
- no legal, regulatory, engineering, environmental, financial, procurement, or
  investment determination.

The next bounded milestone is Archive Results or an explicitly approved
operational hardening sprint. Sprint 5 does not silently expand into either.
