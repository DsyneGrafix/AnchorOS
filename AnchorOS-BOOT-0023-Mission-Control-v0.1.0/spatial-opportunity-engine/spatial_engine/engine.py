"""Deterministic S.P.A.T.I.A.L. scoring, gate, and recommendation engine."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from .models import (
    AnalysisResult,
    Confidence,
    Decision,
    DimensionResult,
    EvidenceItem,
    EvidenceState,
    FatalDisposition,
    GateStatus,
    Opportunity,
    valid_iso_date,
)


ENGINE_VERSION = "0.1.0"
METHODOLOGY = "SIO-001 v0.1"

DIMENSIONS: dict[str, tuple[str, int]] = {
    "problem_evidence": ("Problem evidence and consequence", 15),
    "authority_clarity": ("Customer, actor, and authority clarity", 15),
    "technical_fit": ("Technical and temporal fit", 15),
    "funding_path": ("Funding and procurement path", 15),
    "strategic_alignment": ("Strategic alignment", 15),
    "differentiated_advantage": ("Differentiated advantage", 10),
    "delivery_readiness": ("Delivery readiness", 10),
    "risk_position": ("Risk and uncertainty position", 5),
}

GATES: dict[str, str] = {
    "S": "Scope & Signals",
    "P": "Pressure & Problem",
    "A1": "Assets, Actors & Authority",
    "T": "Technical & Temporal Fit",
    "I": "Investment & Implementation Path",
    "A2": "Alignment & Advantage",
}

EVIDENCE_CONFIDENCE = {
    EvidenceState.VERIFIED: 1.0,
    EvidenceState.SUPPORTED: 0.75,
    EvidenceState.ASSUMPTION: 0.35,
    EvidenceState.UNKNOWN: 0.0,
    EvidenceState.DISPUTED: 0.15,
}


class InputError(ValueError):
    """Raised when an opportunity record violates the engine contract."""


class SpatialEngine:
    """Evaluate one opportunity using SIO-001's evidence, gates, and score."""

    def analyze(self, raw: dict[str, Any] | Opportunity) -> AnalysisResult:
        try:
            opportunity = raw if isinstance(raw, Opportunity) else Opportunity.from_dict(raw)
        except (TypeError, ValueError) as exc:
            raise InputError(f"Invalid opportunity value: {exc}") from exc

        self._validate(opportunity)
        dimension_results = self._score_dimensions(opportunity)
        score = round(sum(v.weighted_points for v in dimension_results), 2)
        confidence, confidence_index, evidence_counts = self._confidence(opportunity.evidence)
        lifecycle_gate = self._lifecycle_gate(opportunity)
        gates = dict(opportunity.gates)
        gates["L"] = lifecycle_gate

        provisional = (
            confidence is not Confidence.HIGH
            or any(v.status is GateStatus.PROVISIONAL for v in gates.values())
        )
        recommendation, reason = self._recommend(
            score=score,
            confidence=confidence,
            gates=gates,
            fatal_constraints=opportunity.fatal_constraints,
        )

        warnings = self._warnings(opportunity, gates, confidence)
        facts = tuple(v for v in opportunity.evidence if v.state is EvidenceState.VERIFIED)
        inferences = tuple(v for v in opportunity.evidence if v.state is EvidenceState.SUPPORTED)
        assumptions = tuple(v for v in opportunity.evidence if v.state is EvidenceState.ASSUMPTION)
        unknowns = tuple(
            v for v in opportunity.evidence
            if v.state in (EvidenceState.UNKNOWN, EvidenceState.DISPUTED)
        )

        return AnalysisResult(
            opportunity_id=opportunity.opportunity_id,
            title=opportunity.title,
            methodology=METHODOLOGY,
            engine_version=ENGINE_VERSION,
            assessment_date=opportunity.assessment_date or date.today().isoformat(),
            score=score,
            confidence=confidence,
            confidence_index=confidence_index,
            provisional=provisional,
            recommendation=recommendation,
            recommendation_reason=reason,
            dimensions=dimension_results,
            gates=gates,
            fatal_constraints=opportunity.fatal_constraints,
            evidence_counts=evidence_counts,
            facts=facts,
            inferences=inferences,
            assumptions=assumptions,
            unknowns_or_disputes=unknowns,
            known_limitations=opportunity.known_limitations,
            lifecycle=opportunity.lifecycle,
            warnings=warnings,
        )

    def _validate(self, opportunity: Opportunity) -> None:
        errors: list[str] = []
        for field_name in (
            "opportunity_id",
            "title",
            "geography",
            "infrastructure_class",
            "problem_statement",
        ):
            if not getattr(opportunity, field_name):
                errors.append(f"{field_name} is required")

        if opportunity.assessment_date and not valid_iso_date(opportunity.assessment_date):
            errors.append("assessment_date must use YYYY-MM-DD")

        evidence_ids = [v.evidence_id for v in opportunity.evidence]
        if not evidence_ids:
            errors.append("at least one evidence item is required")
        if any(not v for v in evidence_ids):
            errors.append("every evidence item requires evidence_id")
        duplicates = sorted(k for k, count in Counter(evidence_ids).items() if count > 1)
        if duplicates:
            errors.append(f"duplicate evidence IDs: {', '.join(duplicates)}")
        for item in opportunity.evidence:
            if not item.claim:
                errors.append(f"evidence {item.evidence_id or '<blank>'} requires a claim")
            if item.state is EvidenceState.VERIFIED and not item.source:
                errors.append(f"verified evidence {item.evidence_id} requires a source")
            for date_name in ("source_date", "retrieved_date"):
                value = getattr(item, date_name)
                if value and not valid_iso_date(value):
                    errors.append(
                        f"evidence {item.evidence_id} {date_name} must use YYYY-MM-DD"
                    )

        missing_dimensions = sorted(set(DIMENSIONS) - set(opportunity.dimensions))
        extra_dimensions = sorted(set(opportunity.dimensions) - set(DIMENSIONS))
        if missing_dimensions:
            errors.append(f"missing dimensions: {', '.join(missing_dimensions)}")
        if extra_dimensions:
            errors.append(f"unknown dimensions: {', '.join(extra_dimensions)}")
        for key, item in opportunity.dimensions.items():
            if not 0 <= item.score <= 5:
                errors.append(f"dimension {key} score must be between 0 and 5")
            if not item.rationale:
                errors.append(f"dimension {key} requires a rationale")

        missing_gates = sorted(set(GATES) - set(opportunity.gates))
        extra_gates = sorted(set(opportunity.gates) - set(GATES))
        if missing_gates:
            errors.append(f"missing gates: {', '.join(missing_gates)}")
        if extra_gates:
            errors.append(f"unknown gates: {', '.join(extra_gates)}")
        for key, gate in opportunity.gates.items():
            if not gate.rationale:
                errors.append(f"gate {key} requires a rationale")

        known_refs = set(evidence_ids)
        all_refs: list[tuple[str, tuple[str, ...]]] = []
        all_refs.extend((f"dimension {k}", v.evidence_refs) for k, v in opportunity.dimensions.items())
        all_refs.extend((f"gate {k}", v.evidence_refs) for k, v in opportunity.gates.items())
        all_refs.extend(
            (f"fatal constraint {v.constraint_id}", v.evidence_refs)
            for v in opportunity.fatal_constraints
        )
        for owner, refs in all_refs:
            missing = sorted(set(refs) - known_refs)
            if missing:
                errors.append(f"{owner} references unknown evidence: {', '.join(missing)}")

        for constraint in opportunity.fatal_constraints:
            if not constraint.constraint_id or not constraint.description:
                errors.append("fatal constraints require constraint_id and description")

        if errors:
            raise InputError("; ".join(errors))

    def _score_dimensions(self, opportunity: Opportunity) -> tuple[DimensionResult, ...]:
        results: list[DimensionResult] = []
        for key, (label, weight) in DIMENSIONS.items():
            item = opportunity.dimensions[key]
            points = round((item.score / 5.0) * weight, 2)
            results.append(
                DimensionResult(
                    key=key,
                    label=label,
                    weight=weight,
                    score=item.score,
                    weighted_points=points,
                    rationale=item.rationale,
                    evidence_refs=item.evidence_refs,
                )
            )
        return tuple(results)

    def _confidence(
        self, evidence: tuple[EvidenceItem, ...]
    ) -> tuple[Confidence, float, dict[str, int]]:
        material = [v for v in evidence if v.material]
        counts = Counter(v.state.value for v in evidence)
        count_record = {key: counts.get(key, 0) for key in ("V", "S", "A", "U", "D")}
        if not material:
            return Confidence.LOW, 0.0, count_record

        index = round(
            sum(EVIDENCE_CONFIDENCE[v.state] for v in material) / len(material), 3
        )
        has_weak = any(v.state in (EvidenceState.UNKNOWN, EvidenceState.DISPUTED) for v in material)
        if index >= 0.8 and not has_weak:
            confidence = Confidence.HIGH
        elif index >= 0.5:
            confidence = Confidence.MODERATE
        else:
            confidence = Confidence.LOW
        return confidence, index, count_record

    def _lifecycle_gate(self, opportunity: Opportunity):
        from .models import GateAssessment

        lifecycle = opportunity.lifecycle
        missing: list[str] = []
        if not lifecycle.owner:
            missing.append("owner")
        if not lifecycle.next_action:
            missing.append("next_action")
        if not lifecycle.resource_ceiling:
            missing.append("resource_ceiling")
        if not valid_iso_date(lifecycle.review_date):
            missing.append("valid review_date")
        else:
            assessment = date.fromisoformat(opportunity.assessment_date) if opportunity.assessment_date else date.today()
            if date.fromisoformat(lifecycle.review_date) <= assessment:
                missing.append("review_date later than assessment_date")

        if missing:
            return GateAssessment(
                status=GateStatus.FAIL,
                rationale="Missing lifecycle controls: " + ", ".join(missing),
            )
        return GateAssessment(
            status=GateStatus.PASS,
            rationale="Owner, next action, resource ceiling, and review date are defined.",
        )

    def _recommend(self, score, confidence, gates, fatal_constraints):
        if any(v.disposition is FatalDisposition.REJECT for v in fatal_constraints):
            return Decision.REJECT, "A fatal reject constraint overrides the numeric score."
        if any(v.disposition is FatalDisposition.HOLD for v in fatal_constraints):
            return Decision.HOLD, "A fatal hold constraint overrides the numeric score."
        failed = [k for k, v in gates.items() if v.status is GateStatus.FAIL]
        if failed:
            return Decision.HOLD, f"Mandatory gate failure ({', '.join(failed)}) overrides the numeric score."

        provisional = [k for k, v in gates.items() if v.status is GateStatus.PROVISIONAL]
        if score >= 80:
            if confidence is Confidence.HIGH and not provisional:
                return Decision.PURSUE, "High score, high evidence confidence, and all gates passed."
            return Decision.VALIDATE, "The score supports pursuit, but evidence or gate confidence remains provisional."
        if score >= 65:
            return Decision.VALIDATE, "Promising opportunity with material validation work remaining."
        if score >= 45:
            return Decision.MONITOR, "A real signal exists, but the opportunity is not ready for pursuit resources."
        if score >= 25:
            return Decision.HOLD, "Current evidence and fit do not justify active pursuit."
        return Decision.REJECT, "The opportunity lacks a credible current path."

    def _warnings(self, opportunity, gates, confidence) -> tuple[str, ...]:
        warnings: list[str] = []
        unreferenced = sorted(
            v.evidence_id
            for v in opportunity.evidence
            if v.evidence_id not in {
                ref
                for assessment in list(opportunity.dimensions.values()) + list(opportunity.gates.values())
                for ref in assessment.evidence_refs
            }
        )
        if unreferenced:
            warnings.append("Evidence not referenced by a dimension or gate: " + ", ".join(unreferenced))
        if confidence is Confidence.LOW:
            warnings.append("Low evidence confidence: recommendation must be treated as provisional.")
        if any(v.status is GateStatus.PROVISIONAL for v in gates.values()):
            warnings.append("One or more mandatory gates remain provisional.")
        if not opportunity.lifecycle.revalidation_triggers:
            warnings.append("No explicit revalidation triggers were supplied.")
        return tuple(warnings)
