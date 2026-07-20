"""Canonical BOOT-0020 reference opportunity and idempotent bootstrap."""

from __future__ import annotations

from typing import Any

from .errors import ApiError
from .service import AnchorIntelService


REFERENCE_OPPORTUNITY_ID = "OI-000001"

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
