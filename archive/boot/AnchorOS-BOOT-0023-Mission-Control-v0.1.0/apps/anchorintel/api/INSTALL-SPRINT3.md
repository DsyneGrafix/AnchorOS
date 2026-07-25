# AnchorIntel Sprint 3 — Safe Installation and Sprint 2 Rollback

Do not extract the ZIP directly over the working application. Stage it, stop
AnchorIntel, back up Sprint 2 source and runtime data, inspect the package, run
isolated tests, and only then start against the working database.

## Package boundary

The ZIP is rooted at `apps/anchorintel/api`. It contains a complete API source
snapshot and excludes:

- `data/anchorintel.db`, WAL, and SHM files;
- uploaded evidence under `data/evidence-files/`;
- backup or failed-installation directories;
- Python caches and temporary files;
- customer data; and
- the unchanged sibling `spatial-opportunity-engine`.

## 1. Stop AnchorIntel

In the terminal running AnchorIntel, press `Ctrl+C`. Do not back up SQLite while
the application is accepting writes.

## 2. Stage and inspect the ZIP

```bash
mkdir -p "/home/ricky/Desktop/anchorintel-sprint3-staging"
unzip -q "/home/ricky/Downloads/AnchorIntel-OI-000001-Sprint3.zip" \
  -d "/home/ricky/Desktop/anchorintel-sprint3-staging"

find "/home/ricky/Desktop/anchorintel-sprint3-staging/apps/anchorintel/api" \
  -type f | sort
```

Confirm that the staged tree contains no `.db`, `.db-wal`, `.db-shm`, uploaded
evidence, `backups`, or `*-failed` content.

## 3. Back up the installed Sprint 2 application

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
mkdir -p "backups/anchorintel-api-sprint2-20260719"
cp -a "apps/anchorintel/api/." \
  "backups/anchorintel-api-sprint2-20260719/"
```

Verify the database and file store are present in the backup:

```bash
ls -lh "backups/anchorintel-api-sprint2-20260719/data/anchorintel.db"
find "backups/anchorintel-api-sprint2-20260719/data/evidence-files" \
  -maxdepth 1 -type f -print
```

## 4. Verify the staged source before installation

The staged API expects the sibling engine in the same AnchorOS application
directory. Copy it only into a temporary verification layout:

```bash
mkdir -p "/home/ricky/Desktop/anchorintel-sprint3-verification/apps/anchorintel"
cp -a "/home/ricky/Desktop/anchorintel-sprint3-staging/apps/anchorintel/api" \
  "/home/ricky/Desktop/anchorintel-sprint3-verification/apps/anchorintel/"
cp -a "apps/anchorintel/spatial-opportunity-engine" \
  "/home/ricky/Desktop/anchorintel-sprint3-verification/apps/anchorintel/"

cd "/home/ricky/Desktop/anchorintel-sprint3-verification/apps/anchorintel/api"
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v

cd "../spatial-opportunity-engine"
python3 -m unittest discover -s tests -v
```

Do not continue unless both suites end with `OK`.

## 5. Install the source overlay

The merge does not delete files and the package contains no runtime database:

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
cp -a \
  "/home/ricky/Desktop/anchorintel-sprint3-staging/apps/anchorintel/api/." \
  "apps/anchorintel/api/"
chmod +x "apps/anchorintel/api/start-anchorintel.sh"
```

## 6. Start and migrate

```bash
./apps/anchorintel/api/start-anchorintel.sh
```

Startup runs idempotent schema initialization, loads and checks
`AKM-GEO-FL-001`, and seeds `KR-000001` only when the reference inputs exist and
no prior reference review is present. Open:

<http://127.0.0.1:8080/opportunities/OI-000001>

## Database migration

Sprint 3 adds:

```sql
CREATE TABLE IF NOT EXISTS knowledge_reviews (...);
CREATE INDEX IF NOT EXISTS knowledge_reviews_opportunity_idx
    ON knowledge_reviews(opportunity_id, created_at DESC);
```

The table stores review records and supersession links. Initialization does not
drop, replace, or rewrite existing Sprint 2 tables or rows. Module definitions
remain files; no module JSON is copied into customer evidence storage.

## Exact Sprint 3 source changes

Added:

- `AKM-GEO-FL-001.md`
- `BOOT-0020-IMPLEMENTATION-NOTES.md`
- `CHANGES-SPRINT3.md`
- `INSTALL-SPRINT3.md`
- `KNOWLEDGE-MODULE-FORMAT.md`
- `SPRINT3-PACKAGE-MANIFEST.txt`
- `SPRINT3-VERIFICATION-CHECKLIST.md`
- `anchorintel_api/knowledge.py`
- `anchorintel_api/knowledge_modules/AKM-GEO-FL-001.json`

Changed:

- `.gitignore`
- `ARCHITECTURE.md`
- `INSTALL-OI-000001.md`
- `README.md`
- `VERIFICATION.md`
- `anchorintel_api/anchoros.py`
- `anchorintel_api/app.py`
- `anchorintel_api/openapi.py`
- `anchorintel_api/reference.py`
- `anchorintel_api/repository.py`
- `anchorintel_api/server.py`
- `anchorintel_api/service.py`
- `anchorintel_api/web.py`
- `anchoros-service.json`
- `pyproject.toml`
- `tests/test_api.py`

All other packaged files are unchanged source carried forward from Sprint 2.

## Restore Sprint 2 if installation fails

Stop AnchorIntel. Preserve the failed Sprint 3 state for diagnosis, then restore
the full source/database/file-store backup:

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
mv "apps/anchorintel/api" "apps/anchorintel/api-sprint3-failed"
mkdir -p "apps/anchorintel/api"
cp -a "backups/anchorintel-api-sprint2-20260719/." \
  "apps/anchorintel/api/"
chmod +x "apps/anchorintel/api/start-anchorintel.sh"
./apps/anchorintel/api/start-anchorintel.sh
```

This restores the pre-migration database and evidence files. Do not reuse the
migrated Sprint 3 database with Sprint 2 code as a substitute for rollback. The
moved failed directory is recoverable and should be retained until diagnosis is
complete.
