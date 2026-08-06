# AIN-201.1 — Commercial Intelligence Pipeline Core

This patch establishes the deterministic orchestration foundation for AIN-201.

## Included

- Immutable pipeline request
- Idempotency key and request fingerprint
- Pipeline manifest and integrity hash
- Common stage contract
- Pipeline orchestrator
- Target Resolution stage
- Read-only Organization Profile Refresh stage
- Optional/requested-output stage semantics
- JSON manifest and receipt persistence
- Replay comparison foundation
- Automated tests
- CPS Energy proof runner

## Prerequisites

This is a patch package. It expects the target AnchorOS repository to already contain:

- `anchorinsight_registry/`
- CIR-002 schema and database support
- AIN-101 Registry Service
- AIN-102 Scoring Service
- AIN-103 Profile Service
- A populated `data/anchorinsight.db`

## Install into AnchorOS

From the AnchorOS repository root, copy:

```bash
cp -r AIN-201_1_Commercial_Intelligence_Pipeline_Core/anchorinsight_pipeline .
cp AIN-201_1_Commercial_Intelligence_Pipeline_Core/tests/test_ain201_pipeline_core.py tests/
cp AIN-201_1_Commercial_Intelligence_Pipeline_Core/examples/run_ain201_pipeline.py examples/
```

## Verify

```bash
python -m unittest tests.test_ain201_pipeline_core -v
python -m examples.run_ain201_pipeline
```

## Scope boundary

AIN-201.1 proves orchestration, target resolution, stage receipts, manifest integrity,
idempotency, optional-stage semantics, and profile refresh.

It does not yet implement autonomous research, evidence review, registry commits,
score changes, opportunity creation, dashboard publication, or report generation.
