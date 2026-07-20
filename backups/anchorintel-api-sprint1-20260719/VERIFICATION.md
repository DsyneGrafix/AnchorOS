# Verification Record — AnchorIntel API v0.1.0 + OI-000001 Sprint 1

Verification date: 2026-07-19

## Automated API checks

Run from the AnchorOS `api` directory:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python -m unittest discover -s tests -v
```

The nine transport-level tests start the real HTTP server on an ephemeral loopback port and verify:

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
11. idempotent creation of `OI-000001` with the canonical FPL profile;
12. Opportunity List, Detail, Edit, and Archive browser flows against the real
    SQLite repository; and
13. preservation of the archived reference record through the API collection.

Observed result on 2026-07-19:

```text
Ran 9 tests in 5.312s

OK
```

The bundled `data/anchorintel.db` was also queried directly after bootstrap.
It contains one active `OI-000001` record at revision 1 and one corresponding
`opportunity.created` audit event.

The path-safe `apps/anchorintel/api/start-anchorintel.sh` launcher was
syntax-checked and started from the AnchorOS root. It resolved the sibling
engine and existing database without relying on the shell's current directory.

## Engine regression checks

Run from `spatial-opportunity-engine`:

```bash
python -m unittest discover -s tests -v
```

The eight engine tests verify scoring, evidence confidence, provisional downgrades, gate and fatal-constraint precedence, input/reference validation, lifecycle gating, deterministic JSON, and report traceability.

## Scope of evidence

Passing checks demonstrate deterministic behavior for the tested contracts in the bundled Python runtime. They do not establish production security, multi-node concurrency, high availability, load capacity, external identity integration, AnchorOS registry compatibility, or the truth of opportunity evidence.
