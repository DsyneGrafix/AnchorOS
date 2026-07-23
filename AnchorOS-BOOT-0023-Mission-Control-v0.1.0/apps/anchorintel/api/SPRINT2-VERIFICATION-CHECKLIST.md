# AnchorIntel Sprint 2 Verification Checklist

## Installation controls

- [ ] Sprint 1 service stopped before backup.
- [ ] Complete `apps/anchorintel/api` backup created.
- [ ] Backup contains `data/anchorintel.db`.
- [ ] Sprint 2 ZIP staged outside the AnchorOS repository.
- [ ] Package manifest reviewed; no database or uploaded evidence in ZIP.
- [ ] API and engine automated suites both end with `OK`.

## OI-000001 and EV-000001

- [ ] Start with `./apps/anchorintel/api/start-anchorintel.sh`.
- [ ] Open <http://127.0.0.1:8080/opportunities/OI-000001>.
- [ ] OI-000001 retains its Sprint 1 fields and edit/archive actions.
- [ ] Evidence section shows EV-000001.
- [ ] EV-000001 title is “Florida Electric Utility Asset Intelligence Context.”
- [ ] Reference notes say it is not an official, supplied, or endorsed Florida Power & Light document.
- [ ] “Attach Evidence” is complete while EV-000001 is active.
- [ ] Knowledge Module Review, Run S.P.A.T.I.A.L., and dossier stages remain incomplete.

## Evidence user workflow

- [ ] “Add Evidence” opens the Add Evidence page.
- [ ] A metadata-only record can be saved and appears in the evidence table.
- [ ] A file-backed record can be saved and is labeled “File attached.”
- [ ] Evidence Detail opens and shows metadata, revision, timestamps, and file integrity fields.
- [ ] Edit Evidence updates metadata and increments the revision.
- [ ] Archive Evidence marks the record archived without deleting it.
- [ ] When every evidence record is archived, “Attach Evidence” returns to pending.
- [ ] Restart the service and confirm evidence records still appear.

## Storage and audit

- [ ] Uploaded file exists under `data/evidence-files` with a generated name.
- [ ] Original filename is present only as metadata.
- [ ] Displayed SHA-256 matches `sha256sum` for the stored file.
- [ ] Path-bearing filenames are rejected.
- [ ] Files above 10 MiB are rejected.
- [ ] `GET /v1/admin/audit` includes create, upload, update, and archive events as applicable.
- [ ] No claim of immutable audit storage or independent evidence verification is displayed.

## API spot checks

```bash
curl -H 'Accept: application/json' \
  http://127.0.0.1:8080/opportunities/OI-000001/evidence

curl -H 'Accept: application/json' \
  http://127.0.0.1:8080/opportunities/OI-000001/evidence/EV-000001

curl http://127.0.0.1:8080/v1/openapi.json
```

Sprint 2 is accepted only after persisted behavior, revisions, audit events,
archive behavior, lifecycle derivation, and restart survival have been checked.

