# BOOT-0020 AnchorIntel Implementation Notes

## Sprint progression

| Sprint | Working capability |
|---|---|
| 1 | `OI-000001` Opportunity Service, persistence, workspace, edit, record archive |
| 2 | `EV-000001` Evidence Service, external file storage/hash, revisions, lifecycle |
| 3 | `AKM-GEO-FL-001` and deterministic `KR-*` Knowledge Review |
| 4 | `AS-*` S.P.A.T.I.A.L. integration, provenance, staleness, replay |
| 5 | `ED-*` Executive Dossier, HTML/PDF/JSON, replay, lifecycle |
| 6 | `AR-*` deterministic archive, manifest/package hashes, replay, read-only closure |

## Completed BOOT-0020 sequence

```text
OI-000001
→ EV-000001
→ KR-000002
→ AS-000001
→ ED-000001
→ AR-000001
```

Every stage has a durable ID and consumes persisted output from the prior stage.
Archive creation packages current records and existing dossier outputs. It does
not run research, an external model, a Knowledge Module, or S.P.A.T.I.A.L.

Fresh reference seeding stops at `ED-000001` and may naturally use `KR-000001`.
The BOOT provenance test explicitly creates and preserves the requested
`KR-000002 → AS-000001 → ED-000001 → AR-000001` chain.

## Verification evidence

- AnchorIntel API tests: 40 passing.
- Existing S.P.A.T.I.A.L. engine tests: eight passing.
- Reference archive: `AR-000001`, 10 files, package hash verified.
- Archive replay: `PASS` after restart.
- Tamper test: changed package bytes produce `FAIL` and audit event.
- Lifecycle: all seven steps complete and opportunity read only.
- Source preservation: opportunity, evidence, review, assessment, and dossier rows remain.

## Operational boundaries

- archive packages live on the local filesystem and must be backed up with SQLite;
- no restore/reopen workflow is implemented;
- hashes are reproducibility/integrity comparisons, not signatures or immutable proof;
- only one local Knowledge Module executor is installed;
- no live research, external AI, authenticated tenancy, HA, or load qualification; and
- no legal, regulatory, engineering, environmental, financial, procurement, or
  investment determination is made.

`boot-0020` is the recommended human-approved Git tag after package review. The
application does not create or publish it.
