"""Canonical BOOT-0020 reference opportunity and idempotent bootstrap."""

from __future__ import annotations

from typing import Any

from .errors import ApiError
from .service import AnchorIntelService


REFERENCE_OPPORTUNITY_ID = "OI-000001"
REFERENCE_EVIDENCE_ID = "EV-000001"
REFERENCE_MODULE_ID = "AKM-GEO-FL-001"

REFERENCE_OPPORTUNITY: dict[str, Any] = {
    "opportunity_id": REFERENCE_OPPORTUNITY_ID,
    "title": "Florida Power & Light Asset Intelligence Opportunity",
    "organization": "Florida Power & Light",
    "sector": "Electric Utility",
    "status": "New",
    "description": (
        "Evaluate the deployment of AnchorIntel to improve asset intelligence, "
        "documentation quality, evidence management, and infrastructure opportunity "
        "assessment for utility operations."
    ),
    "geography": "Florida",
    "infrastructure_class": "Electric Utility",
    "problem_statement": (
        "Evaluate the deployment of AnchorIntel to improve asset intelligence, "
        "documentation quality, evidence management, and infrastructure opportunity "
        "assessment for utility operations."
    ),
    "reference_record": True,
    "workflow": [
        {"key": "create", "label": "Create Opportunity", "state": "complete"},
        {"key": "save", "label": "Save Opportunity", "state": "complete"},
        {"key": "evidence", "label": "Attach Evidence", "state": "pending"},
        {
            "key": "knowledge",
            "label": "Knowledge Module Review",
            "state": "pending",
        },
        {"key": "assessment", "label": "Run S.P.A.T.I.A.L.", "state": "pending"},
        {
            "key": "dossier",
            "label": "Generate Executive Opportunity Dossier",
            "state": "pending",
        },
        {"key": "archive", "label": "Archive Results", "state": "pending"},
    ],
}

REFERENCE_EVIDENCE: dict[str, Any] = {
    "evidence_id": REFERENCE_EVIDENCE_ID,
    "title": "Florida Electric Utility Asset Intelligence Context",
    "evidence_type": "Technical Record",
    "source": "Sirius Logic Systems Reference Analysis",
    "source_date": "",
    "description": (
        "Initial reference evidence supporting evaluation of an AnchorIntel "
        "asset-intelligence deployment for Florida electric utility operations."
    ),
    "evidence_status": "Collected",
    "evidence_confidence": "Moderate",
    "notes": (
        "Reference demonstration record. This is not an official Florida Power & "
        "Light document and is not represented as supplied or endorsed by Florida "
        "Power & Light."
    ),
}


def ensure_reference_opportunity(
    service: AnchorIntelService, actor: str = "anchorintel-bootstrap"
) -> tuple[dict[str, Any], bool]:
    """Create OI-000001 once and return ``(record, created)``.

    Existing records are never overwritten, including archived records. This makes
    startup seeding safe and preserves edits, evidence links, and audit history.
    """

    try:
        existing = service.repository.get_opportunity(
            REFERENCE_OPPORTUNITY_ID, include_archived=True
        )
    except ApiError as exc:
        if exc.code != "opportunity_not_found":
            raise
    else:
        return existing, False

    return service.create_opportunity(dict(REFERENCE_OPPORTUNITY), actor), True


def ensure_reference_evidence(
    service: AnchorIntelService, actor: str = "anchorintel-bootstrap"
) -> tuple[dict[str, Any] | None, bool]:
    """Create EV-000001 once without overwriting active or archived evidence."""

    opportunity = service.repository.get_opportunity(
        REFERENCE_OPPORTUNITY_ID, include_archived=True
    )
    try:
        existing = service.repository.get_evidence(
            REFERENCE_EVIDENCE_ID,
            opportunity_id=REFERENCE_OPPORTUNITY_ID,
            include_archived=True,
        )
    except ApiError as exc:
        if exc.code != "evidence_not_found":
            raise
    else:
        return existing, False

    # An archived reference opportunity remains archived. Startup seeding must
    # not bypass the normal rule that active opportunities receive evidence.
    if opportunity["archived"]:
        return None, False

    return (
        service.create_managed_evidence(
            REFERENCE_OPPORTUNITY_ID, dict(REFERENCE_EVIDENCE), actor
        ),
        True,
    )


def ensure_reference_records(
    service: AnchorIntelService, actor: str = "anchorintel-bootstrap"
) -> dict[str, Any]:
    opportunity, opportunity_created = ensure_reference_opportunity(service, actor)
    evidence, evidence_created = ensure_reference_evidence(service, actor)
    review, review_created = ensure_reference_review(service, actor)
    return {
        "opportunity": opportunity,
        "opportunity_created": opportunity_created,
        "evidence": evidence,
        "evidence_created": evidence_created,
        "knowledge_review": review,
        "knowledge_review_created": review_created,
    }


def ensure_reference_review(
    service: AnchorIntelService, actor: str = "anchorintel-bootstrap"
) -> tuple[dict[str, Any] | None, bool]:
    """Generate KR-000001 from persisted OI-000001 and active evidence once."""

    opportunity = service.repository.get_opportunity(
        REFERENCE_OPPORTUNITY_ID, include_archived=True
    )
    if opportunity["archived"]:
        return None, False
    active_evidence = service.repository.list_evidence(REFERENCE_OPPORTUNITY_ID)
    if not active_evidence:
        return None, False
    reviews = service.repository.list_knowledge_reviews(REFERENCE_OPPORTUNITY_ID)
    if reviews:
        return service.get_knowledge_review(
            REFERENCE_OPPORTUNITY_ID, reviews[0]["review_id"]
        ), False
    return (
        service.run_knowledge_review(
            REFERENCE_OPPORTUNITY_ID,
            REFERENCE_MODULE_ID,
            actor,
            review_status="Completed",
        ),
        True,
    )
