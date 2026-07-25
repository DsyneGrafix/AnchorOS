# Sprint 6 Verification Checklist

## Before installation

- [ ] Stop AnchorIntel before copying SQLite or runtime files.
- [ ] Back up the complete Sprint 5 source, DB/WAL/SHM, evidence store, and any
      existing archive directory.
- [ ] Extract the Sprint 6 ZIP into a separate staging directory.
- [ ] Verify the distributed ZIP SHA-256.
- [ ] Confirm the package contains no `.db`, WAL/SHM, uploaded evidence, runtime
      archive ZIP, backup, cache, `tmp`, or customer data.
- [ ] Run 40 API tests and eight engine tests in an isolated AnchorOS-shaped tree.

## Migration

- [ ] Confirm `archives` is created without data loss.
- [ ] Confirm the opportunity index and current-archive unique index exist.
- [ ] Confirm `data/archives/` exists and is excluded from Git.
- [ ] Confirm OI/EV/KR/AS/ED rows and revisions are unchanged after startup.

## Manual BOOT-0020 verification

- [ ] Open `OI-000001` and confirm the current chain is complete through dossier.
- [ ] Open **Archive Results** and review readiness/warnings.
- [ ] Create the archive and confirm `AR-000001` appears.
- [ ] Confirm the lifecycle shows seven completed steps.
- [ ] Confirm the archived opportunity displays a read-only banner.
- [ ] Confirm normal opportunity/evidence edit actions are unavailable.
- [ ] Open evidence, Knowledge Review, assessment, and dossier read-only views.
- [ ] Download `AR-000001.zip`.
- [ ] Confirm the ZIP contains exactly the 10 documented members.
- [ ] Replay the archive and confirm `PASS`.
- [ ] Confirm package and per-file hashes match.
- [ ] Confirm upstream records and uploaded evidence still exist.
- [ ] Confirm audit contains prepared, completed, downloaded, and replayed events.

## Negative checks

- [ ] Incomplete lifecycle returns `archive_not_ready`.
- [ ] Stale opportunity/evidence/review/assessment/dossier is rejected.
- [ ] Duplicate current archive returns `archive_already_exists`.
- [ ] Modified archive bytes replay `FAIL` without silent repair.
- [ ] Missing archive package replay returns `FAIL`.

## Rollback

- [ ] Stop AnchorIntel.
- [ ] Preserve the failed Sprint 6 tree for diagnosis.
- [ ] Restore the complete Sprint 5 source/database/evidence/archive backup.
- [ ] Start Sprint 5 and rerun its verification before discarding the backup.
