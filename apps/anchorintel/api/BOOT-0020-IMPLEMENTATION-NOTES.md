# BOOT-0020 AnchorIntel Implementation Notes

## Sprint progression

| Sprint | Working capability |
|---|---|
| 1 | OI-000001 Opportunity Service, SQLite persistence, browser workspace, edit, archive |
| 2 | EV-000001 Evidence Service, file hashing/storage, revisions, archive, lifecycle |
| 3 | AKM-GEO-FL-001 Knowledge Module and generated KR-000001 Knowledge Review |

## Sprint 3 architecture delta

BOOT-0020 now demonstrates a working persisted sequence:

```text
Opportunity record
→ active evidence trace
→ versioned Knowledge Module
→ deterministic Knowledge Review
→ current/stale lifecycle determination
```

The review output is replay-identifiable and preserves its inputs without
claiming immutable audit, independent verification, or source truth. A review
continues to satisfy the lifecycle only while its opportunity, evidence, and
module conditions remain current.

## Verification evidence

- AnchorIntel API tests: 22 passing.
- Existing S.P.A.T.I.A.L. engine tests: 8 passing.
- Reference output: `KR-000001`, Completed, Moderate confidence.
- Extracted-package verification: recorded in `VERIFICATION.md` and the package
  manifest after final assembly.

## Known limitations and future work

- only one local Knowledge Module executor is installed;
- no live research, current-data acquisition, or external AI execution;
- no new S.P.A.T.I.A.L. assessment integration in Sprint 3;
- no Executive Opportunity Dossier;
- no authentication, authorization, multi-tenant isolation, or tamper-evident
  audit storage;
- no legal, regulatory, engineering, environmental, financial, procurement, or
  investment determination.

The next bounded milestone is Knowledge Module output integration into a future
S.P.A.T.I.A.L. assessment input contract, not an expansion of Sprint 3.
