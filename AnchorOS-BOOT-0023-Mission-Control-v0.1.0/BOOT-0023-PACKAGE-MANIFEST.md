# BOOT-0023 Standalone Package Manifest

This is a complete standalone AnchorOS repository based on the verified BOOT-0022 baseline and extended with BOOT-0023 Mission Control Integration.

## Required runtime files

- `app.py`
- `startup.py`
- `version.py`
- `core/`
- `services/`
- `frameworks/`
- `applications/mission_control/`

## BOOT-0023 additions

- Mission Control managed application
- Application discovery and lifecycle integration
- Local HTTP server and responsive dashboard
- Versioned operational APIs
- Event Bus runtime feed
- Automatic browser launch
- Graceful shutdown
- Four Mission Control tests
- Installation, release, architecture, and verification documentation

## Standalone status

No files from BOOT-0021 or BOOT-0022 are required outside this archive. The package contains all Python source code and static assets needed to run BOOT-0023.
