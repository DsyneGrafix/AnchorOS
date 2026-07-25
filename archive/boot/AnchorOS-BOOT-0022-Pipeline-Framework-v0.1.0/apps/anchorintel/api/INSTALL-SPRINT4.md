# AnchorIntel Sprint 4 — Safe Installation and Sprint 3 Restoration

Do not extract the ZIP directly over the working application. Stage it, stop
AnchorIntel, back up Sprint 3 source and all runtime data, inspect the package,
run isolated tests, and only then install the source overlay.

## Package boundary

The ZIP is rooted at `apps/anchorintel/api`. It contains a complete API source
snapshot and excludes SQLite DB/WAL/SHM files, uploaded evidence, backups,
failed-install directories, caches, customer data, and the unchanged sibling
`spatial-opportunity-engine`.

## 1. Stop AnchorIntel

Press `Ctrl+C` in the terminal running AnchorIntel. Do not copy SQLite while the
service is accepting writes.

## 2. Stage and inspect

```bash
mkdir -p "/home/ricky/Desktop/anchorintel-sprint4-staging"
unzip -q "/home/ricky/Downloads/AnchorIntel-OI-000001-Sprint4.zip" \
  -d "/home/ricky/Desktop/anchorintel-sprint4-staging"

find "/home/ricky/Desktop/anchorintel-sprint4-staging/apps/anchorintel/api" \
  -type f | sort
```

Confirm there is no `.db`, `.db-wal`, `.db-shm`, uploaded evidence, backup,
`*-failed`, or Python cache content.

## 3. Back up Sprint 3 before migration

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
mkdir -p "backups/anchorintel-api-sprint3-20260720"
cp -a "apps/anchorintel/api/." \
  "backups/anchorintel-api-sprint3-20260720/"
```

Verify that the backup includes the database and file store:

```bash
ls -lh "backups/anchorintel-api-sprint3-20260720/data/anchorintel.db"
find "backups/anchorintel-api-sprint3-20260720/data/evidence-files" \
  -maxdepth 1 -type f -print
```

If SQLite uses WAL mode, the stopped-service directory copy also preserves any
`.db-wal` and `.db-shm` files that exist.

## 4. Verify staged source before installation

```bash
mkdir -p "/home/ricky/Desktop/anchorintel-sprint4-verification/apps/anchorintel"
cp -a "/home/ricky/Desktop/anchorintel-sprint4-staging/apps/anchorintel/api" \
  "/home/ricky/Desktop/anchorintel-sprint4-verification/apps/anchorintel/"
cp -a "apps/anchorintel/spatial-opportunity-engine" \
  "/home/ricky/Desktop/anchorintel-sprint4-verification/apps/anchorintel/"

cd "/home/ricky/Desktop/anchorintel-sprint4-verification/apps/anchorintel/api"
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v

cd "../spatial-opportunity-engine"
python3 -m unittest discover -s tests -v
```

Do not continue unless the API reports 27 tests and `OK`, and the engine reports
8 tests and `OK`.

## 5. Install the database-free source overlay

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
cp -a \
  "/home/ricky/Desktop/anchorintel-sprint4-staging/apps/anchorintel/api/." \
  "apps/anchorintel/api/"
chmod +x "apps/anchorintel/api/start-anchorintel.sh"
```

This merge does not delete files and the package does not contain runtime data.

## 6. Start and migrate

```bash
./apps/anchorintel/api/start-anchorintel.sh
```

Open <http://127.0.0.1:8080/opportunities/OI-000001>. Startup initializes the
schema idempotently. It creates `AS-000001` only when no operational reference
assessment exists and the persisted OI/EV/KR chain is current. It does not
overwrite edited, archived, stale, or existing records.

## Database migration

Sprint 4 retains `assessments` and adds missing columns:

```sql
assessment_kind TEXT NOT NULL DEFAULT 'legacy'
knowledge_review_id TEXT
engine_version TEXT NOT NULL DEFAULT ''
adapter_version TEXT NOT NULL DEFAULT ''
replay_hash TEXT NOT NULL DEFAULT ''
provenance_json TEXT NOT NULL DEFAULT '{}'
revision INTEGER NOT NULL DEFAULT 1
updated_at TEXT NOT NULL DEFAULT ''
```

Existing `updated_at` values are initialized from `created_at`. Existing
assessment rows remain `legacy`; they are not converted into operational
assessments. The migration also creates an opportunity/kind/date index. No
table or row is dropped, and evidence bytes remain outside SQLite.

## Exact Sprint 4 source changes

Added:

- `CHANGES-SPRINT4.md`
- `INSTALL-SPRINT4.md`
- `SPRINT4-PACKAGE-MANIFEST.txt`
- `SPRINT4-VERIFICATION-CHECKLIST.md`
- `anchorintel_api/assessment.py`

Changed:

- `ARCHITECTURE.md`
- `README.md`
- `VERIFICATION.md`
- `anchorintel_api/__init__.py`
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

All other packaged files are unchanged source carried forward from Sprint 3.

## Restore Sprint 3 if installation fails

Stop AnchorIntel. Preserve the failed Sprint 4 tree for diagnosis, then restore
the complete pre-migration source/database/file-store backup:

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
mv "apps/anchorintel/api" "apps/anchorintel/api-sprint4-failed"
mkdir -p "apps/anchorintel/api"
cp -a "backups/anchorintel-api-sprint3-20260720/." \
  "apps/anchorintel/api/"
chmod +x "apps/anchorintel/api/start-anchorintel.sh"
./apps/anchorintel/api/start-anchorintel.sh
```

This restores Sprint 3 source, SQLite state, and evidence files together. Do not
point Sprint 3 source at the migrated Sprint 4 database as a substitute for
restoration. Retain the failed tree until diagnosis is complete.
