

Do not extract the Sprint 2 ZIP directly over the working application. Stage
it, back up Sprint 1, inspect the overlay, run the tests, and only then start the
service against the existing database.

## Package boundary

The ZIP is rooted at `apps/anchorintel/api` for the installed AnchorOS layout.
It contains the complete API project but deliberately excludes:

- `data/anchorintel.db` and SQLite WAL/SHM files;
- all uploaded files under `data/evidence-files/`;
- Python caches and temporary test data; and
- changes to the sibling `spatial-opportunity-engine`.

## Files added by Sprint 2

- `.gitignore`
- `CHANGES-SPRINT2.md`
- `INSTALL-SPRINT2.md`
- `SPRINT2-PACKAGE-MANIFEST.txt`
- `SPRINT2-VERIFICATION-CHECKLIST.md`
- `data/evidence-files/.gitignore`

## Existing Sprint 1 files changed

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

The package also carries unchanged Sprint 1 project files so it is a complete
source snapshot. The package manifest identifies every installable member and
its SHA-256 digest; the manifest omits only its own recursive digest.

## 1. Stop the current service

If AnchorIntel is running, return to that terminal and press `Ctrl+C`. Do not
copy the database while the server is accepting writes.

## 2. Stage the ZIP

Assuming the downloaded file is in `~/Downloads`:

```bash
mkdir -p "/home/ricky/Desktop/anchorintel-sprint2-staging"
unzip -q "/home/ricky/Downloads/AnchorIntel-OI-000001-Sprint2.zip" \
  -d "/home/ricky/Desktop/anchorintel-sprint2-staging"
```

Confirm the staged layout:

```bash
find "/home/ricky/Desktop/anchorintel-sprint2-staging/apps/anchorintel/api" \
  -maxdepth 2 -type f | sort
```

## 3. Back up Sprint 1

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
mkdir -p "backups/anchorintel-api-sprint1-20260719"
cp -a "apps/anchorintel/api/." \
  "backups/anchorintel-api-sprint1-20260719/"
```

Confirm the database exists in the backup before continuing:

```bash
ls -lh \
  "backups/anchorintel-api-sprint1-20260719/data/anchorintel.db"
```

## 4. Install the source overlay

This merge does not remove files and the ZIP contains no database:

```bash
cp -a \
  "/home/ricky/Desktop/anchorintel-sprint2-staging/apps/anchorintel/api/." \
  "apps/anchorintel/api/"
chmod +x "apps/anchorintel/api/start-anchorintel.sh"
```

## 5. Run the isolated test suites before migration

The API tests use temporary databases and file stores; they do not alter the
installed `data/anchorintel.db`.

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS/apps/anchorintel/api"
PYTHONPATH="../spatial-opportunity-engine:." \
  python3 -m unittest discover -s tests -v

cd "../spatial-opportunity-engine"
python3 -m unittest discover -s tests -v
```

Do not continue unless both suites end with `OK`.

## 6. Start Sprint 2 and allow the safe migration

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
./apps/anchorintel/api/start-anchorintel.sh
```

Startup initializes the evidence file directory, migrates the database if
needed, and idempotently seeds OI-000001 and EV-000001. Open:

<http://127.0.0.1:8080/opportunities/OI-000001>

## Database migration

Repository startup reads `PRAGMA table_info(evidence)` and conditionally runs:

```sql
ALTER TABLE evidence ADD COLUMN archived INTEGER NOT NULL DEFAULT 0;
ALTER TABLE evidence ADD COLUMN archived_at TEXT;
```

It also creates an index over opportunity, archive state, and creation time.
The migration is additive and idempotent. It does not delete, replace, or
rewrite existing opportunity, evidence, assessment, lifecycle, or audit rows.
New evidence metadata remains in the existing JSON record column. Uploaded
bytes are stored under `data/evidence-files`, never in SQLite.

## Restore Sprint 1 if installation fails

Stop the service first. Preserve the failed Sprint 2 state instead of deleting
it, then restore the complete backup:

```bash
cd "/home/ricky/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
mv "apps/anchorintel/api" "apps/anchorintel/api-sprint2-failed"
mkdir -p "apps/anchorintel/api"
cp -a "backups/anchorintel-api-sprint1-20260719/." \
  "apps/anchorintel/api/"
chmod +x "apps/anchorintel/api/start-anchorintel.sh"
./apps/anchorintel/api/start-anchorintel.sh
```

This restores both Sprint 1 source and its pre-migration database. The moved
`api-sprint2-failed` directory retains any Sprint 2 uploads for diagnosis or
manual recovery. No normal rollback step permanently deletes evidence.
