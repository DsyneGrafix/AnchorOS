# Customer Onboarding Demonstration

This application demonstrates CP-001 through CP-009 using the real AnchorOS
Audit, Event Bus, Configuration, Manifest, Health, and Boot Pipeline
components.

Run it from the repository root:

```bash
python -m apps.customer_onboarding_demo
```

The BOOT-0021 Security Core returns deterministic, hash-linked integration
receipts through the pipeline's existing public consumer contract. It does
not authenticate identities, issue tokens, store credentials, contact an
identity provider, or provide tenant infrastructure isolation.

The demonstration prepares a deployment record but does not deploy external
resources. It contains no CRM, billing, payment, invoice, forecasting, or
marketing behavior.
