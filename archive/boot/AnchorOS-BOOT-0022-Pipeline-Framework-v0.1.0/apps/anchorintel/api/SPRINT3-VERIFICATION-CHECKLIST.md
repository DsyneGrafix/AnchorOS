# Sprint 3 Verification Checklist

Use this checklist after staging and again after installation.

## Package safety

- [ ] ZIP SHA-256 matches the supplied digest.
- [ ] `SPRINT3-PACKAGE-MANIFEST.txt` hashes match extracted files.
- [ ] No SQLite database, WAL/SHM file, uploaded evidence, backup, cache, or
      customer data is present.
- [ ] `api` and `spatial-opportunity-engine` are siblings.
- [ ] Sprint 2 source, database, and evidence-file store are backed up.

## Automated verification

- [ ] API suite reports 22 tests and `OK`.
- [ ] Existing S.P.A.T.I.A.L. engine suite reports 8 tests and `OK`.
- [ ] `python3 -m py_compile anchorintel_api/*.py` succeeds.
- [ ] `bash -n start-anchorintel.sh` succeeds.

## Reference workflow

- [ ] `OI-000001` opens and retains `EV-000001`.
- [ ] `AKM-GEO-FL-001` appears in the module library with version 1.0 and Active
      status.
- [ ] `KR-000001` is generated from persisted inputs, not inserted as a fixed
      output object.
- [ ] The review reports Moderate confidence for the bounded reference input.
- [ ] Findings, assumptions, unknowns, risks, and missing evidence are visible.
- [ ] Evidence trace contains `EV-000001` and its current revision.
- [ ] Input, output, and module hashes are visible.
- [ ] The reference notice disclaims official FPL origin, endorsement,
      procurement intent, ownership, service territory, funding, and approval.

## Lifecycle and staleness

- [ ] Attach Evidence is complete with active `EV-000001`.
- [ ] Knowledge Module Review is complete with a current completed review.
- [ ] S.P.A.T.I.A.L. and dossier stages remain pending.
- [ ] Editing the opportunity makes the prior review stale and Knowledge Module
      Review pending.
- [ ] Editing or archiving consumed evidence makes the prior review stale.
- [ ] Rerun creates a new review and preserves/supersedes the prior record.
- [ ] Draft, incomplete, failed, superseded, and stale reviews do not complete
      the lifecycle.

## Audit and restart

- [ ] Audit includes module load, review start, and completion.
- [ ] Rerun includes superseded and rerun events.
- [ ] First stale detection is recorded without claiming immutable storage.
- [ ] Service restart preserves the review and trace.
