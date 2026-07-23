# AnchorIntel Sprint 5 — Safe Installation and Sprint 4 Restoration

Do not extract the ZIP directly over the working application. Stage it, stop
AnchorIntel, back up Sprint 4 source and all runtime data, inspect the package,
run isolated tests, and only then install the source overlay.

## Package boundary

The ZIP is rooted at `apps/anchorintel/api`. It contains a complete API source
snapshot and excludes SQLite DB/WAL/SHM files, uploaded evidence, backups,
failed-install directories, caches, temporary PDF checks, customer data, and the
unchanged sibling `spatial-opportunity-engine`.

## 1. Stop AnchorIntel

Press `Ctrl+C` in the terminal running AnchorIntel. Do not copy SQLite while the
service is accepting writes.

## 2. Stage and inspect

```bash
mkdir -p "/home/ricky/Desktop/anchorintel-sprint5-staging"
unzip -q "/home/ricky/Downloads/AnchorIntel-OI-000001-Sprint5.zip" \
  -d "/home/ricky/Desktop/anchorintel-sprint5-staging"

find "/home/ricky/Desktop/anchorintel-sprint5-staging/apps/anchorintel/api" \
  -type f | sort
```

Confirm there is no `.db`, `.db-wal`, `.db-shm`, uploaded evidence, backup,
`*-failed`, `tmp`, or Python cache content.

## 3. Back up Sprint 4 before migration

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
mkdir -p "backups/anchorintel-api-sprint4-20260720"
cp -a "apps/anchorintel/api/." \
  "backups/anchorintel-api-sprint4-20260720/"
```

Verify that the backup includes the database and file store:

```bash
ls -lh "backups/anchorintel-api-sprint4-20260720/data/anchorintel.db"
find "backups/anchorintel-api-sprint4-20260720/data/evidence-files" \
  -maxdepth 1 -type f -print
```

The stopped-service copy also preserves SQLite WAL/SHM files if they exist.

## 4. Verify staged source before installation

```bash
mkdir -p "/home/ricky/Desktop/anchorintel-sprint5-verification/apps/anchorintel"
cp -a "/home/ricky/Desktop/anchorintel-sprint5-staging/apps/anchorintel/api" \
  "/home/ricky/Desktop/anchorintel-sprint5-verification/apps/anchorintel/"
cp -a "apps/anchorintel/spatial-opportunity-engine" \
  "/home/ricky/Desktop/anchorintel-sprint5-verification/apps/anchorintel/"

cd "/home/ricky/Desktop/anchorintel-sprint5-verification/apps/anchorintel/api"
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v

cd "../spatial-opportunity-engine"
python3 -m unittest discover -s tests -v
```

Do not continue unless the API reports 32 tests and `OK`, and the engine reports
8 tests and `OK`.

## 5. Install the database-free source overlay

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
cp -a \
  "/home/ricky/Desktop/anchorintel-sprint5-staging/apps/anchorintel/api/." \
  "apps/anchorintel/api/"
chmod +x "apps/anchorintel/api/start-anchorintel.sh"
```

This merge does not delete files and the package contains no runtime data.

## 6. Start and migrate

```bash
./apps/anchorintel/api/start-anchorintel.sh
```

Open <http://127.0.0.1:8080/opportunities/OI-000001>. Startup initializes the
schema idempotently. It creates `ED-000001` only when no dossier exists and the
persisted OI/EV/KR/AS chain is current. It does not overwrite edited, archived,
stale, superseded, or existing records.

## Database migration

Sprint 5 creates one table and index:

```sql
CREATE TABLE executive_dossiers (
  dossier_id TEXT PRIMARY KEY,
  opportunity_id TEXT NOT NULL,
  knowledge_review_id TEXT NOT NULL,
  assessment_id TEXT NOT NULL,
  input_snapshot_json TEXT NOT NULL,
  dossier_json TEXT NOT NULL,
  html_report TEXT NOT NULL,
  pdf_report BLOB NOT NULL,
  input_hash TEXT NOT NULL,
  replay_hash TEXT NOT NULL,
  format_version TEXT NOT NULL,
  supersedes_dossier_id TEXT,
  revision INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(opportunity_id, input_hash)
);
```

Foreign keys link the opportunity, Knowledge Review, assessment, and optional
predecessor. An opportunity/date index supports listing. No existing table,
column, row, database file, or evidence file is removed or rewritten.

## Exact Sprint 5 source changes

Added:

- `CHANGES-SPRINT5.md`
- `INSTALL-SPRINT5.md`
- `SPRINT5-PACKAGE-MANIFEST.txt`
- `SPRINT5-VERIFICATION-CHECKLIST.md`
- `anchorintel_api/dossier.py`

Changed:

- `ARCHITECTURE.md`
- `BOOT-0020-IMPLEMENTATION-NOTES.md`
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

All other packaged files are unchanged source carried forward from Sprint 4.

## Restore Sprint 4 if installation fails

Stop AnchorIntel. Preserve the failed Sprint 5 tree for diagnosis, then restore
the complete pre-migration source/database/file-store backup:

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
mv "apps/anchorintel/api" "apps/anchorintel/api-sprint5-failed"
mkdir -p "apps/anchorintel/api"
cp -a "backups/anchorintel-api-sprint4-20260720/." \
  "apps/anchorintel/api/"
chmod +x "apps/anchorintel/api/start-anchorintel.sh"
./apps/anchorintel/api/start-anchorintel.sh
```

This restores Sprint 4 source, SQLite state, and evidence files together. Do not
point Sprint 4 source at the migrated Sprint 5 database as a substitute for
restoration. Retain the failed tree until diagnosis is complete.
