"""AIN-304 — Intelligence Gap Resolution.

Converts governed AIN-103 profile gaps into bounded collection requirements.
It does not acquire sources, infer missing facts, create findings, approve
evidence, or modify scorecards. Requirements describe what must be learned
next; downstream AIN-303.2/AIN-302 services remain responsible for acquisition
and evidence governance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any


@dataclass(frozen=True, slots=True)
class CollectionRequirement:
    requirement_id: str
    gap_key: str
    title: str
    objective: str
    priority: int
    decision_impact: str
    completion_condition: str
    preferred_source_class: str
    handoff_target: str = "AIN-303.2"

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "gap_key": self.gap_key,
            "title": self.title,
            "objective": self.objective,
            "priority": self.priority,
            "decision_impact": self.decision_impact,
            "completion_condition": self.completion_condition,
            "preferred_source_class": self.preferred_source_class,
            "handoff_target": self.handoff_target,
        }


@dataclass(frozen=True, slots=True)
class GapResolutionPlan:
    plan_id: str
    organization_id: str
    organization_name: str
    readiness_percent: float
    requirements: tuple[CollectionRequirement, ...]

    @property
    def integrity_hash(self) -> str:
        canonical = json.dumps(self.to_dict(include_integrity=False), sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self, *, include_integrity: bool = True) -> dict[str, Any]:
        payload = {
            "plan_id": self.plan_id,
            "organization_id": self.organization_id,
            "organization_name": self.organization_name,
            "readiness_percent": self.readiness_percent,
            "requirement_count": len(self.requirements),
            "requirements": [item.to_dict() for item in self.requirements],
        }
        if include_integrity:
            payload["integrity_hash"] = self.integrity_hash
        return payload


class IntelligenceGapResolutionService:
    """Create deterministic, evidence-bounded collection plans from AIN-103."""

    VERSION = "304.1"

    def __init__(self, profiles: Any) -> None:
        self.profiles = profiles

    def build_plan(self, organization_identifier: str) -> GapResolutionPlan:
        profile = self.profiles.export_payload(organization_identifier)
        org = profile["organization"]
        readiness = profile["readiness"]
        requirements: list[CollectionRequirement] = []

        def add(gap_key: str, title: str, objective: str, priority: int,
                impact: str, condition: str, source_class: str) -> None:
            requirements.append(CollectionRequirement(
                requirement_id=self._requirement_id(org["cof_organization_id"], gap_key),
                gap_key=gap_key,
                title=title,
                objective=objective,
                priority=priority,
                decision_impact=impact,
                completion_condition=condition,
                preferred_source_class=source_class,
            ))

        if not org.get("headquarters"):
            add("headquarters_missing", "Confirm headquarters",
                "Establish the organization's current headquarters from an authoritative public source.",
                40, "Improves organization identity and geographic context.",
                "A governed evidence record supports a headquarters value.",
                "Official organization source")

        if not profile["markets"]:
            add("market_link_missing", "Establish relevant commercial market",
                "Identify and support at least one market relevant to the organization's commercial context.",
                85, "Required by AIN-103 readiness and strategic-fit interpretation.",
                "At least one governed market link is supported by evidence.",
                "Official, regulatory, or authoritative industry source")

        contacts = profile["relationships"]["contact_count"]
        contact_target = getattr(self.profiles.policy, "contact_target", 2)
        if contacts < contact_target:
            add("contact_coverage_low", "Identify relevant decision contacts",
                f"Identify {contact_target - contacts} additional relevant leadership or decision contact(s).",
                55, "Improves relationship context and future Relationship Strength assessment.",
                f"At least {contact_target} relevant contacts are governed and linked to the organization.",
                "Official leadership or organization source")

        evidence_count = profile["evidence"]["count"]
        evidence_target = getattr(self.profiles.policy, "evidence_target", 5)
        if evidence_count < evidence_target:
            add("evidence_coverage_low", "Increase governed evidence coverage",
                f"Collect decision-relevant evidence until the profile contains at least {evidence_target} governed records.",
                75, "Raises the evidentiary basis available for scoring and executive review.",
                f"At least {evidence_target} governed evidence records are linked to the organization.",
                "Authoritative primary or high-quality secondary source")

        model_priorities = {
            "Organization Strategic Fit": 100,
            "Organizational Viability Score": 90,
            "Evidence Confidence Score": 80,
            "Relationship Strength Score": 65,
            "Commercial Confidence Index": 20,
        }
        for tile in profile["score_tiles"]:
            if tile["status"] != "Missing":
                continue
            model = tile["model"]
            key = model.lower().replace(" ", "_") + "_missing"
            if model == "Commercial Confidence Index":
                add(key, "Enable Commercial Confidence Index",
                    "Resolve prerequisite score-model gaps so CCI can be calculated from approved inputs.",
                    model_priorities[model], "Produces the composite commercial confidence state only after prerequisites exist.",
                    "An approved Commercial Confidence Index scorecard exists.",
                    "Derived from approved governed scorecards")
            else:
                add(key, f"Support {model}",
                    f"Collect the governed facts required to perform the {model} assessment; do not infer missing inputs.",
                    model_priorities[model], f"Directly resolves the missing {model} decision input.",
                    f"An approved {model} scorecard exists and is evidence-supported.",
                    "Sources appropriate to the score model's required criteria")

        requirements.sort(key=lambda item: (-item.priority, item.requirement_id))
        plan_id = self._plan_id(org["cof_organization_id"], readiness["percent"], requirements)
        return GapResolutionPlan(
            plan_id=plan_id,
            organization_id=org["cof_organization_id"],
            organization_name=org["display_name"],
            readiness_percent=float(readiness["percent"]),
            requirements=tuple(requirements),
        )

    @staticmethod
    def _requirement_id(organization_id: str, gap_key: str) -> str:
        digest = sha256(f"{organization_id}|{gap_key}".encode()).hexdigest()[:12]
        return f"CR-{digest}"

    @staticmethod
    def _plan_id(organization_id: str, readiness: float, requirements: list[CollectionRequirement]) -> str:
        payload = {
            "organization": organization_id,
            "readiness": readiness,
            "requirements": [item.requirement_id for item in requirements],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"IGR-{sha256(canonical.encode()).hexdigest()[:16]}"
