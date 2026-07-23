# AnchorOS Security Core v0.1 — BOOT-0021

Security Core is an authoritative AnchorOS Platform Service providing a
narrow, deterministic interface for organization-scoped identity metadata,
role assignments, policy assignments, authorization decisions, and evidence
verification.

## Architectural boundary

```text
Applications and Pipelines
        ↓
Security Core public interface
        ↓
Audit · Event Bus · Configuration · Health · Manifest
        ↓
AnchorOS Kernel
```

Security Core inherits `Module`, is discovered with other services, retains
the authoritative `ServiceRegistry`, resolves its dependencies at `start()`,
appears in `PlatformManifest`, and participates in normal module lifecycle and
health reporting. It does not duplicate any Platform Service.

## Public interface

The service directly satisfies `SecurityCoreGateway`, including:

```python
health()
assign_identity_and_roles(...)
assign_policy(...)
```

It additionally exposes identity registration, role-based authorization,
receipt verification, full-chain verification, and deterministic replay.
The Customer Onboarding Pipeline contract was not changed.

## Deterministic evidence

Every attempted security operation creates a structured receipt with a stable
sequence, normalized input hash, prior and resulting security-state snapshots,
state hashes, previous receipt hash, result, outcome, reason code, and final
SHA-256 receipt hash. Wall-clock timestamps and Event Bus UUIDs are excluded
from the receipt evidence.

Assignment calls with identical normalized input and idempotency key return the
original logical receipt. Reusing a key with different input creates a
fail-closed conflict receipt. Replay reconstructs the operation from its stored
input and prior state and compares the expected resulting state, decision, and
evidence hash.

## Configuration

The existing Configuration service owns:

- `security_core.enabled`
- `security_core.required_platform_services`
- `security_core.allowed_roles`
- `security_core.allowed_policy_ids`

The platform defaults are defined in `services/configuration.py` and may be
overridden through the service API. The engine contains no customer-specific
role or policy list. Missing, malformed, disabled, or unconfigured values fail
closed.

## Authorization model

The v0.1 policy is deliberately small: an identity is `ALLOW`ed only when it is
registered within the requested organization and holds the configured required
role there. Every other outcome is `DENY`, with a reason code and receipt.

## Repository boundary

Identity, role, policy, receipt, and idempotency access are isolated behind
repository protocols. BOOT-0021 ships in-memory adapters only. Persistent
adapters can be added without changing the engine's public interface.

## Fail-closed behavior

Operations are rejected or denied when Security Core or a required service is
not running, configuration is missing, identifiers are invalid, roles or
policies are unconfigured, idempotency conflicts, or evidence fails
verification. Unexpected exceptions are converted to safe failure receipts;
raw internal exception text is not published.

## Explicit limitations

Security Core v0.1 is not an identity provider or enterprise IAM system. It
does not create accounts, authenticate credentials, store passwords, issue
tokens, implement OAuth/OIDC/SAML, contact external identity providers, manage
certificates/keys/secrets, isolate tenant infrastructure, administer users,
operate network controls, detect malware, or provide SIEM functionality.

State and receipts are lost when the process exits. The Audit service remains
an in-memory event consumer, receipt hashes are integrity checks rather than
digital signatures, and there is no concurrency qualification or persistent
transaction boundary in this milestone.
