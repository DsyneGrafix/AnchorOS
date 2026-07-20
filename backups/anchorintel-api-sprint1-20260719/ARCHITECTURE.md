# AnchorIntel API v1 Architecture

## Decision-operating-system boundary

The long-range operating loop is:

```text
Research → Evidence → Knowledge Modules → Opportunity → Assessment
         → Decision → Lifecycle → Revalidation → Learning → Knowledge Library
```

Version 1 implements the durable middle of that loop: Evidence → Opportunity → Assessment → Decision → Lifecycle → Revalidation. Research acquisition and Knowledge Modules remain external inputs until their provenance, versioning, and recommendation contracts are defined.

## Layering

```text
Clients / AnchorFiber / Opportunity workspace
                    ↓ HTTP /v1 and server-rendered commands
AnchorIntel business services and lifecycle controls
                    ↓ stable adapter
S.P.A.T.I.A.L. assessment engine
                    ↓
SQLite records, immutable assessment snapshots, audit events
                    ↑
AnchorOS register / start / stop / health
```

The API owns resource identity, revisions, evidence transitions, lifecycle events, persistence, audit, and reports. The Opportunity workspace calls the same business service as API clients, so edits and archives preserve identical validation, concurrency, and audit behavior. The engine owns validation, scoring, confidence, gates, warnings, and deterministic recommendation. Clients never call a public `calculate_score` function.

`OI-000001` is installed through an idempotent bootstrap. Bootstrap never
overwrites an existing active or archived record, protecting manual edits,
linked evidence, and audit history.

## Resource invariants

| Resource | Invariant |
|---|---|
| Opportunity | May be saved as an incomplete draft; must satisfy the engine contract before assessment |
| Evidence | Belongs to one opportunity; promotion to S or V uses the verification command |
| Assessment | Immutable snapshot of the opportunity and all current evidence plus engine result |
| Report | Projection of a stored assessment, so later record edits cannot rewrite history |
| Lifecycle event | Records prior state, resulting state, triggering assessment, reason, and time |
| Audit entry | Append-only actor/action record for mutations and assessment runs |

## Lifecycle state

An opportunity begins `Unassessed`. A successful assessment sets its operational queue to the engine recommendation: `Pursue`, `Validate`, `Monitor`, `Hold`, or `Reject`. The v1 dashboard-oriented endpoints expose Hold, Monitor, Pursue, and due-review queues. Validate and Reject remain visible through the opportunity resource and can receive dedicated routes without changing stored state.

Archive sets the lifecycle state to `Archived` and excludes the opportunity from normal collections. Revalidation requires a prior assessment, optionally updates lifecycle controls, and creates an immutable successor assessment.

## AnchorOS separation

- **AnchorOS** supplies process lifecycle, authenticated gateway concerns, shared operational services, and module registration.
- **AnchorIntel** supplies opportunity, evidence, assessment, reporting, revalidation, and learning-oriented service contracts.
- **S.P.A.T.I.A.L.** supplies the methodology and deterministic assessment framework.
- **AnchorFiber and future applications** consume the service and contribute domain records; they do not own the platform or engine lifecycle.

This keeps platform, framework, and application responsibilities explicit while allowing the engine to evolve behind `/v1/assessments/run`.
