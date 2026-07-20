"""Deterministic adapter between AnchorIntel records and the S.P.A.T.I.A.L. engine.

The scoring engine remains an independent, unchanged package.  This module makes
the application-to-engine mapping explicit and replayable.  It deliberately uses
conservative values when the bounded Knowledge Module does not cover a required
S.P.A.T.I.A.L. dimension.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from spatial_engine.engine import ENGINE_VERSION


ADAPTER_VERSION = "1.0.0"


def _active_evidence_ids(evidence: list[dict[str, Any]]) -> list[str]:
    return sorted(str(item["evidence_id"]) for item in evidence)


def _finding(review: dict[str, Any], question_id: str) -> dict[str, Any]:
    for item in review.get("output", {}).get("findings", []):
        if item.get("question_id") == question_id:
            return item
    return {}


def _has_terms(evidence: list[dict[str, Any]], terms: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for item in evidence:
        text = " ".join(
            str(item.get(field, ""))
            for field in ("title", "description", "claim", "notes", "source")
        ).lower()
        if any(term in text for term in terms):
            matches.append(str(item["evidence_id"]))
    return sorted(matches)


def _dimension(
    score: float, rationale: str, evidence_refs: list[str] | None = None
) -> dict[str, Any]:
    return {
        "score": score,
        "rationale": rationale,
        "evidence_refs": sorted(evidence_refs or []),
    }


def _gate(
    status: str, rationale: str, evidence_refs: list[str] | None = None
) -> dict[str, Any]:
    return {
        "status": status,
        "rationale": rationale,
        "evidence_refs": sorted(evidence_refs or []),
    }


def _stable_dates(
    opportunity: dict[str, Any], module: dict[str, Any]
) -> tuple[str, str]:
    raw_assessment = str(opportunity.get("assessment_date", "")).strip()
    try:
        assessment = date.fromisoformat(raw_assessment)
    except ValueError:
        assessment = date.fromisoformat(str(module["effective_date"]))
    raw_review = str(
        opportunity.get("lifecycle", {}).get("review_date")
        or module.get("review_date", "")
    ).strip()
    try:
        review = date.fromisoformat(raw_review)
    except ValueError:
        review = assessment + timedelta(days=180)
    if review <= assessment:
        review = assessment + timedelta(days=180)
    return assessment.isoformat(), review.isoformat()


def build_engine_input(
    opportunity: dict[str, Any],
    evidence: list[dict[str, Any]],
    review: dict[str, Any],
    module: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the exact engine payload and a human-readable derivation record."""

    evidence_ids = _active_evidence_ids(evidence)
    organization = str(opportunity.get("organization", "")).strip()
    infrastructure_class = str(opportunity.get("infrastructure_class", "")).strip()
    problem_statement = str(
        opportunity.get("problem_statement") or opportunity.get("description", "")
    ).strip()
    strategic_text = " ".join(
        str(opportunity.get(field, ""))
        for field in ("title", "description", "problem_statement")
    ).lower()
    funding_refs = _has_terms(
        evidence,
        ("funding", "budget", "procurement", "capital plan", "solicitation"),
    )
    strong_funding_refs = sorted(
        item["evidence_id"]
        for item in evidence
        if item["evidence_id"] in funding_refs
        and str(item.get("state", "")).upper() in {"S", "V"}
    )
    output = review.get("output", {})
    unknown_count = len(output.get("unknowns", []))
    risk_count = len(output.get("risks", []))
    missing_count = len(output.get("missing_evidence", []))
    risk_score = max(0.5, round(3.0 - 0.25 * (unknown_count + risk_count + missing_count), 1))

    persisted_dimensions = opportunity.get("dimensions")
    if isinstance(persisted_dimensions, dict) and len(persisted_dimensions) == 8:
        dimensions = persisted_dimensions
        dimension_basis = "Persisted opportunity dimension assessments"
    else:
        dimensions = {
            "problem_evidence": _dimension(
                1.5 if evidence_ids and problem_statement else 0.5,
                "Adapter-derived: a problem statement and active evidence exist, but the geographic Knowledge Module does not independently establish the operational problem or consequence.",
                evidence_ids,
            ),
            "authority_clarity": _dimension(
                2.0 if organization else 0.5,
                "Adapter-derived: the organization is named, but the current review does not establish sponsor, buyer, budget, procurement, or approval authority.",
                _finding(review, "FL-Q03").get("evidence_ids", []),
            ),
            "technical_fit": _dimension(
                2.0 if infrastructure_class else 0.5,
                "Adapter-derived: an infrastructure class is identified, while requirements, assets, dependencies, and implementation constraints remain unverified.",
                _finding(review, "FL-Q02").get("evidence_ids", []),
            ),
            "funding_path": _dimension(
                2.5 if strong_funding_refs else 0.5,
                "Adapter-derived: supported funding or procurement evidence is present."
                if strong_funding_refs
                else "Adapter-derived conservative default: the bounded inputs do not establish a supported funding, procurement, or implementation path.",
                strong_funding_refs,
            ),
            "strategic_alignment": _dimension(
                3.0 if "anchorintel" in strategic_text else 1.5,
                "Adapter-derived: the opportunity explicitly concerns an AnchorIntel deployment; customer intent and a bounded engagement remain unverified."
                if "anchorintel" in strategic_text
                else "Adapter-derived conservative default: strategic alignment is not explicitly established in the persisted inputs.",
                evidence_ids,
            ),
            "differentiated_advantage": _dimension(
                1.5,
                "Adapter-derived conservative default: the current geographic review does not test competitive differentiation or buyer-relevant advantage.",
                [],
            ),
            "delivery_readiness": _dimension(
                1.0,
                "Adapter-derived conservative default: delivery team, commercial scope, authorization, resources, and implementation plan are not established by the current review.",
                [],
            ),
            "risk_position": _dimension(
                risk_score,
                f"Adapter-derived from the bounded review trace: {unknown_count} unknown(s), {risk_count} risk(s), and {missing_count} missing-evidence item(s) remain recorded.",
                evidence_ids,
            ),
        }
        dimension_basis = f"AnchorIntel deterministic adapter v{ADAPTER_VERSION}"

    persisted_gates = opportunity.get("gates")
    if isinstance(persisted_gates, dict) and len(persisted_gates) == 6:
        gates = persisted_gates
        gate_basis = "Persisted opportunity gate assessments"
    else:
        geo_disposition = str(_finding(review, "FL-Q01").get("disposition", "Unknown"))
        gates = {
            "S": _gate(
                "pass" if infrastructure_class and geo_disposition in {"Supported", "Partially Supported"} else "fail",
                "The geography and infrastructure class are bounded at opportunity-review level; this is not independent location verification."
                if infrastructure_class
                else "The opportunity scope or infrastructure signal is not sufficiently bounded.",
                _finding(review, "FL-Q01").get("evidence_ids", []),
            ),
            "P": _gate(
                "provisional" if problem_statement and evidence_ids else "fail",
                "A persisted problem statement and evidence trace exist, but measured pressure and consequence are not independently established."
                if problem_statement and evidence_ids
                else "A supported problem and consequence are not established.",
                evidence_ids,
            ),
            "A1": _gate(
                "provisional" if organization else "fail",
                "The organization is named, while sponsor, buyer, budget owner, procurement authority, and approver remain unverified."
                if organization
                else "No relevant organization or authority is identified.",
                _finding(review, "FL-Q03").get("evidence_ids", []),
            ),
            "T": _gate(
                "provisional" if infrastructure_class else "fail",
                "The infrastructure class is identified, but a bounded requirement, dependency map, and delivery schedule remain unverified."
                if infrastructure_class
                else "Technical fit cannot be evaluated without an infrastructure class.",
                _finding(review, "FL-Q02").get("evidence_ids", []),
            ),
            "I": _gate(
                "provisional" if strong_funding_refs else "fail",
                "Supported evidence references a possible funding or procurement path; eligibility, authority, and availability still require validation."
                if strong_funding_refs
                else "No supported funding, procurement, or implementation pathway is established in the bounded inputs.",
                strong_funding_refs,
            ),
            "A2": _gate(
                "provisional" if "anchorintel" in strategic_text else "fail",
                "An AnchorIntel use case is named, but differentiation, customer value, commercial scope, and delivery advantage remain unverified."
                if "anchorintel" in strategic_text
                else "A bounded strategic role and differentiated advantage are not established.",
                evidence_ids,
            ),
        }
        gate_basis = f"AnchorIntel deterministic adapter v{ADAPTER_VERSION}"

    assessment_date, review_date = _stable_dates(opportunity, module)
    persisted_lifecycle = opportunity.get("lifecycle")
    if not isinstance(persisted_lifecycle, dict) or not all(
        str(persisted_lifecycle.get(key, "")).strip()
        for key in ("owner", "next_action", "resource_ceiling", "review_date")
    ):
        triggers = [
            str(item.get("reason", "")).strip()
            for item in output.get("missing_evidence", [])
            if str(item.get("reason", "")).strip()
        ]
        lifecycle = {
            "owner": str(opportunity.get("analyst") or "AnchorIntel opportunity lead"),
            "next_action": "Resolve the current Knowledge Review's missing evidence before authorizing pursuit resources.",
            "resource_ceiling": "Assessment analysis only; no proposal, engineering, customer commitment, or implementation spend is authorized.",
            "review_date": review_date,
            "revalidation_triggers": triggers
            or ["Opportunity, evidence, Knowledge Review, module, adapter, or engine version changes"],
        }
        lifecycle_basis = f"AnchorIntel deterministic adapter v{ADAPTER_VERSION}"
    else:
        lifecycle = persisted_lifecycle
        lifecycle_basis = "Persisted opportunity lifecycle controls"

    engine_evidence = []
    for item in sorted(evidence, key=lambda value: value["evidence_id"]):
        engine_evidence.append(
            {
                "evidence_id": item["evidence_id"],
                "claim": str(item.get("claim") or item.get("description") or item.get("title", "")),
                "state": str(item.get("state", "A")).upper(),
                "source": str(item.get("source", "")),
                "source_date": str(item.get("source_date", "")),
                "retrieved_date": str(item.get("date_collected", "")),
                "geography": str(opportunity.get("geography", "")),
                "material": bool(item.get("material", True)),
                "notes": str(item.get("notes", "")),
            }
        )

    known_limitations = list(opportunity.get("known_limitations", []))
    for item in output.get("limitations", []):
        if item not in known_limitations:
            known_limitations.append(item)
    for item in output.get("missing_evidence", []):
        statement = f"Missing evidence — {item.get('category', 'Uncategorized')}: {item.get('reason', '')}".strip()
        if statement not in known_limitations:
            known_limitations.append(statement)

    payload = {
        "opportunity_id": opportunity["opportunity_id"],
        "title": opportunity["title"],
        "geography": opportunity["geography"],
        "infrastructure_class": infrastructure_class,
        "problem_statement": problem_statement,
        "analyst": str(opportunity.get("analyst", "")),
        "assessment_date": assessment_date,
        "evidence": engine_evidence,
        "dimensions": dimensions,
        "gates": gates,
        "fatal_constraints": list(opportunity.get("fatal_constraints", [])),
        "known_limitations": known_limitations,
        "lifecycle": lifecycle,
    }
    derivation = {
        "adapter_version": ADAPTER_VERSION,
        "engine_version": ENGINE_VERSION,
        "dimension_basis": dimension_basis,
        "gate_basis": gate_basis,
        "lifecycle_basis": lifecycle_basis,
        "assessment_date_basis": "Persisted opportunity assessment date or Knowledge Module effective date",
        "bounded_input_notice": (
            "The adapter uses only persisted local opportunity, active evidence, Knowledge Review, and Knowledge Module records. "
            "Conservative defaults identify unassessed domains; they are not independent findings."
        ),
    }
    return payload, derivation


