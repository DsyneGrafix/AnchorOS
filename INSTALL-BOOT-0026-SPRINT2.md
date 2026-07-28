# Install BOOT-0026 Sprint 2

From the extracted patch directory, copy the contents of `AnchorOS/` over the root of the existing AnchorOS repository.

Example:

```bash
cp -a AnchorOS/. "/path/to/AnchorOS/"
cd "/path/to/AnchorOS"
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/verify_boot_0026_sprint2.py
python app.py
```

Expected service verification ending:

```text
Facility Service Status: OPERATIONAL
BOOT-0026 Sprint 2 Verification: PASS
```

Do not replace the repository with this ZIP. It is a patch and depends on BOOT-0025 and BOOT-0026 Sprint 1.
