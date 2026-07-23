# S.P.A.T.I.A.L. Infrastructure Opportunity Intelligence Engine

Version 0.1.0 is the executable reference implementation of **SIO-001 — S.P.A.T.I.A.L. Infrastructure Opportunity Intelligence Methodology**.

It evaluates one infrastructure opportunity at a time and produces a traceable recommendation:

- **Pursue**
- **Validate**
- **Monitor**
- **Hold**
- **Reject**

The engine preserves the method's core controls:

- separate verified facts, supported inferences, assumptions, unknowns, and disputes;
- calculate the published eight-dimension, 100-point score;
- require every S.P.A.T.I.A.L. gate to pass or remain visibly provisional;
- prevent a high score from overriding a failed gate or fatal constraint;
- downgrade high-scoring cases when evidence confidence is insufficient;
- require an owner, bounded next action, resource ceiling, and review date;
- produce reproducible JSON and human-readable Markdown decision records.

## Requirements

- Python 3.10 or newer
- No third-party runtime packages

## Quick start

From this directory:

```bash
python -m spatial_engine examples/rural_broadband.json
```

Create both report formats:

```bash
python -m spatial_engine examples/rural_broadband.json \
  --json-out output/SIO-2026-001-result.json \
  --md-out output/SIO-2026-001-decision.md
```

Print a complete result:

```bash
python -m spatial_engine examples/rural_broadband.json --format json
python -m spatial_engine examples/rural_broadband.json --format markdown
```

Optional editable installation:

```bash
python -m pip install -e .
spatial-engine examples/rural_broadband.json
```

## Opportunity record

Use [`examples/rural_broadband.json`](examples/rural_broadband.json) as the controlled input template. The example is explicitly fictional.

Required top-level sections:

| Section | Purpose |
|---|---|
| Opportunity metadata | Bounds the case, geography, class, problem, analyst, and assessment date |
| `evidence` | Records evidence state, claim, source, dates, geography, materiality, and limitations |
| `dimensions` | Supplies 0–5 scores, rationales, and evidence references for all eight weighted dimensions |
| `gates` | Records S, P, A1, T, I, and A2 status; L is calculated from lifecycle controls |
| `fatal_constraints` | Applies explicit Hold or Reject overrides |
| `known_limitations` | Keeps incomplete or excluded work visible |
| `lifecycle` | Defines owner, next action, resource ceiling, review date, and revalidation triggers |

### Evidence states

- `V` — Verified fact
- `S` — Supported inference
- `A` — Assumption
- `U` — Unknown
- `D` — Disputed

### Gate states

- `pass`
- `provisional`
- `fail`

The two A stages use distinct machine identifiers:

- `A1` — Assets, Actors & Authority
- `A2` — Alignment & Advantage

The engine derives `L` — Lifecycle Decision & Learning — from the lifecycle fields.

## Deterministic recommendation rules

The following precedence applies:

1. Fatal Reject constraint → **Reject**.
2. Fatal Hold constraint → **Hold**.
3. Any failed mandatory gate → **Hold**.
4. Score 80–100 with High confidence and all gates passed → **Pursue**.
5. Score 80–100 with weaker confidence or a provisional gate → **Validate**.
6. Score 65–79 → **Validate**.
7. Score 45–64 → **Monitor**.
8. Score 25–44 → **Hold**.
9. Score 0–24 → **Reject**.

This conservative rule set intentionally chooses one deterministic default from SIO-001's broader decision bands. A human reviewer may approve a different controlled decision, but the override should be documented outside the engine result with its reason and authority.

## Verification

Run the automated test suite:

```bash
python -m unittest discover -s tests -v
```

The suite verifies score calculation, confidence downgrades, gate overrides, fatal constraints, reference integrity, lifecycle control, and report traceability.

## Boundaries

This engine is an opportunity-intelligence tool. It does not certify source truth, engineering design, cybersecurity, safety, legal compliance, funding eligibility, procurement status, financial returns, or commercial success.

AnchorStack remains separate: it determines continuation validity for execution under current conditions. This engine may produce or consume controlled opportunity records, but it does not extend AnchorStack's proof surface or assign AnchorStack responsibility for engineering, market, or funding validation.

