# Changelog

## BOOT-0023 — Mission Control Integration

- Added Mission Control as the first managed AnchorOS application.
- Added application discovery, manifest registration, lifecycle startup, and shutdown.
- Added a dependency-free threaded local HTTP server.
- Added automatic browser launch after verified boot.
- Added a responsive live operational dashboard.
- Added platform status, health, inventory, manifest, audit, pipeline, and event APIs.
- Added event-bus subscriptions for platform and application lifecycle events.
- Added automatic port fallback from 8080 through 8090.
- Added `--verify-only` and `--no-browser` command-line options.
- Updated platform identity to BOOT-0023.
- Added four Mission Control tests; platform suite now contains 56 tests.
