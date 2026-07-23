# BOOT-0021 — Security Core v0.1

## Objective

Introduce the first bounded, authoritative Security Core as an AnchorOS
Platform Service and replace the Customer Onboarding demonstration adapter
without expanding into enterprise IAM.

## Implemented

- SC-001 dependency-checked initialization and lifecycle states.
- SC-002 bounded organization identity metadata registration.
- SC-003 deterministic, idempotent, organization-scoped role assignment.
- SC-004 deterministic, idempotent organization policy assignment.
- SC-005 default-DENY role authorization with reason codes.
- SC-006 operational health and dependency reporting.
- SC-007 receipt and hash-chain verification.
- SC-008 deterministic operation replay.
- Platform Manifest, Service Registry, Configuration, Event Bus, Audit, Health,
  startup, and lifecycle integration.
- Direct compatibility with CP-003 and CP-006.
- End-to-end demonstration and automated verification.

## Evidence model

Each operation produces a sequential `SCR-######` receipt containing normalized
input, prior and resulting security state, SHA-256 hashes, result, outcome,
reason code, and previous-receipt linkage. Operational event timestamps are not
part of deterministic receipt hashes.

## Scope boundary

No passwords, authentication server, external identity provider, OAuth/OIDC,
SAML, tokens, certificates, secrets, encryption keys, tenant infrastructure,
network controls, malware detection, SIEM, billing, or license transactions are
implemented.

## Milestone status

Implementation is maintained on local branch
`feature/boot-0021-security-core`. No commit, push, merge, tag, release, or
publication is authorized by this work package.
