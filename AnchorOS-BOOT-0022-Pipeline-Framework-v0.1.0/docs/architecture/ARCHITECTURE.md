# AnchorOS Architecture — BOOT-0021

```text
                         AnchorOS
                    Operational Platform

                            │
                      Boot Pipeline
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
     Kernel          Platform Services       Frameworks

 Module Manager      Audit Engine            AnchorDefense
 Lifecycle           Event Bus               AnchorEnergy
 Boot Pipeline       Configuration           AnchorFiber
 Service Registry    Health Monitor          AnchorGrid
                     Platform Manifest        AnchorHealth
                     Security Core            AnchorStack
                            │
                            ▼
               Pipelines and Applications
```

## Architectural language

- Pipelines govern deterministic lifecycles.
- Platform Services provide reusable capabilities.
- Frameworks provide domain intelligence.
- Applications consume these layers through public interfaces.

Security Core is a Platform Service. The Customer Onboarding Pipeline consumes
its public gateway for CP-003 and CP-006; the pipeline does not implement
identity registration, role assignment, authorization, or policy evaluation.

The existing eight-stage Boot Pipeline remains unchanged. BOOT-0021 changes
service discovery only by passing the authoritative `ServiceRegistry` as the
factory context, allowing dependency-aware services to resolve existing
services at lifecycle start.
