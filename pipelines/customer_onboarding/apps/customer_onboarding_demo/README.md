# Customer Onboarding Demonstration

This application demonstrates CP-001 through CP-009 using the real AnchorOS
Audit, Event Bus, Configuration, Manifest, Health, and Boot Pipeline
components.

Run it from the repository root:

```bash
python -m apps.customer_onboarding_demo
```

The demonstration Security Core adapter returns deterministic integration
receipts so the public consumer boundary can be exercised before BOOT-0021
provides the production Security Core. It does not authenticate identities,
authorize roles, evaluate policy, store credentials, or provide tenant
isolation. It is not a production security implementation.

The demonstration prepares a deployment record but does not deploy external
resources. It contains no CRM, billing, payment, invoice, forecasting, or
marketing behavior.
