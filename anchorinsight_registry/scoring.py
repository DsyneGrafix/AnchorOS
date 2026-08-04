"""AIN-102 — AnchorInsight Scoring and Decision Service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .errors import NotFoundError, ValidationError
from .service import CommercialIntelligenceRegistryService


@dataclass(frozen=True, slots=True)
class Criterion:
    name: str
    maximum: float
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class ScoreModel:
    model_id: str
    version: str
    subject_type: str
    criteria: tuple[Criterion, ...]
    decision_bands: tuple[tuple[float, str], ...]

    @property
    def maximum_score(self) -> float:
        return sum(item.maximum * item.weight for item in self.criteria)


class ScoringDecisionService:
    """Deterministic scoring and recommendation layer for AnchorInsight."""

    name = "Scoring and Decision Service"
    version = "1.0.0"

    MODELS: dict[str, ScoreModel] = {
        "organization_fit": ScoreModel(
            model_id="Organization Strategic Fit",
            version="1.0",
            subject_type="Organization",
            criteria=(
                Criterion("ICP Fit", 5),
                Criterion("Strategic Importance", 5),
                Criterion("Problem Relevance", 5),
                Criterion("Pilot Suitability", 5),
                Criterion("Long-Term Value", 5),
            ),
            decision_bands=((85, "Pursue"), (70, "Validate"), (50, "Monitor"), (30, "Hold"), (0, "Reject")),
        ),
        "organizational_viability": ScoreModel(
            model_id="Organizational Viability Score",
            version="1.0",
            subject_type="Organization",
            criteria=(
                Criterion("Financial Stability", 5),
                Criterion("Market Stability", 5),
                Criterion("Strategic Direction", 5),
                Criterion("Operational Continuity", 5),
                Criterion("Organizational Risk", 5),
            ),
            decision_bands=((85, "Pursue"), (70, "Validate"), (50, "Monitor"), (30, "Hold"), (0, "Reject")),
        ),
        "evidence_confidence": ScoreModel(
            model_id="Evidence Confidence Score",
            version="1.0",
            subject_type="Organization",
            criteria=(
                Criterion("Quality", 5),
                Criterion("Authority", 5),
                Criterion("Recency", 5),
                Criterion("Completeness", 5),
                Criterion("Corroboration", 5),
            ),
            decision_bands=((85, "Verified"), (70, "Supported"), (50, "Provisional"), (30, "Weak"), (0, "Insufficient")),
        ),
        "relationship_strength": ScoreModel(
            model_id="Relationship Strength Score",
            version="1.0",
            subject_type="Organization",
            criteria=(
                Criterion("Access", 4),
                Criterion("Trust", 4),
                Criterion("Influence", 4),
                Criterion("Engagement", 4),
                Criterion("Reciprocity", 4),
            ),
            decision_bands=((85, "Strong"), (70, "Established"), (50, "Developing"), (30, "Weak"), (0, "None")),
        ),
        "opportunity": ScoreModel(
            model_id="Opportunity Score",
            version="1.0",
            subject_type="Opportunity",
            criteria=(
                Criterion("Customer Need", 5),
                Criterion("Buyer Authority", 5),
                Criterion("Budget Readiness", 5),
                Criterion("Strategic Alignment", 5),
                Criterion("Technical Fit", 5),
                Criterion("Competitive Position", 5),
                Criterion("Delivery Readiness", 5),
                Criterion("Long-Term Value", 5),
            ),
            decision_bands=((85, "Pursue"), (70, "Validate"), (50, "Monitor"), (30, "Hold"), (0, "Reject")),
        ),
    }

    CCI_COMPONENTS = {
        "Organization Strategic Fit": 0.25,
        "Organizational Viability Score": 0.20,
        "Evidence Confidence Score": 0.20,
        "Relationship Strength Score": 0.15,
        "Opportunity Score": 0.20,
    }

    def __init__(self, registry: CommercialIntelligenceRegistryService) -> None:
        self.registry = registry

    def health(self) -> dict[str, Any]:
        registry_health = self.registry.health()
        return {
            "name": self.name,
            "version": self.version,
            "status": "HEALTHY" if registry_health["status"] == "HEALTHY" else "DEGRADED",
            "models": sorted(self.MODELS),
            "registry": registry_health,
        }

    def list_models(self) -> list[dict[str, Any]]:
        return [
            {
                "key": key,
                "model_id": model.model_id,
                "version": model.version,
                "subject_type": model.subject_type,
                "maximum_score": model.maximum_score,
                "criteria": [
                    {"name": c.name, "maximum": c.maximum, "weight": c.weight}
                    for c in model.criteria
                ],
            }
            for key, model in sorted(self.MODELS.items())
        ]

    def evaluate(
        self,
        *,
        model_key: str,
        subject_identifier: str,
        criterion_scores: Mapping[str, float],
        reviewer: str,
        actor: str,
        evidence_ids: Sequence[str] = (),
        recommendation: str | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        model = self._model(model_key)
        normalized_scores = self._validate_scores(model, criterion_scores)
        weighted_total = sum(
            normalized_scores[c.name] * c.weight for c in model.criteria
        )
        maximum = model.maximum_score
        normalized = round(weighted_total / maximum * 100, 2)
        decision = self._decision(model, normalized)
        result = {
            "model_key": model_key,
            "model_id": model.model_id,
            "model_version": model.version,
            "subject_type": model.subject_type,
            "subject_identifier": subject_identifier,
            "criterion_scores": normalized_scores,
            "maximum_score": maximum,
            "total_score": weighted_total,
            "normalized_score": normalized,
            "decision": decision,
            "recommendation": recommendation or self._default_recommendation(decision),
        }
        if persist:
            scorecard = self.registry.create_scorecard(
                subject_type=model.subject_type,
                subject_identifier=subject_identifier,
                score_model=model.model_id,
                model_version=model.version,
                criterion_scores=normalized_scores,
                maximum_score=maximum,
                decision_outcome=decision,
                reviewer=reviewer,
                actor=actor,
                recommendation=result["recommendation"],
                evidence_ids=evidence_ids,
            )
            result["scorecard"] = scorecard
        return result

    def calculate_cci(
        self,
        *,
        organization_identifier: str,
        opportunity_identifier: str | None = None,
        persist: bool = True,
        reviewer: str,
        actor: str,
    ) -> dict[str, Any]:
        profile = self.registry.get_organization_profile(organization_identifier)
        latest = self._latest_scores(profile["scorecards"])

        components: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        weighted_sum = 0.0
        weight_used = 0.0

        for model_id, weight in self.CCI_COMPONENTS.items():
            item = latest.get(model_id)
            if item is None:
                missing.append(model_id)
                continue
            components[model_id] = {
                "score": item["normalized_score"],
                "weight": weight,
                "contribution": round(item["normalized_score"] * weight, 2),
                "scorecard_id": item["cof_scorecard_id"],
            }
            weighted_sum += item["normalized_score"] * weight
            weight_used += weight

        if weight_used == 0:
            raise ValidationError("CCI cannot be calculated without component scorecards")

        normalized = round(weighted_sum / weight_used, 2)
        evidence_coverage = round(weight_used * 100, 2)
        decision = self._cci_decision(normalized, evidence_coverage)
        result = {
            "organization": profile["organization"]["cof_organization_id"],
            "normalized_score": normalized,
            "coverage_percent": evidence_coverage,
            "decision": decision,
            "components": components,
            "missing_components": missing,
            "recommendation": self._cci_recommendation(decision, missing),
        }

        if persist:
            criterion_scores = {
                key: value["score"] * value["weight"]
                for key, value in components.items()
            }
            max_score = sum(100 * value["weight"] for value in components.values())
            scorecard = self.registry.create_scorecard(
                subject_type="Organization",
                subject_identifier=organization_identifier,
                score_model="Commercial Confidence Index",
                model_version="1.0",
                criterion_scores=criterion_scores,
                maximum_score=max_score,
                decision_outcome=decision,
                reviewer=reviewer,
                actor=actor,
                recommendation=result["recommendation"],
            )
            result["scorecard"] = scorecard
        return result

    def recommendation_for_organization(self, organization_identifier: str) -> dict[str, Any]:
        profile = self.registry.get_organization_profile(organization_identifier)
        latest = self._latest_scores(profile["scorecards"])
        cci = latest.get("Commercial Confidence Index")
        if cci:
            decision = cci["decision_outcome"]
            score = cci["normalized_score"]
            basis = cci["cof_scorecard_id"]
        else:
            fit = latest.get("Organization Strategic Fit")
            if fit is None:
                return {
                    "decision": "Validate",
                    "confidence": "Low",
                    "basis": "No approved strategic scorecard",
                    "next_action": "Complete the Organization Strategic Fit scorecard.",
                }
            decision = fit["decision_outcome"]
            score = fit["normalized_score"]
            basis = fit["cof_scorecard_id"]

        action = profile["open_actions"][0]["description"] if profile["open_actions"] else self._default_recommendation(decision)
        return {
            "decision": decision,
            "confidence": "High" if score >= 85 else "Moderate" if score >= 70 else "Low",
            "score": score,
            "basis": basis,
            "next_action": action,
        }

    def _model(self, key: str) -> ScoreModel:
        try:
            return self.MODELS[key]
        except KeyError as exc:
            raise ValidationError(f"Unknown score model: {key}") from exc

    @staticmethod
    def _validate_scores(model: ScoreModel, supplied: Mapping[str, float]) -> dict[str, float]:
        expected = {c.name: c for c in model.criteria}
        missing = [name for name in expected if name not in supplied]
        unknown = [name for name in supplied if name not in expected]
        if missing:
            raise ValidationError(f"Missing criteria: {', '.join(missing)}")
        if unknown:
            raise ValidationError(f"Unknown criteria: {', '.join(unknown)}")
        normalized: dict[str, float] = {}
        for name, value in supplied.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"{name} must be numeric") from exc
            if numeric < 0 or numeric > expected[name].maximum:
                raise ValidationError(
                    f"{name} must be between 0 and {expected[name].maximum}"
                )
            normalized[name] = numeric
        return normalized

    @staticmethod
    def _decision(model: ScoreModel, normalized: float) -> str:
        for threshold, decision in model.decision_bands:
            if normalized >= threshold:
                return decision
        return model.decision_bands[-1][1]

    @staticmethod
    def _latest_scores(scorecards: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
        latest: dict[str, Mapping[str, Any]] = {}
        for item in scorecards:
            if item["status"] not in {"Approved", "Superseded", "Expired"}:
                continue
            latest.setdefault(item["score_model"], item)
        return latest

    @staticmethod
    def _default_recommendation(decision: str) -> str:
        return {
            "Pursue": "Advance to the next bounded commercial action.",
            "Validate": "Collect missing evidence and validate the next decision gate.",
            "Monitor": "Maintain awareness and reassess when material conditions change.",
            "Hold": "Pause additional investment until blocking conditions are resolved.",
            "Reject": "Close the route and preserve the supporting rationale.",
            "Verified": "Evidence is sufficient for the current bounded claim.",
            "Supported": "Use with stated limitations and continue corroboration.",
            "Provisional": "Do not rely on this score without additional verification.",
            "Strong": "Use the relationship actively while preserving reciprocity.",
            "Established": "Continue deliberate relationship development.",
            "Developing": "Increase relevant, reciprocal engagement.",
        }.get(decision, "Review the result and determine the next justified action.")

    @staticmethod
    def _cci_decision(score: float, coverage: float) -> str:
        if coverage < 60:
            return "Validate"
        if score >= 85:
            return "Pursue"
        if score >= 70:
            return "Validate"
        if score >= 50:
            return "Monitor"
        if score >= 30:
            return "Hold"
        return "Reject"

    @staticmethod
    def _cci_recommendation(decision: str, missing: Sequence[str]) -> str:
        missing_text = ""
        if missing:
            missing_text = " Complete missing components: " + ", ".join(missing) + "."
        base = ScoringDecisionService._default_recommendation(decision)
        return base + missing_text
