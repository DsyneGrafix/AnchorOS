# AnchorOS Customer Onboarding Pipeline — CP-001 v0.1

## Package contents

- Customer Pipeline Engine
- CP-001 through CP-009 stage definitions
- Customer onboarding state and transition models
- Fail-closed lifecycle manager
- Hash-linked replay evidence
- Audit and Event Bus integration
- Configuration, Manifest, Health, Service Registry, and Boot Pipeline integration
- Public Security Core consumer contract
- Non-production demonstration Security Core adapter
- Runnable demonstration application
- Ten Customer Onboarding Pipeline unit tests
- Architecture, scope, and known-limitations documentation

## Verified baseline

- Customer Onboarding Pipeline tests: 10/10 passed
- AnchorIntel API tests: 40/40 passed
- S.P.A.T.I.A.L. engine tests: 8/8 passed
- AnchorOS Boot Pipeline: PASS, 8/8 stages
- AnchorOS Lifecycle Manager: VERIFIED
- Demonstration terminal state: Operational
- Deterministic replay: VERIFIED

## Installation

Merge the package contents into the root of the current AnchorOS repository,
preserving the included directory structure.

Run the focused tests:

```bash
python -m unittest tests.test_customer_onboarding
```

Run the demonstration:

```bash
python -m apps.customer_onboarding_demo
```

## Scope boundary

This version manages customer onboarding only. It does not implement CRM,
billing, payments, invoicing, sales forecasting, marketing automation,
authentication, authorization, credential storage, or external identity
providers.

The included Security Core adapter is for deterministic demonstration and
testing only. It is not a production security implementation.

## Version 0.1 limitations

- Onboarding records are stored in memory.
- Failed records are terminal; controlled resume/re-entry is not implemented.
- Framework enablement records intent but does not create external resources.
- Deployment Preparation creates evidence but performs no deployment.
- Production CP-003 and CP-006 integration awaits the Security Core public API.

No Git commit, tag, release, or publication action is included in this package.
