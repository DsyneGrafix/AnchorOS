# Install BOOT-0025 Phase 1

1. Back up or commit the current AnchorOS working tree.
2. Extract this ZIP.
3. Copy the contents of the included `AnchorOS/` directory into the root of the existing AnchorOS repository, preserving paths and replacing files when prompted.
4. From the repository root, run:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/verify_boot_0025_phase1.py
python app.py
```

The default persistent database is created at:

```text
data/infrastructure_registry.db
```

To use another path:

```bash
export ANCHOROS_REGISTRY_DB=/absolute/path/registry.db
python app.py
```
