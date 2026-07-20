# Verification Record — AnchorIntel API v0.5.0 Sprint 5

Verification date: 2026-07-20

## AnchorIntel API suite

Run from `apps/anchorintel/api`:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v
```

The 32 tests use temporary databases, evidence stores, module directories, and
loopback HTTP servers. They retain all Sprint 1–4 coverage and add:

1. OpenAPI v0.5.0 dossier and export discovery;
2. `ED-000001` reference seeding and idempotency;
3. exact `KR-000002 → AS-000001 → ED-000001` provenance preservation;
4. readiness and bounded-generation UI;
5. persisted executive, opportunity, evidence, review, and assessment summaries;
6. exact assessment recommendation, gates, score, confidence, risk, explanation;
7. deterministic JSON, HTML, PDF, input hash, and replay hash;
8. download content types and filenames;
9. replay comparison for every stored artifact;
10. staleness reversal of the dossier lifecycle step;
11. replayability of stale stored snapshots;
12. restart persistence; and
13. safe additive migration of an existing database.

Observed source-tree result:

```text
Ran 32 tests in 17.960s

OK
```

## Existing S.P.A.T.I.A.L. engine suite

Run from `apps/anchorintel/spatial-opportunity-engine`:

```bash
python3 -m unittest discover -s tests -v
```

The unchanged eight tests cover scoring, evidence confidence, provisional
downgrades, gate/fatal-constraint precedence, input/reference validation,
lifecycle gating, deterministic JSON, and report traceability.

## Static and PDF checks

```bash
python3 -m py_compile anchorintel_api/*.py tests/test_api.py
bash -n start-anchorintel.sh
pdfinfo ED-000001.pdf
pdftotext ED-000001.pdf -
pdftoppm -png ED-000001.pdf ED-000001
```

Poppler accepted the generated PDF 1.4 file as an unencrypted, three-page,
letter-size document. Text extraction and visual page renders contained the full
trace, replay data, bounded-use footer, page numbering, and no clipping or
overlap.

## Reference seed smoke check

A fresh temporary SQLite database must produce:

```text
OI-000001 / revision 1
EV-000001 / revision 1
KR-000001 / Completed / Moderate
AS-000001 / Hold / 33.2 / Low / assessment replay match true
ED-000001 / HTML + PDF + JSON / dossier replay match true
Generate Executive Opportunity Dossier lifecycle complete
Archive Results pending
```

## Extracted-package verification

The final ZIP is extracted into an isolated AnchorOS-shaped tree. The unchanged
sibling engine is copied only for dependency resolution. Both test suites,
Python compilation, launcher syntax, reference seed/replay, PDF validation,
manifest verification, and exclusion scans are rerun there. Final timings and
the ZIP digest are recorded in the Sprint 5 package manifest.

## Scope of evidence

These checks demonstrate the bundled contracts in the tested Python runtime.
They do not establish production security, multi-process concurrency safety,
high availability, load capacity, authenticated AnchorOS registry integration,
source truth, current Florida conditions, independent verification,
cryptographic immutability, or tamper-evident audit storage.
