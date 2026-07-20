# Verification Record — AnchorIntel API v0.2.0 Evidence Service Sprint 2

Verification date: 2026-07-19

## Automated API checks

Run from the AnchorOS `api` directory:

```bash
PYTHONPATH="../spatial-opportunity-engine:." \
  python -m unittest discover -s tests -v
```

The 15 automated tests include real HTTP transport tests on an ephemeral
loopback port plus direct migration and restart-persistence checks. They verify:

1. health and OpenAPI discovery;
2. Sprint 1 Opportunity List, Detail, Edit, Archive, SQLite revision, and audit behavior;
3. idempotent OI-000001 and EV-000001 reference seeding;
4. metadata-only evidence creation;
5. Add, Detail, and Edit Evidence page rendering;
6. opportunity-scoped evidence listing and retrieval;
7. metadata update and revision increment;
8. recoverable evidence archive and audit visibility;
9. lifecycle completion with active evidence and return to pending after archive;
10. multipart file upload, safe generated storage name, and external storage;
11. SHA-256 calculation and file download;
12. missing-opportunity, invalid type/status, unsafe filename, and oversize-file rejection;
13. additive Sprint 1 schema migration without legacy-row loss;
14. evidence persistence after repository shutdown and restart;
15. inherited assessment, report, lifecycle queue, revalidation, and controlled A → S → V behavior; and
16. AnchorOS adapter registration, startup, health, and shutdown.

Observed result on 2026-07-19:

```text
Ran 15 tests in 8.687s

OK
```

The Sprint 2 overlay does not contain `data/anchorintel.db` or customer-uploaded
files. Tests create isolated temporary databases and file stores. The release
launcher is syntax-checked separately and resolves the sibling engine without
depending on the caller's working directory.

A copy of the actual Sprint 1 packaged database was then started through the
Sprint 2 CLI. Startup reported the existing OI-000001, created EV-000001,
bound the HTTP service, and a fresh repository process read the migrated data
as `OI-000001 EV-000001 complete 1`. The original Sprint 1 database was not
modified during this check.

## Engine regression checks

Run from `spatial-opportunity-engine`:

```bash
python -m unittest discover -s tests -v
```

The eight unchanged engine tests verify scoring, evidence confidence,
provisional downgrades, gate and fatal-constraint precedence, input/reference
validation, lifecycle gating, deterministic JSON, and report traceability.

## Scope of evidence

Passing checks demonstrate behavior for the tested contracts in the bundled
Python runtime. They do not establish production security, multi-node
concurrency, high availability, load capacity, external identity integration,
AnchorOS registry compatibility, evidence truth, independent verification,
cryptographic immutability, or tamper-evident audit storage.
