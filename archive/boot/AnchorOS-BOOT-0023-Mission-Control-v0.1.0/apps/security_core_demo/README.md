# Security Core Demonstration

Run from the repository root:

```bash
python -m apps.security_core_demo
```

The application discovers and starts the real AnchorOS Platform Services,
resolves Security Core from `ServiceRegistry`, verifies all eight existing
Boot Pipeline stages, and demonstrates:

- identity metadata registration;
- organization-scoped role and policy assignments;
- one `ALLOW` and one default-deny `DENY` decision;
- hash-linked receipt verification and deterministic replay;
- CP-001 through CP-009 using the same Security Core instance.

No credentials are collected, no user is authenticated, and no external
identity provider, token service, secret store, or network service is used.
