# BOOT-0023 — Mission Control Integration Architecture

Mission Control is the first application managed by AnchorOS. It is discovered after services and frameworks, registered in the Platform Manifest, started by the Lifecycle Manager, and stopped before frameworks and services.

```text
AnchorOS Boot
  ├── Services
  ├── Frameworks
  ├── Applications
  │    └── Mission Control
  ├── Boot Pipeline Verification
  └── Operational Declaration
```

Mission Control receives platform events through the Event Bus and exposes a read-only operational snapshot through a local standard-library HTTP server. The browser dashboard retrieves current state from versioned `/api/v1` endpoints.

The server binds to loopback only. BOOT-0023 does not expose Mission Control to the network by default.
