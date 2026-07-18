# Verification Record — AnchorIntel API v0.1.0

Release date: 2026-07-18

## Automated API checks

Run from `anchorintel-api`:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python -m unittest discover -s tests -v
```

The eight transport-level tests start the real HTTP server on an ephemeral loopback port and verify:

1. health and OpenAPI discovery;
2. opportunity and evidence ingestion followed by assessment execution;
3. JSON and Markdown reports generated from the stored assessment;
4. Hold and due-review lifecycle queues;
5. controlled Assumption → Supported → Verified promotion and blocked PATCH bypass;
6. revision-conflict signaling with `If-Match`;
7. incomplete-draft rejection at the assessment boundary;
8. revalidation linked to the superseded assessment;
9. recoverable opportunity archiving and audit visibility; and
10. AnchorOS adapter registration, startup, health, and shutdown.

## Engine regression checks

Run from `spatial-opportunity-engine`:

```bash
python -m unittest discover -s tests -v
```

The eight engine tests verify scoring, evidence confidence, provisional downgrades, gate and fatal-constraint precedence, input/reference validation, lifecycle gating, deterministic JSON, and report traceability.

## Scope of evidence

Passing checks demonstrate deterministic behavior for the tested contracts in the bundled Python runtime. They do not establish production security, multi-node concurrency, high availability, load capacity, external identity integration, AnchorOS registry compatibility, or the truth of opportunity evidence.
