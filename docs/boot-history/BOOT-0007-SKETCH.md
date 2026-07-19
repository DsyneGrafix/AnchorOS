# BOOT-0007 — Event Before Coupling

**Status:** Planned  
**Primary Goal:** Replace the direct AnchorStack → Audit dependency with event-driven communication through AnchorCore Event Bus.

## Target Architecture

```text
AnchorStack
    │
    │ publishes: framework.started
    ▼
Event Bus
    │
    ├──► Audit Engine
    ├──► Health Monitor
    └──► Future Subscribers
```

## Current State

AnchorStack currently calls the Audit Engine directly when it starts.

```text
AnchorStack → Audit
```

This works, but it creates direct coupling between the framework and a platform service.

## Boot #0007 Change

AnchorStack will receive the Event Bus as its platform dependency and publish a structured event:

```text
framework.started
```

The Audit Engine will subscribe to that event and create the audit record.

AnchorStack will no longer know that Audit exists.

## Required Work

1. Extend `EventBus` with:
   - `subscribe(event_name, callback)`
   - `publish(event_name, payload)`

2. Add an Audit event handler:
   - `handle_event(payload)`

3. Update AnchorStack:
   - Replace direct `audit.log(...)`
   - Publish `framework.started` through Event Bus

4. Update startup:
   - Subscribe Audit to `framework.started`
   - Provide Event Bus to AnchorStack through the discovery context

5. Verify:
   - Event is published
   - Audit receives it
   - Audit record is preserved
   - AnchorStack starts without a direct Audit dependency

## Acceptance Criteria

Boot #0007 is complete when the console shows:

```text
✓ Event: framework.started
✓ Audit: [AnchorStack] framework.started — AnchorStack entered the Running state.
```

and AnchorStack has no direct import or reference to the Audit class.

## Doctrine Enforced

> Event Before Coupling

Components communicate through events whenever practical rather than direct dependencies.
