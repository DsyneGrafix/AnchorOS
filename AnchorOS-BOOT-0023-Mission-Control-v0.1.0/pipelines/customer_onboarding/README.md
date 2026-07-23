# AnchorOS Customer Onboarding Pipeline v0.1

The Customer Onboarding Pipeline provisions an organization through a bounded,
deterministic lifecycle. Pipelines govern lifecycles; Platform Services provide
reusable capabilities; frameworks provide domain intelligence; applications
consume those layers.

## Scope boundary

This package manages customer onboarding only. It does not implement CRM,
billing, payments, invoicing, sales forecasting, marketing automation,
authentication, authorization, credential storage, or external identity
providers.

CP-003 and CP-006 consume `SecurityCoreGateway`, a narrow public interface now
implemented directly by the BOOT-0021 Security Core Platform Service. Calls
include deterministic idempotency keys and fail closed when the interface or
its receipts are unavailable.

`CustomerPipelineEngine.from_registry()` resolves the five consumed Platform
Services from the authoritative `ServiceRegistry`; it does not construct or
duplicate them.

## Stages

| Stage | Purpose | Entry | Exit |
|---|---|---|---|
| CP-001 Customer Registration | Accept a bounded onboarding request | Unique ID, organization name, canonical slug | Registration evidence recorded |
| CP-002 Organization Provisioning | Produce a stable AnchorOS organization identity | Valid registration | Deterministic organization ID recorded |
| CP-003 Identity & Role Assignment | Request assignment from Security Core | Provisioned organization, operational Security Core, identity and roles | Security Core receipt validated |
| CP-004 License Assignment | Assign a configured entitlement | Identity assignment and configured license | Non-commercial license assignment recorded |
| CP-005 Framework Enablement | Enable available frameworks | License assigned; frameworks registered and Running | Enablement evidence recorded |
| CP-006 Security Policy Assignment | Request policy assignment from Security Core | Frameworks enabled and policy supplied | Security Core receipt validated |
| CP-007 Deployment Preparation | Prepare a manifest-bound deployment plan | Security policy assigned and environment configured | Preparation-only plan and digest recorded |
| CP-008 Validation | Verify the full evidence chain and platform readiness | Prior evidence, running services, full Boot Pipeline pass | Validation receipt reports PASS |
| CP-009 Operational | Declare the organization operational | Passing validation receipt | Final operational transition recorded |

The authoritative machine-readable definitions, including detailed entry and
exit criteria, are in `stages.py`.

## Determinism and replay

Every state transition records a canonical input hash, the previous transition
hash, structured output details, and its own SHA-256 transition hash. Execution
stops at the first failed requirement and transitions to `Failed`. Replay
re-executes the request without creating a second record and compares the full
terminal state, transition count, and final hash.

Audit timestamps and event IDs are operational metadata from existing Platform
Services; they are intentionally excluded from deterministic transition hashes.

## Boot integration

CP-008 consumes the existing `BootPipeline` result and requires all eight
stages to be present and passing. The Customer Onboarding Pipeline does not
change Boot Pipeline stages, execution order, or operational behavior.

## Version 0.1 limitations

- Onboarding records use an in-memory store; durable persistence and restart
  recovery are not yet implemented.
- A failed record is terminal and requires a new onboarding identifier; a
  controlled resume/re-entry workflow is not yet implemented.
- Framework enablement records organization-to-framework intent after Manifest
  and Health checks; it does not create external tenant resources.
- Deployment Preparation produces evidence only and performs no deployment.
- Security assignments are in memory and do not survive service restart.
- Security Core v0.1 registers bounded identity metadata but does not create or
  authenticate accounts and does not contact external identity providers.
