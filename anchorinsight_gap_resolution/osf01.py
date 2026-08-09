"""OSF-01 Problem Alignment determination.

Evaluates governed customer evidence against the bounded SLS-CAP-001 capability
registry without inventing semantic matches. Capability intersections must be
explicitly asserted by a reviewer/evaluator and trace to governed COF-EVD-*
records plus an admissible CAP-* definition.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from typing import Iterable

from .capabilities import CapabilityRegistry, CurrentCapability, load_sls_cap_001


class OSF01State(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    UNKNOWN = "UNKNOWN"


class CapabilityMatchState(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"


@dataclass(frozen=True, slots=True)
class GovernedEvidenceReference:
    evidence_id: str
    assertion: str
    classification: str
    verified: bool

    def validate(self) -> None:
        if not self.evidence_id.startswith("COF-EVD-"):
            raise ValueError("OSF-01 evidence must use a COF-EVD-* identifier")
        if not self.assertion.strip():
            raise ValueError("OSF-01 evidence assertion is required")
        if not self.verified:
            raise ValueError("OSF-01 may only consume verified governed evidence")


@dataclass(frozen=True, slots=True)
class CapabilityMatchAssessment:
    capability_id: str
    state: CapabilityMatchState
    evidence_ids: tuple[str, ...]
    rationale: str
    evaluator_id: str

    def validate(self) -> None:
        if not self.evidence_ids:
            raise ValueError("Capability match assessment requires governed evidence")
        if not self.rationale.strip():
            raise ValueError("Capability match assessment requires a rationale")
        if not self.evaluator_id.strip():
            raise ValueError("Capability match assessment requires evaluator identity")


@dataclass(frozen=True, slots=True)
class OSF01Determination:
    organization_id: str
    contract_id: str
    obligation_id: str
    capability_registry_id: str
    state: OSF01State
    evidence_ids: tuple[str, ...]
    supported_capability_ids: tuple[str, ...]
    partially_supported_capability_ids: tuple[str, ...]
    not_supported_capability_ids: tuple[str, ...]
    rationale: str

    @property
    def integrity_hash(self) -> str:
        payload = {
            "organization_id": self.organization_id,
            "contract_id": self.contract_id,
            "obligation_id": self.obligation_id,
            "capability_registry_id": self.capability_registry_id,
            "state": self.state.value,
            "evidence_ids": list(self.evidence_ids),
            "supported_capability_ids": list(self.supported_capability_ids),
            "partially_supported_capability_ids": list(self.partially_supported_capability_ids),
            "not_supported_capability_ids": list(self.not_supported_capability_ids),
            "rationale": self.rationale,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {
            "organization_id": self.organization_id,
            "contract_id": self.contract_id,
            "obligation_id": self.obligation_id,
            "capability_registry_id": self.capability_registry_id,
            "state": self.state.value,
            "evidence_ids": list(self.evidence_ids),
            "supported_capability_ids": list(self.supported_capability_ids),
            "partially_supported_capability_ids": list(self.partially_supported_capability_ids),
            "not_supported_capability_ids": list(self.not_supported_capability_ids),
            "rationale": self.rationale,
            "integrity_hash": self.integrity_hash,
        }


class OSF01ProblemAlignmentService:
    """Determine OSF-01 from governed evidence and explicit CAP-* assessments."""

    VERSION = "1.0"
    CONTRACT_ID = "OSF-EC-001"
    OBLIGATION_ID = "OSF-01"

    def __init__(self, capability_registry: CapabilityRegistry | None = None) -> None:
        self.capability_registry = capability_registry or load_sls_cap_001()

    def determine(
        self,
        *,
        organization_id: str,
        evidence: Iterable[GovernedEvidenceReference],
        capability_assessments: Iterable[CapabilityMatchAssessment] = (),
    ) -> OSF01Determination:
        if not organization_id.strip():
            raise ValueError("organization_id is required")

        evidence_items = tuple(evidence)
        for item in evidence_items:
            item.validate()
        evidence_by_id = {item.evidence_id: item for item in evidence_items}
        if len(evidence_by_id) != len(evidence_items):
            raise ValueError("OSF-01 evidence identifiers must be unique")

        assessments = tuple(capability_assessments)
        admissible = {
            item.capability_id: item
            for item in self.capability_registry.admissible_capabilities
        }
        seen_capabilities: set[str] = set()
        for assessment in assessments:
            assessment.validate()
            if assessment.capability_id not in admissible:
                raise ValueError(
                    f"Capability {assessment.capability_id} is not admissible under "
                    f"{self.capability_registry.registry_id}"
                )
            if assessment.capability_id in seen_capabilities:
                raise ValueError("Only one OSF-01 assessment per capability is permitted")
            seen_capabilities.add(assessment.capability_id)
            unknown_evidence = set(assessment.evidence_ids) - set(evidence_by_id)
            if unknown_evidence:
                raise ValueError(
                    "Capability assessment references evidence not supplied to OSF-01: "
                    + ", ".join(sorted(unknown_evidence))
                )

        supported = tuple(
            a.capability_id for a in assessments if a.state == CapabilityMatchState.SUPPORTED
        )
        partial = tuple(
            a.capability_id
            for a in assessments
            if a.state == CapabilityMatchState.PARTIALLY_SUPPORTED
        )
        rejected = tuple(
            a.capability_id
            for a in assessments
            if a.state == CapabilityMatchState.NOT_SUPPORTED
        )

        if not evidence_items:
            state = OSF01State.UNKNOWN
            rationale = "No verified governed customer evidence is available for OSF-01."
        elif supported:
            state = OSF01State.SUPPORTED
            rationale = (
                "Verified governed evidence and an explicit evaluator assessment establish "
                "at least one admissible current SLS capability intersection."
            )
        elif partial:
            state = OSF01State.PARTIALLY_SUPPORTED
            rationale = (
                "Verified governed evidence establishes a customer need and an evaluator "
                "identified at least one plausible but incomplete current capability intersection."
            )
        elif rejected and len(rejected) == len(admissible):
            state = OSF01State.NOT_SUPPORTED
            rationale = (
                "Verified governed evidence establishes the customer need, and every capability "
                "admissible under SLS-CAP-001 was explicitly evaluated as not addressing it."
            )
        else:
            state = OSF01State.UNKNOWN
            rationale = (
                "Verified governed evidence establishes customer-side facts, but no sufficiently "
                "supported current-capability intersection has been established."
            )

        return OSF01Determination(
            organization_id=organization_id,
            contract_id=self.CONTRACT_ID,
            obligation_id=self.OBLIGATION_ID,
            capability_registry_id=self.capability_registry.registry_id,
            state=state,
            evidence_ids=tuple(sorted(evidence_by_id)),
            supported_capability_ids=tuple(sorted(supported)),
            partially_supported_capability_ids=tuple(sorted(partial)),
            not_supported_capability_ids=tuple(sorted(rejected)),
            rationale=rationale,
        )
