# AIN-302 — Research Findings & Evidence Lifecycle

This patch extends the verified AIN-201.1 pipeline core with the first
controlled intelligence-creation capability.

## Implements

- Source admission
- Versioned draft findings
- Finding receipts
- Duplicate correlation
- Reviewer authority
- Human review decisions
- Atomic authoritative evidence commits
- Idempotent evidence retries
- Reconstructable source → finding → review → evidence chain

## Prerequisites

- AnchorOS repository
- AIN-201.1 installed and tagged
- Python 3.12+
- Existing `anchorinsight_pipeline/`

## Install

From the extracted package folder:

```bash
./install_patch.sh "$HOME/Desktop/AnchorStack 1.0 Canon/Platform/AnchorOS"
```

## Verify

From the AnchorOS repository root:

```bash
python -m unittest tests.test_ain302_evidence_lifecycle -v
python -m examples.run_ain302_evidence_proof
```

## Scope boundary

This milestone does not implement live web acquisition, scheduling, score
recalculation, opportunity generation, report rendering, or automatic approval.
