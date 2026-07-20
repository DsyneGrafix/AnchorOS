# Install OI-000001 Sprint 1 — Historical Instructions

These instructions describe the original Sprint 1 package. For the bounded
Sprint 2 Evidence Service overlay, backup, migration, install, verification,
and rollback procedure, use `INSTALL-SPRINT2.md`.

This package is arranged for the current AnchorOS repository layout:

```text
AnchorOS/apps/anchorintel/api
AnchorOS/apps/anchorintel/spatial-opportunity-engine
```

Extract the ZIP into the AnchorOS repository root. The archive updates only
`apps/anchorintel/api`; it does not replace the sibling S.P.A.T.I.A.L. engine.

Then run:

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
chmod +x apps/anchorintel/api/start-anchorintel.sh
./apps/anchorintel/api/start-anchorintel.sh
```

Open <http://127.0.0.1:8080/opportunities>.

The launcher creates `OI-000001` only when it is absent. It never overwrites an
existing or archived record.