def build_operational_result(
    engine_result: dict[str, Any],
    review: dict[str, Any],
    evidence_trace: list[dict[str, Any]],
    derivation: dict[str, Any],
) -> dict[str, Any]:
    """Augment the unchanged engine result with application-level trace fields."""

    result = dict(engine_result)
    failed_gates = sorted(
        key for key, value in result.get("gates", {}).items() if value.get("status") == "fail"
    )
    review_output = review.get("output", {})
    risk_statements = [
        str(item.get("statement", ""))
        for item in review_output.get("risks", [])
        if str(item.get("statement", ""))
    ]
    if failed_gates:
        risk_level = "High"
    elif risk_statements or result.get("unknowns_or_disputes"):
        risk_level = "Moderate"
    else:
        risk_level = "Low"
    result["risk_profile"] = {
        "level": risk_level,
        "failed_gates": failed_gates,
        "knowledge_risks": risk_statements,
        "warnings": list(result.get("warnings", [])),
    }
    result["knowledge_review_id"] = review["review_id"]
    result["knowledge_assumptions"] = list(review_output.get("assumptions", []))
    result["explanation"] = {
        "engine": result.get("recommendation_reason", ""),
        "input_derivation": derivation,
    }
    result["evidence_trace"] = evidence_trace
    return result
