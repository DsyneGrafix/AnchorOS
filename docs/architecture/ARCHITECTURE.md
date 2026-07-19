                        AnchorOS

                Operational Platform

                           │

                    Boot Pipeline
                           │

        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼

      Core            AnchorCore         Frameworks

  Module Manager      Audit Engine       AnchorStack
  Lifecycle           Event Bus
  Boot Pipeline       Health
                      Manifest
                      Configuration

                           │
                           ▼

                     Applications

Core
Defines platform behavior and execution.

AnchorCore
Provides reusable platform services consumed by frameworks.
