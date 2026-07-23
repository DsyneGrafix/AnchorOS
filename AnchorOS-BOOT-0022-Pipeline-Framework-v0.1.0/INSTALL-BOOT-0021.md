# BOOT-0021 Standalone Installation and Verification

Package: `AnchorOS-BOOT-0021-Security-Core-v0.1.1-standalone.zip`

This package is a complete repository snapshot. Do not overlay it onto an
existing checkout.

## Extract

```bash
unzip AnchorOS-BOOT-0021-Security-Core-v0.1.1-standalone.zip
cd AnchorOS-BOOT-0021-Security-Core-v0.1.1
```

## Verify package integrity

```bash
sha256sum -c BOOT-0021-SHA256SUMS.txt
```

Every listed file must report `OK`. In particular, confirm:

```bash
test -f core/boot_pipeline.py
test -f core/module.py
test -f core/service_registry.py
test -f services/security_core/engine.py
test -f pipelines/customer_onboarding/engine.py
```

## Optional Python environment

The core platform and security tests use the standard library. For the full
AnchorIntel API environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

## Execute verification

```bash
python -m compileall -q core services pipelines apps tests
python -m unittest discover -s tests -v
PYTHONPATH=spatial-opportunity-engine \
  python -m unittest discover -s spatial-opportunity-engine/tests -v
PYTHONPATH=apps/anchorintel/api:spatial-opportunity-engine \
python -m unittest discover -s apps/anchorintel/api/tests -v
python app.py
python -m apps.security_core_demo
bash -n apps/anchorintel/api/start-anchorintel.sh
```

Expected results:

- 29 Security Core and Customer Onboarding tests pass;
- 8 S.P.A.T.I.A.L. tests pass;
- 40 AnchorIntel tests pass;
- Boot Pipeline reports 8/8 `PASS`;
- platform status is `HEALTHY`;
- Security Core is `Operational`;
- the demonstration reaches verified customer state `Operational`.

## Removal

The package does not migrate or modify external data. To remove this standalone
copy, archive or delete its extracted directory. This does not affect any other
AnchorOS checkout.
