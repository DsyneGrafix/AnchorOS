# Verification Record — AnchorIntel API v0.3.0 Sprint 3

Verification date: 2026-07-19

## AnchorIntel API suite

Run from `apps/anchorintel/api`:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v
```

The 22 tests use temporary databases, file stores, module directories, and
loopback HTTP servers. They cover:

1. all retained Sprint 1 opportunity behavior;
2. all retained Sprint 2 evidence, file, revision, archive, lifecycle, and
   migration behavior;
3. health and OpenAPI v0.3.0 discovery;
4. module list/retrieve and browser views;
5. required module fields and integrity-hash rejection;
6. unknown module and missing opportunity rejection;
7. deterministic review output and hashes;
8. active-only evidence consumption and archived-evidence exclusion;
9. exact evidence revision/hash/status/confidence traceability;
10. review persistence after repository restart;
11. draft completion and lifecycle eligibility;
12. failed-executor persistence and failure audit;
13. opportunity-revision staleness;
14. evidence-revision and archive staleness;
15. rerun/supersession with prior review preservation;
16. module load, review start/complete/fail/supersede/rerun/stale audit events;
17. generated OI-000001/EV-000001/KR-000001 reference workflow and bounded
    disclaimers;
18. Knowledge Module run/detail and evidence-trace UI; and
19. existing assessment, report, revalidation, queue, evidence-promotion, and
    AnchorOS adapter regressions.

Observed source-tree result:

```text
Ran 22 tests in 12.297s

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

## Static checks

```bash
python3 -m py_compile anchorintel_api/*.py tests/test_api.py
bash -n start-anchorintel.sh
```

## Extracted-package verification

The final ZIP is extracted into an isolated temporary AnchorOS-shaped tree. The
unchanged sibling engine is linked only for test resolution. The API suite,
engine suite, Python compilation, launcher syntax check, manifest hash check,
reference seed smoke test, and exclusion scan are rerun against the extracted
files. Final observed timings and ZIP digest are recorded in
`SPRINT3-PACKAGE-MANIFEST.txt`.

## Scope of evidence

These checks demonstrate the bundled contracts in the tested Python runtime.
They do not establish production security, concurrent multi-process safety,
high availability, load capacity, authenticated AnchorOS registry integration,
evidence truth, current Florida conditions, independent verification,
cryptographic immutability, or tamper-evident audit storage.
