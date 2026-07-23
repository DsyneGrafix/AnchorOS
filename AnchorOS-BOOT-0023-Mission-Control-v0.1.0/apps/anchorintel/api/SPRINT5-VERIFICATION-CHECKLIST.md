# Sprint 5 Verification Checklist

## Before installation

- [ ] AnchorIntel is stopped.
- [ ] Sprint 4 API source, SQLite DB/WAL/SHM, and evidence files are backed up.
- [ ] ZIP is staged outside the live application.
- [ ] Package contains no runtime database, uploaded evidence, cache, or temp PDF.
- [ ] Staged API suite reports 32 tests and `OK`.
- [ ] Existing engine suite reports 8 tests and `OK`.

## Migration and startup

- [ ] `executive_dossiers` is created without data loss.
- [ ] Existing OI, EV, KR, AS, audit, and lifecycle records remain readable.
- [ ] Startup reports `ED-000001` created or already present when inputs are current.
- [ ] `/health` reports version `0.5.0`.
- [ ] `/v1/openapi.json` includes dossier collection, detail, replay, and export paths.

## Reference workflow

- [ ] OI-000001 opens.
- [ ] Evidence, Knowledge Review, and Assessment remain current.
- [ ] Generate Executive Dossier readiness states that it uses persisted local records only.
- [ ] ED-000001 opens inside AnchorIntel.
- [ ] Recommendation, score, confidence, risk, gates, and explanation match AS-000001 exactly.
- [ ] Evidence is summarized, not duplicated.
- [ ] Traceability follows the assessment's real KR link.
- [ ] Footer contains all five bounded-use statements.
- [ ] Generate Executive Opportunity Dossier is complete.
- [ ] Archive Results remains pending.

## Exports and replay

- [ ] HTML downloads and opens as a standalone document.
- [ ] PDF downloads, passes `pdfinfo`, and renders without clipping or overlap.
- [ ] JSON downloads and parses.
- [ ] All exports contain ED-000001 and the provenance chain.
- [ ] Dossier replay reports JSON, HTML, and PDF matches.
- [ ] Repeating generation with identical inputs reuses ED-000001.
- [ ] Dossier persists and replays after restart.
- [ ] A changed upstream record marks the dossier stale and reverses only its lifecycle completion.

## Audit and boundary

- [ ] `dossier.generated` is recorded once for creation.
- [ ] `dossier.replayed` records artifact comparison results.
- [ ] No Knowledge Module or S.P.A.T.I.A.L. execution occurs during dossier replay.
- [ ] No internet, external AI, or evidence generation is involved.
- [ ] Hashes are described as reproducibility checks, not independent verification.

## Rollback

- [ ] Sprint 4 restoration path is understood before migration.
- [ ] Failed Sprint 5 tree will be preserved for diagnosis.
- [ ] Restoration uses the complete Sprint 4 source/database/evidence backup.
