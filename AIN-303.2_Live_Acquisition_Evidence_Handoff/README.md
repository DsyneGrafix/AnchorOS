# AIN-303.2 — Live Acquisition → AIN-302 Handoff

**Status:** Release Candidate

## Objective

Close the Version 1 boundary between AIN-303 research acquisition and the AIN-302 governed evidence lifecycle.

## Implemented

- Bounded live HTTP/HTTPS acquisition provider.
- Existing AIN-303 immutable document preservation and acquisition receipts remain authoritative.
- Provenance validation across CandidateSource, AcquiredDocument, and AcquisitionReceipt.
- Deterministic AIN-303.2 handoff receipt with SHA-256 integrity hash.
- Immutable persistence of handoff receipts.
- AIN-302 source admission through the existing EvidenceLifecycleService.
- End-to-end bridge orchestration from ResearchRequest through live acquisition to AIN-302 source admission.
- Verification that AIN-303.2 does not create findings, approve findings, commit evidence, score organizations, or authorize commercial action.

## Architecture Boundary

```text
ResearchRequest
    ↓
AIN-303.1 ResearchPlan
    ↓
CandidateSource
    ↓
AIN-303.2 Live Provider
    ↓
AcquiredDocument + AcquisitionReceipt
    ↓
Provenance / Hash Validation
    ↓
EvidenceHandoffReceipt
    ↓
AIN-302 Source Admission
    ↓
ADMITTED SOURCE

STOP

AIN-302 remains responsible for:
- finding creation
- human review
- finding approval/rejection
- authoritative evidence commit
```

## V1 Live Provider Boundary

The bundled provider intentionally retrieves one already-approved HTTP/HTTPS URL at a time. It does not crawl links, execute JavaScript, bypass access controls, rotate proxies, or perform AI extraction.

A future provider such as Apify can implement the same provider contract without changing the evidence handoff boundary.

## Verification

`tests/test_ain3032_live_handoff.py` verifies live HTTP retrieval using a local HTTP server, acquisition receipts, provenance integrity checks, handoff receipt persistence, AIN-302 source admission, rejection of invalid chains, and the complete ResearchRequest → live acquisition → AIN-302 handoff path.
