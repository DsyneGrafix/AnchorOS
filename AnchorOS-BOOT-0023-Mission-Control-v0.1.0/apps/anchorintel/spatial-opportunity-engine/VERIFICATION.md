# S.P.A.T.I.A.L. Engine Verification Record

**Engine:** 0.1.0  
**Methodology:** SIO-001 v0.1  
**Verification date:** 18 July 2026  
**Status:** PASS for the bounded tests below

## Verification scope

The verification checks that the reference implementation:

1. calculates the published weighted score deterministically;
2. separates evidence confidence from opportunity score;
3. downgrades high-scoring opportunities when evidence remains weak;
4. prevents a failed gate from being overridden by a high score;
5. applies fatal Hold and Reject constraints before score bands;
6. rejects references to evidence that does not exist;
7. requires lifecycle ownership, next action, resource ceiling, and a future review date;
8. renders evidence-linked Markdown and JSON decision records;
9. preserves the engine's non-certification boundary.

## Commands

```bash
python -m compileall -q spatial_engine tests
python -m unittest discover -s tests -v
python -m spatial_engine examples/rural_broadband.json \
  --json-out output/SIO-2026-001-result.json \
  --md-out output/SIO-2026-001-decision.md
python -m json.tool output/SIO-2026-001-result.json >/dev/null
```

## Expected example result

| Field | Expected |
|---|---|
| Opportunity | SIO-2026-001 |
| Score | 62.50/100 |
| Evidence confidence | Moderate |
| Recommendation | Monitor — Provisional |
| Lifecycle gate | Pass |
| Fatal constraints | None |

The example is fictional. The result verifies engine behavior, not a real infrastructure opportunity.

## Limitations

- The test suite is bounded and does not establish production assurance.
- Scoring thresholds have not yet been calibrated against real completed opportunities.
- Cross-reviewer scoring consistency has not yet been measured.
- Source authenticity is supplied to, not certified by, the engine.
- Engineering, legal, financial, regulatory, safety, cybersecurity, procurement, and funding conclusions remain outside scope.

## Next verification step

Run SIO-001's initial verification plan against at least three representative opportunity classes, retain the complete decision records, compare reviewer scoring variance, and use the results to propose Version 0.2 threshold or worksheet corrections.
