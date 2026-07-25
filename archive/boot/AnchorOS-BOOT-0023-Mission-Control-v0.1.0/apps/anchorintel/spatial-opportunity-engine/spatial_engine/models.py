"""Typed domain models for S.P.A.T.I.A.L. opportunity analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class EvidenceState(str, Enum):
    VERIFIED = "V"
    SUPPORTED = "S"
    ASSUMPTION = "A"
    UNKNOWN = "U"
    DISPUTED = "D"


class GateStatus(str, Enum):
    PASS = "pass"
    PROVISIONAL = "provisional"
    FAIL = "fail"


class Decision(str, Enum):
    PURSUE = "Pursue"
    VALIDATE = "Validate"
    MONITOR = "Monitor"
    HOLD = "Hold"
    REJECT = "Reject"


class Confidence(str, Enum):
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"


class FatalDisposition(str, Enum):
    HOLD = "hold"
    REJECT = "reject"


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    claim: str
    state: EvidenceState
    source: str = ""
    source_date: str = ""
    retrieved_date: str = ""
    geography: str = ""
    material: bool = True
    staleness_risk: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvidenceItem":
        return cls(
            evidence_id=str(raw.get("evidence_id", "")).strip(),
            claim=str(raw.get("claim", "")).strip(),
            state=EvidenceState(str(raw.get("state", "")).upper()),
            source=str(raw.get("source", "")).strip(),
            source_date=str(raw.get("source_date", "")).strip(),
            retrieved_date=str(raw.get("retrieved_date", "")).strip(),
            geography=str(raw.get("geography", "")).strip(),
            material=bool(raw.get("material", True)),
            staleness_risk=str(raw.get("staleness_risk", "")).strip(),
            notes=str(raw.get("notes", "")).strip(),
        )


@dataclass(frozen=True)
class DimensionAssessment:
    score: float
    rationale: str
    evidence_refs: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DimensionAssessment":
        return cls(
            score=float(raw.get("score", -1)),
            rationale=str(raw.get("rationale", "")).strip(),
            evidence_refs=tuple(str(v).strip() for v in raw.get("evidence_refs", [])),
        )


@dataclass(frozen=True)
class GateAssessment:
    status: GateStatus
    rationale: str
    evidence_refs: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "GateAssessment":
        return cls(
            status=GateStatus(str(raw.get("status", "")).lower()),
            rationale=str(raw.get("rationale", "")).strip(),
            evidence_refs=tuple(str(v).strip() for v in raw.get("evidence_refs", [])),
        )


@dataclass(frozen=True)
class FatalConstraint:
    constraint_id: str
    description: str
    disposition: FatalDisposition
    evidence_refs: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "FatalConstraint":
        return cls(
            constraint_id=str(raw.get("constraint_id", "")).strip(),
            description=str(raw.get("description", "")).strip(),
            disposition=FatalDisposition(str(raw.get("disposition", "")).lower()),
            evidence_refs=tuple(str(v).strip() for v in raw.get("evidence_refs", [])),
        )


@dataclass(frozen=True)
class LifecycleControl:
    owner: str
    next_action: str
    resource_ceiling: str
    review_date: str
    revalidation_triggers: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LifecycleControl":
        return cls(
            owner=str(raw.get("owner", "")).strip(),
            next_action=str(raw.get("next_action", "")).strip(),
            resource_ceiling=str(raw.get("resource_ceiling", "")).strip(),
            review_date=str(raw.get("review_date", "")).strip(),
            revalidation_triggers=tuple(
                str(v).strip() for v in raw.get("revalidation_triggers", [])
            ),
        )


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    title: str
    geography: str
    infrastructure_class: str
    problem_statement: str
    evidence: tuple[EvidenceItem, ...]
    dimensions: dict[str, DimensionAssessment]
    gates: dict[str, GateAssessment]
    lifecycle: LifecycleControl
    fatal_constraints: tuple[FatalConstraint, ...] = ()
    known_limitations: tuple[str, ...] = ()
    analyst: str = ""
    assessment_date: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Opportunity":
        return cls(
            opportunity_id=str(raw.get("opportunity_id", "")).strip(),
            title=str(raw.get("title", "")).strip(),
            geography=str(raw.get("geography", "")).strip(),
            infrastructure_class=str(raw.get("infrastructure_class", "")).strip(),
            problem_statement=str(raw.get("problem_statement", "")).strip(),
            evidence=tuple(EvidenceItem.from_dict(v) for v in raw.get("evidence", [])),
            dimensions={
                str(k): DimensionAssessment.from_dict(v)
                for k, v in raw.get("dimensions", {}).items()
            },
            gates={
                str(k): GateAssessment.from_dict(v)
                for k, v in raw.get("gates", {}).items()
            },
            lifecycle=LifecycleControl.from_dict(raw.get("lifecycle", {})),
            fatal_constraints=tuple(
                FatalConstraint.from_dict(v) for v in raw.get("fatal_constraints", [])
            ),
            known_limitations=tuple(str(v).strip() for v in raw.get("known_limitations", [])),
            analyst=str(raw.get("analyst", "")).strip(),
            assessment_date=str(raw.get("assessment_date", "")).strip(),
        )


@dataclass(frozen=True)
class DimensionResult:
    key: str
    label: str
    weight: int
    score: float
    weighted_points: float
    rationale: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisResult:
    opportunity_id: str
    title: str
    methodology: str
    engine_version: str
    assessment_date: str
    score: float
    confidence: Confidence
    confidence_index: float
    provisional: bool
    recommendation: Decision
    recommendation_reason: str
    dimensions: tuple[DimensionResult, ...]
    gates: dict[str, GateAssessment]
    fatal_constraints: tuple[FatalConstraint, ...]
    evidence_counts: dict[str, int]
    facts: tuple[EvidenceItem, ...]
    inferences: tuple[EvidenceItem, ...]
    assumptions: tuple[EvidenceItem, ...]
    unknowns_or_disputes: tuple[EvidenceItem, ...]
    known_limitations: tuple[str, ...]
    lifecycle: LifecycleControl
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        def normalize(value: Any) -> Any:
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, tuple):
                return [normalize(v) for v in value]
            if isinstance(value, list):
                return [normalize(v) for v in value]
            if isinstance(value, dict):
                return {k: normalize(v) for k, v in value.items()}
            return value

        return normalize(asdict(self))


def valid_iso_date(value: str) -> bool:
    if not value:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True

