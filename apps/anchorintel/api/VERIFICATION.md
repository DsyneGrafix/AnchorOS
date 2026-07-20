# Verification Record — AnchorIntel API v0.4.0 Sprint 4

Verification date: 2026-07-20

## AnchorIntel API suite

Run from `apps/anchorintel/api`:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v
```

The 27 tests use temporary databases, file stores, module directories, and
loopback HTTP servers. They cover all retained Sprint 1–3 tests plus:

1. OpenAPI v0.4.0 assessment and replay discovery;
2. generated `OI-000001 → EV-000001 → KR-000001 → AS-000001` provenance;
3. readiness and bounded-execution UI;
4. persisted recommendation, score, confidence, risk, gates, assumptions,
   explanation, evidence trace, versions, and replay hash;
5. deterministic results and hashes for identical inputs;
6. exact stored-snapshot replay;
7. stale opportunity revision rejection;
8. stale evidence trace rejection;
9. superseded Knowledge Review rejection;
10. assessment staleness and lifecycle reversal;
11. assessment persistence and replay after repository restart; and
12. assessment completion/replay/stale audit behavior.

Observed source-tree result:

```text
Ran 27 tests in 14.998s

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

## Reference seed smoke check

A fresh temporary SQLite database is seeded through the public bootstrap. The
check requires these generated records and behavior:

```text
OI-000001 / revision 1
EV-000001 / revision 1
KR-000001 / Completed / Moderate
AS-000001 / Hold / 33.2 / Low / replay match true
Run S.P.A.T.I.A.L. lifecycle complete
Executive Opportunity Dossier pending
```

## Extracted-package verification

The final ZIP is extracted into an isolated AnchorOS-shaped tree. The unchanged
sibling engine is copied only for dependency resolution. The API suite, engine
suite, Python compilation, launcher syntax, manifest hash verification,
reference seed/replay smoke check, and exclusion scan are rerun against the
extracted package. Final timings and ZIP digest are recorded in the Sprint 4
manifest and delivery message.

## Scope of evidence

These checks demonstrate the bundled contracts in the tested Python runtime.
They do not establish production security, concurrent multi-process safety,
high availability, load capacity, authenticated AnchorOS registry integration,
source truth, current Florida conditions, independent verification,
cryptographic immutability, or tamper-evident audit storage.
