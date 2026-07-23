# AnchorOS BOOT-0023 — Mission Control Integration

BOOT-0023 makes Mission Control the first managed AnchorOS application. A successful platform boot starts the local dashboard, registers it in the Platform Manifest, verifies the eight-stage boot pipeline, and opens the browser unless disabled.

## Start AnchorOS

```bash
python app.py
```

Mission Control normally opens at `http://127.0.0.1:8080`. If that port is occupied, AnchorOS automatically tries ports 8081 through 8090.

## Verification mode

```bash
python app.py --verify-only --no-browser
python -m unittest discover -s tests -v
```

## Mission Control APIs

- `/api/v1/status`
- `/api/v1/health`
- `/api/v1/services`
- `/api/v1/frameworks`
- `/api/v1/applications`
- `/api/v1/manifest`
- `/api/v1/audit`
- `/api/v1/pipeline`
- `/api/v1/events`
