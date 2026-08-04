"""AIN-103 — AnchorInsight Organization Intelligence Profile Service.

Produces a stable, display-ready decision object from AIN-101 registry records
and AIN-102 scoring outputs. It contains no HTML and performs no raw SQL writes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .errors import ValidationError
from .scoring import ScoringDecisionService
from .service import CommercialIntelligenceRegistryService


@dataclass(frozen=True, slots=True)
class ProfilePolicy:
    stale_after_days: int = 90
    evidence_target: int = 5
    contact_target: int = 2
    required_score_models: tuple[str, ...] = (
        "Organization Strategic Fit",
        "Organizational Viability Score",
        "Evidence Confidence Score",
        "Relationship Strength Score",
        "Commercial Confidence Index",
    )


class OrganizationIntelligenceProfileService:
    """Read-model service for one-page organization intelligence profiles."""

    name = "Organization Intelligence Profile Service"
    version = "1.0.0"

    def __init__(
        self,
        registry: CommercialIntelligenceRegistryService,
        scoring: ScoringDecisionService | None = None,
        policy: ProfilePolicy | None = None,
    ) -> None:
        self.registry = registry
        self.scoring = scoring or ScoringDecisionService(registry)
        self.policy = policy or ProfilePolicy()

    def health(self) -> dict[str, Any]:
        registry_health = self.registry.health()
        scoring_health = self.scoring.health()
        healthy = (
            registry_health["status"] == "HEALTHY"
            and scoring_health["status"] == "HEALTHY"
        )
        return {
            "name": self.name,
            "version": self.version,
            "status": "HEALTHY" if healthy else "DEGRADED",
            "registry": registry_health,
            "scoring": scoring_health,
        }

    def build_profile(self, organization_identifier: str) -> dict[str, Any]:
        raw = self.registry.get_organization_profile(organization_identifier)
        organization = raw["organization"]
        latest_scores = self._latest_scorecards(raw["scorecards"])
        recommendation = self.scoring.recommendation_for_organization(
            organization_identifier
        )

        profile = {
            "profile_version": self.version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "organization": self._identity(organization),
            "decision": {
                **recommendation,
                "status": organization["cof_status"],
                "strategic_value": organization["strategic_value"],
                "priority": organization["priority"],
            },
            "score_tiles": self._score_tiles(latest_scores),
            "commercial_confidence": self._commercial_confidence(latest_scores),
            "markets": self._markets(raw["markets"]),
            "evidence": self._evidence_summary(raw["evidence"]),
            "relationships": {
                "contact_count": len(raw["contacts"]),
                "contacts": self._contacts(raw["contacts"]),
                "relationship_score": self._score_value(
                    latest_scores, "Relationship Strength Score"
                ),
            },
            "opportunities": self._opportunities(raw["opportunities"]),
            "actions": self._actions(raw["open_actions"]),
            "risks": self._risks(raw["risks"]),
            "assumptions": self._assumptions(raw["assumptions"]),
            "timeline": self._timeline(raw["lifecycle"]),
            "readiness": self._readiness(raw, latest_scores),
            "data_quality": self._data_quality(raw, latest_scores),
        }
        profile["headline"] = self._headline(profile)
        return profile

    def build_compact_card(self, organization_identifier: str) -> dict[str, Any]:
        profile = self.build_profile(organization_identifier)
        return {
            "cof_organization_id": profile["organization"]["cof_organization_id"],
            "name": profile["organization"]["display_name"],
            "sector": profile["organization"]["sector"],
            "role": profile["organization"]["role"],
            "decision": profile["decision"]["decision"],
            "confidence": profile["decision"].get("confidence"),
            "cci": profile["commercial_confidence"]["score"],
            "priority": profile["decision"]["priority"],
            "open_actions": len(profile["actions"]["items"]),
            "evidence_count": profile["evidence"]["count"],
            "readiness": profile["readiness"]["status"],
            "headline": profile["headline"],
        }

    def export_payload(self, organization_identifier: str) -> dict[str, Any]:
        """JSON-safe payload suitable for Flask, REST, or AOS-180."""
        return self.build_profile(organization_identifier)

    @staticmethod
    def _identity(record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "organization_id": record["organization_id"],
            "cof_organization_id": record["cof_organization_id"],
            "legal_name": record["legal_name"],
            "display_name": record["common_name"] or record["legal_name"],
            "industry": record["industry"],
            "sector": record["sector"],
            "role": record["role"],
            "website": record["website"],
            "headquarters": record["headquarters"],
            "relationship_stage": record["relationship_stage"],
            "owner": record["owner"],
            "status": record["status"],
            "last_reviewed_at": record["last_reviewed_at"],
            "next_review_at": record["next_review_at"],
        }

    @staticmethod
    def _latest_scorecards(
        scorecards: Sequence[Mapping[str, Any]]
    ) -> dict[str, Mapping[str, Any]]:
        latest: dict[str, Mapping[str, Any]] = {}
        for card in scorecards:
            if card["status"] not in {"Approved", "Superseded", "Expired"}:
                continue
            latest.setdefault(card["score_model"], card)
        return latest

    @staticmethod
    def _score_value(
        latest: Mapping[str, Mapping[str, Any]], model: str
    ) -> float | None:
        item = latest.get(model)
        return None if item is None else float(item["normalized_score"])

    def _score_tiles(
        self, latest: Mapping[str, Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        order = [
            "Organization Strategic Fit",
            "Organizational Viability Score",
            "Evidence Confidence Score",
            "Relationship Strength Score",
            "Commercial Confidence Index",
        ]
        tiles: list[dict[str, Any]] = []
        for model in order:
            item = latest.get(model)
            if item is None:
                tiles.append({
                    "model": model,
                    "score": None,
                    "decision": "Not Assessed",
                    "status": "Missing",
                    "scorecard_id": None,
                })
            else:
                tiles.append({
                    "model": model,
                    "score": float(item["normalized_score"]),
                    "decision": item["decision_outcome"],
                    "status": item["status"],
                    "scorecard_id": item["cof_scorecard_id"],
                    "assessed_at": item["assessment_date"],
                    "recommendation": item["recommendation"],
                })
        return tiles

    def _commercial_confidence(
        self, latest: Mapping[str, Mapping[str, Any]]
    ) -> dict[str, Any]:
        card = latest.get("Commercial Confidence Index")
        if card is None:
            return {
                "score": None,
                "decision": "Validate",
                "coverage": None,
                "status": "Not Calculated",
                "scorecard_id": None,
            }
        return {
            "score": float(card["normalized_score"]),
            "decision": card["decision_outcome"],
            "coverage": self._cci_coverage(card),
            "status": card["status"],
            "scorecard_id": card["cof_scorecard_id"],
            "recommendation": card["recommendation"],
            "assessed_at": card["assessment_date"],
        }

    @staticmethod
    def _cci_coverage(card: Mapping[str, Any]) -> float | None:
        try:
            criteria = __import__("json").loads(card["criterion_scores_json"])
            weights = {
                "Organization Strategic Fit": 0.25,
                "Organizational Viability Score": 0.20,
                "Evidence Confidence Score": 0.20,
                "Relationship Strength Score": 0.15,
                "Opportunity Score": 0.20,
            }
            return round(
                sum(weights[key] for key in criteria if key in weights) * 100, 2
            )
        except (TypeError, ValueError, KeyError):
            return None

    @staticmethod
    def _markets(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "cof_market_id": row["cof_market_id"],
                "name": row["name"],
                "relevance": row["relevance"],
                "market_role": row["market_role"],
                "priority": row["membership_priority"],
                "state": row["membership_state"],
            }
            for row in rows
        ]

    @staticmethod
    def _contacts(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "cof_contact_id": row["cof_contact_id"],
                "name": row["full_name"],
                "title": row["title"],
                "department": row["department"],
                "decision_role": row["decision_role"],
                "relationship_strength": row["relationship_strength"],
                "last_contact_at": row["last_contact_at"],
                "next_action": row["next_action"],
            }
            for row in rows
        ]

    @staticmethod
    def _opportunities(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        active = [
            row for row in rows
            if row["lifecycle_state"] not in {"Won", "Lost", "Closed"}
        ]
        return {
            "count": len(rows),
            "active_count": len(active),
            "items": [
                {
                    "cof_opportunity_id": row["cof_opportunity_id"],
                    "name": row["name"],
                    "type": row["opportunity_type"],
                    "state": row["lifecycle_state"],
                    "decision": row["decision_outcome"],
                    "estimated_value": row["estimated_value"],
                    "currency": row["currency"],
                    "next_action": row["next_action"],
                    "review_date": row["review_date"],
                }
                for row in rows
            ],
        }

    @staticmethod
    def _evidence_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        counts = {
            "Verified": 0,
            "Supported": 0,
            "Assumption": 0,
            "Unknown": 0,
            "Disputed": 0,
        }
        for row in rows:
            counts[row["classification"]] = counts.get(row["classification"], 0) + 1
        return {
            "count": len(rows),
            "classification_counts": counts,
            "items": [
                {
                    "cof_evidence_id": row["cof_evidence_id"],
                    "assertion": row["assertion"],
                    "classification": row["classification"],
                    "confidence": row["confidence"],
                    "source_title": row["source_title"],
                    "publisher": row["publisher"],
                    "url": row["url"],
                    "captured_at": row["captured_at"],
                    "link_type": row["link_type"],
                    "relevance": row["relevance"],
                }
                for row in rows
            ],
        }

    @staticmethod
    def _actions(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "count": len(rows),
            "items": [
                {
                    "cof_action_id": row["cof_action_id"],
                    "description": row["description"],
                    "owner": row["owner"],
                    "priority": row["priority"],
                    "due_at": row["due_at"],
                    "status": row["status"],
                }
                for row in rows
            ],
        }

    @staticmethod
    def _risks(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "count": len(rows),
            "items": [
                {
                    "cof_risk_id": row["cof_risk_id"],
                    "title": row["title"],
                    "category": row["category"],
                    "likelihood": row["likelihood"],
                    "impact": row["impact"],
                    "risk_score": row["risk_score"],
                    "status": row["status"],
                    "mitigation": row["mitigation"],
                    "review_date": row["review_date"],
                }
                for row in rows
            ],
        }

    @staticmethod
    def _assumptions(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "count": len(rows),
            "items": [
                {
                    "cof_assumption_id": row["cof_assumption_id"],
                    "statement": row["statement"],
                    "status": row["status"],
                    "confidence": row["confidence"],
                    "review_date": row["review_date"],
                    "resolution": row["resolution"],
                }
                for row in rows
            ],
        }

    @staticmethod
    def _timeline(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "cof_lifecycle_event_id": row["cof_lifecycle_event_id"],
                "event_type": row["event_type"],
                "previous_state": row["previous_state"],
                "new_state": row["new_state"],
                "reason": row["reason"],
                "actor": row["actor"],
                "occurred_at": row["occurred_at"],
            }
            for row in rows[:25]
        ]

    def _readiness(
        self,
        raw: Mapping[str, Any],
        latest: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Any]:
        checks = {
            "market_linked": len(raw["markets"]) > 0,
            "strategic_fit_scored": "Organization Strategic Fit" in latest,
            "viability_scored": "Organizational Viability Score" in latest,
            "evidence_scored": "Evidence Confidence Score" in latest,
            "relationship_scored": "Relationship Strength Score" in latest,
            "cci_calculated": "Commercial Confidence Index" in latest,
            "evidence_present": len(raw["evidence"]) > 0,
            "next_action_present": len(raw["open_actions"]) > 0,
        }
        passed = sum(checks.values())
        percent = round(passed / len(checks) * 100, 2)
        status = "Ready" if percent == 100 else "Developing" if percent >= 60 else "Incomplete"
        return {
            "status": status,
            "percent": percent,
            "checks": checks,
            "missing": [name for name, ok in checks.items() if not ok],
        }

    def _data_quality(
        self,
        raw: Mapping[str, Any],
        latest: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Any]:
        organization = raw["organization"]
        warnings: list[str] = []
        if not organization["website"]:
            warnings.append("Website is missing.")
        if not organization["headquarters"]:
            warnings.append("Headquarters is missing.")
        if len(raw["contacts"]) < self.policy.contact_target:
            warnings.append(
                f"Only {len(raw['contacts'])} contacts are recorded; target is "
                f"{self.policy.contact_target}."
            )
        if len(raw["evidence"]) < self.policy.evidence_target:
            warnings.append(
                f"Only {len(raw['evidence'])} evidence records are linked; target is "
                f"{self.policy.evidence_target}."
            )
        missing_models = [
            model for model in self.policy.required_score_models if model not in latest
        ]
        if missing_models:
            warnings.append("Missing score models: " + ", ".join(missing_models) + ".")
        return {
            "status": "Complete" if not warnings else "Attention Required",
            "warning_count": len(warnings),
            "warnings": warnings,
        }

    @staticmethod
    def _headline(profile: Mapping[str, Any]) -> str:
        name = profile["organization"]["display_name"]
        decision = profile["decision"]["decision"]
        cci = profile["commercial_confidence"]["score"]
        action = profile["decision"]["next_action"]
        score_text = "not yet calculated" if cci is None else f"{cci:.2f}"
        return (
            f"{name}: {decision} with Commercial Confidence {score_text}. "
            f"Next justified action: {action}"
        )
