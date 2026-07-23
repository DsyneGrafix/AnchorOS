# AnchorIntel Sprint 6 — Safe Installation and Sprint 5 Restoration

Do not extract the ZIP directly over the installed application. Sprint 6 adds a
database table and external archive storage. Stage it, stop AnchorIntel, back up
Sprint 5 source and all runtime state, verify independently, then install the
source overlay.

Installed application root:

```text
/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS/apps/anchorintel/api
```

## 1. Stop AnchorIntel

Press `Ctrl+C` in the terminal running AnchorIntel. Do not copy SQLite while the
service is accepting writes.

## 2. Verify and stage the package

```bash
cd "/home/ricky/Downloads"
sha256sum "AnchorIntel-OI-000001-Sprint6.zip"

mkdir -p "/home/ricky/Desktop/anchorintel-sprint6-staging"
unzip -q "AnchorIntel-OI-000001-Sprint6.zip" \
  -d "/home/ricky/Desktop/anchorintel-sprint6-staging"

find "/home/ricky/Desktop/anchorintel-sprint6-staging/apps/anchorintel/api" \
  -type f | sort
```

Compare the digest with the delivered digest and verify
`SPRINT6-PACKAGE-MANIFEST.txt`. Confirm there is no database, WAL/SHM, uploaded
evidence, generated archive ZIP, backup, `tmp`, cache, or customer data.

## 3. Back up Sprint 5 before migration

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
mkdir -p "backups/anchorintel-api-sprint5-20260720"
cp -a "apps/anchorintel/api/." \
  "backups/anchorintel-api-sprint5-20260720/"
```

Verify the stopped-service backup:

```bash
ls -lh "backups/anchorintel-api-sprint5-20260720/data/anchorintel.db"
find "backups/anchorintel-api-sprint5-20260720/data/evidence-files" \
  -maxdepth 1 -type f -print
find "backups/anchorintel-api-sprint5-20260720/data/archives" \
  -maxdepth 1 -type f -print 2>/dev/null || true
```

Keep DB, WAL/SHM, evidence, and archive storage together. The ZIP is a source
overlay and intentionally contains none of those runtime artifacts.

## 4. Verify staged source independently

```bash
mkdir -p "/home/ricky/Desktop/anchorintel-sprint6-verification/apps/anchorintel"
cp -a "/home/ricky/Desktop/anchorintel-sprint6-staging/apps/anchorintel/api" \
  "/home/ricky/Desktop/anchorintel-sprint6-verification/apps/anchorintel/"
cp -a "apps/anchorintel/spatial-opportunity-engine" \
  "/home/ricky/Desktop/anchorintel-sprint6-verification/apps/anchorintel/"

cd "/home/ricky/Desktop/anchorintel-sprint6-verification/apps/anchorintel/api"
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v

PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s ../spatial-opportunity-engine/tests -v
```

Do not continue unless the API reports 40 tests and `OK`, and the engine reports
eight tests and `OK`.

## 5. Install the database-free source overlay

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
cp -a \
  "/home/ricky/Desktop/anchorintel-sprint6-staging/apps/anchorintel/api/." \
  "apps/anchorintel/api/"
chmod +x "apps/anchorintel/api/start-anchorintel.sh"
```

This copy is additive and does not delete runtime files.

## 6. Start and migrate

```bash
./apps/anchorintel/api/start-anchorintel.sh
```

Startup creates the archive schema and `data/archives/` idempotently. It does
not create `AR-000001` automatically. Open
<http://127.0.0.1:8080/opportunities/OI-000001>, review Archive Results
readiness, and archive only after verifying the current chain.

## Database migration

Sprint 6 adds one table and two indexes:

```sql
CREATE TABLE archives (
  archive_id TEXT PRIMARY KEY,
  opportunity_id TEXT NOT NULL,
  opportunity_revision INTEGER NOT NULL,
  evidence_trace_json TEXT NOT NULL,
  knowledge_review_id TEXT NOT NULL,
  knowledge_review_revision INTEGER NOT NULL,
  assessment_id TEXT NOT NULL,
  assessment_revision INTEGER NOT NULL,
  dossier_id TEXT NOT NULL,
  dossier_format_version TEXT NOT NULL,
  archive_status TEXT NOT NULL,
  archive_reason TEXT NOT NULL,
  archived_by TEXT NOT NULL,
  archive_timestamp TEXT NOT NULL,
  package_manifest_json TEXT NOT NULL,
  package_hash TEXT NOT NULL,
  replay_hash TEXT NOT NULL,
  record_count INTEGER NOT NULL,
  file_count INTEGER NOT NULL,
  storage_location TEXT NOT NULL,
  provenance_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX archives_opportunity_idx
  ON archives(opportunity_id, created_at DESC);

CREATE UNIQUE INDEX archives_current_opportunity_idx
  ON archives(opportunity_id)
  WHERE archive_status IN ('Prepared', 'Archived');
```

Foreign keys reference opportunity, review, assessment, and dossier. No existing
table, column, row, DB file, evidence file, or dossier export is removed or
rewritten. Successful archive creation sets the opportunity container to
archived/read-only without incrementing the source revision.

## Exact Sprint 6 source changes

Added:

- `ARCHIVE-FORMAT.md`
- `BOOT-0020-COMPLETION-REPORT.md`
- `CHANGES-SPRINT6.md`
- `INSTALL-SPRINT6.md`
- `SPRINT6-PACKAGE-MANIFEST.txt`
- `SPRINT6-VERIFICATION-CHECKLIST.md`
- `anchorintel_api/archive.py`
- `data/archives/.gitignore`
- `tests/test_archive.py`

Changed:

- `.gitignore`
- `ARCHITECTURE.md`
- `BOOT-0020-IMPLEMENTATION-NOTES.md`
- `README.md`
- `VERIFICATION.md`
- `anchorintel_api/__init__.py`
- `anchorintel_api/anchoros.py`
- `anchorintel_api/app.py`
- `anchorintel_api/openapi.py`
- `anchorintel_api/repository.py`
- `anchorintel_api/server.py`
- `anchorintel_api/service.py`
- `anchorintel_api/web.py`
- `anchoros-service.json`
- `pyproject.toml`
- `tests/test_api.py`

All other packaged files are carried forward unchanged from Sprint 5.

## Restore Sprint 5 if installation fails

Stop AnchorIntel. Preserve the failed Sprint 6 tree, then restore the complete
pre-migration backup:

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
mv "apps/anchorintel/api" "apps/anchorintel/api-sprint6-failed"
mkdir -p "apps/anchorintel/api"
cp -a "backups/anchorintel-api-sprint5-20260720/." \
  "apps/anchorintel/api/"
chmod +x "apps/anchorintel/api/start-anchorintel.sh"
./apps/anchorintel/api/start-anchorintel.sh
```

This restores Sprint 5 source, SQLite, evidence, and preexisting archive storage
together. Do not point restored Sprint 5 source at a migrated Sprint 6 database
as a substitute for restoration. Keep the failed tree until diagnosis completes.
