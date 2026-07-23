# BOOT-0010 — Service Registry Architecture

**Status:** Architected  
**Metallurgy Stage:** Ember  
**Release Milestone:** AnchorOS v0.1.0 Alpha — Foundation

## Primary Goal

Introduce a platform-owned Service Registry that provides one authoritative directory of active AnchorOS services.

## Architectural Decision

The Service Registry belongs in the AnchorOS kernel:

```text
core/service_registry.py
```

It is not an AnchorCore service and is not discovered like a plugin.

Reason: discovery, dependency resolution, and framework creation all need the registry. Making the registry itself a discovered service would introduce a circular dependency.

## Target Architecture

```text
AnchorOS Kernel
├── ModuleManager
├── ServiceRegistry
└── Startup Orchestrator
        │
        ├── discovers AnchorCore
        ├── registers services
        ├── discovers frameworks
        └── supplies registry
```

## Target API

```python
registry.register(service)
registry.get("Event Bus")
registry.require("Audit Engine")
registry.contains("Health Monitor")
registry.list_services()
```

## Separation of Responsibility

### ModuleManager

- Discovers modules
- Owns lifecycle
- Starts and stops modules
- Produces health reports

### ServiceRegistry

- Provides service lookup
- Enforces uniqueness
- Resolves required dependencies
- Exposes the active service catalog

## Acceptance Criteria

1. `ServiceRegistry` exists in `core/service_registry.py`.
2. AnchorCore services are registered automatically.
3. Frameworks receive the registry rather than a raw context dictionary.
4. AnchorStack resolves Event Bus through `registry.require("Event Bus")`.
5. Missing dependencies fail clearly before startup.
6. Startup banner reports version, codename, boot, stage, and build.
7. AnchorOS ends with `Platform Operational`.
8. Git tag `v0.1.0-alpha` is created after verification.
