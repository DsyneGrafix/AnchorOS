# Verification Record — AnchorIntel API v0.6.0 Sprint 6

Verification date: 2026-07-20

## AnchorIntel API suite

Run from `apps/anchorintel/api`:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v
```

Observed source-tree result:

```text
Ran 40 tests in 19.191s

OK
```

The 40 tests retain all 32 Sprint 1–5 checks and add eight Sprint 6 scenarios:

1. exact `OI → EV → KR-000002 → AS → ED → AR` closure and source preservation;
2. incomplete lifecycle rejection;
3. stale opportunity and evidence rejection;
4. stale review, assessment, and dossier rejection;
5. byte-identical pure package construction;
6. restart persistence and replay;
7. duplicate prevention and tamper detection; and
8. API/UI create, detail, download, replay, and audit behavior.

The existing migration test also confirms `archives` is added to a legacy
database without loss of opportunity, evidence, or assessment rows.

## Existing S.P.A.T.I.A.L. engine suite

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s ../spatial-opportunity-engine/tests -v
```

Observed result: eight tests, `OK`. The unchanged suite covers scoring, evidence
confidence, provisional downgrades, gate/fatal precedence, validation, lifecycle
gating, deterministic JSON, and report traceability.

## Static and package checks

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m compileall -q anchorintel_api tests
bash -n start-anchorintel.sh
python3 -m json.tool anchoros-service.json >/dev/null
```

Archive-specific tests verify the exact 10-member set, manifest equality,
per-member hashes/sizes, final package hash, safe names, record IDs, revisions,
module hash, assessment/dossier replay hashes, and persisted provenance.

## BOOT-0020 smoke check

The controlled fixture produces:

```text
OI-000001 / revision 1
EV-000001 / revision 1
KR-000002 / Completed
AS-000001 / persisted assessment replay hash
ED-000001 / HTML + PDF + JSON / dossier replay match
AR-000001 / 5 records / 10 files / archive replay PASS
Lifecycle: seven steps complete / opportunity read only
```

Source-tree BOOT fixture archive package SHA-256:

```text
8264d363188231817ffc9c9b33aca73b89b15d09c4c7c4a0aa209fd5f070c99e
```

The fixture replayed `PASS`. Runtime archive hashes are instance-specific and
remain visible on each `AR-*` detail page.

## Extracted-package verification

The final ZIP is extracted into an isolated AnchorOS-shaped tree. The unchanged
sibling engine is copied only for dependency resolution. Both test suites,
compilation, launcher/JSON syntax, source manifest verification, exclusion scan,
reference BOOT archive creation, ZIP/member hashes, and replay are rerun there.
Final results and the source ZIP digest are recorded in the Sprint 6 manifest.

## Scope of evidence

These checks demonstrate the bundled contracts in the tested Python runtime.
They do not establish production security, concurrency safety, HA, load
capacity, authenticated AnchorOS registry integration, source truth, current
Florida conditions, independent verification, cryptographic immutability, or
tamper-evident audit storage.
