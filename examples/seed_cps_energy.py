
"""Seed the CIR-002 proof case with CPS Energy and the electric-utility market."""
from __future__ import annotations

import json
from pathlib import Path

from anchorinsight_registry.db import RegistryDatabase, utc_now


def seed(database_path: str | Path) -> dict:
    db = RegistryDatabase(database_path)
    db.initialize()

    market = db.create_market(
        name="Texas Infrastructure Utilities",
        definition=(
            "Texas utilities and utility ecosystem organizations managing "
            "complex physical infrastructure and modernization programs."
        ),
        lifecycle_state="Investigating",
        decision_outcome="Validate",
        priority="High",
        cof_market_id="COF-MKT-2026-001",
    )

    organization = db.create_organization(
        legal_name="City Public Service Board of San Antonio",
        common_name="CPS Energy",
        role="Infrastructure Owner",
        industry="Energy",
        sector="Municipal Utility",
        website="https://www.cpsenergy.com",
        headquarters="San Antonio, Texas",
        cof_status="Validate",
        priority="High",
        strategic_value="Pilot Candidate",
        cof_organization_id="COF-ORG-2026-001",
    )

    membership = db.add_market_membership(
        market["market_id"],
        organization["organization_id"],
        relevance="Primary",
        market_role="Potential Customer",
        priority="High",
    )

    scorecard = db.create_scorecard(
        subject_type="Organization",
        subject_id=organization["organization_id"],
        score_model="Organization Strategic Fit",
        model_version="1.0",
        criterion_scores={
            "ICP Fit": 5,
            "Strategic Importance": 5,
            "Problem Relevance": 4,
            "Pilot Suitability": 4,
            "Long-Term Value": 5,
        },
        maximum_score=25,
        decision_outcome="Validate",
        reviewer="Ricky Jarnagin",
        recommendation=(
            "Identify engineering leadership and verify a bounded paid "
            "assessment or pilot path."
        ),
    )

    now = utc_now()
    action_cof_id = db.next_cof_id("action")
    lifecycle_cof_id = db.next_cof_id("lifecycle_event")
    with db.transaction() as connection:
        connection.execute(
            """
            INSERT INTO actions(
                action_id, cof_action_id, subject_type, subject_id,
                description, owner, priority, due_at, status,
                created_at, updated_at
            ) VALUES (?, ?, 'Organization', ?, ?, ?, 'High', NULL, 'Open', ?, ?)
            """,
            (
                db.internal_id(),
                action_cof_id,
                organization["organization_id"],
                "Identify engineering and infrastructure leadership.",
                "Ricky Jarnagin",
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO lifecycle_events(
                lifecycle_event_id, cof_lifecycle_event_id, subject_type,
                subject_id, event_type, previous_state, new_state, reason,
                actor, occurred_at, created_at
            ) VALUES (?, ?, 'Organization', ?, 'organization.registered',
                      NULL, 'Validate', ?, ?, ?, ?)
            """,
            (
                db.internal_id(),
                lifecycle_cof_id,
                organization["organization_id"],
                "Initial AnchorInsight proof record.",
                "Ricky Jarnagin",
                now,
                now,
            ),
        )

    return {
        "market": market,
        "organization": organization,
        "membership": membership,
        "scorecard": scorecard,
        "profile": db.organization_profile(organization["organization_id"]),
        "health": db.health(),
    }


if __name__ == "__main__":
    output = seed(Path("data") / "anchorinsight.db")
    print(json.dumps(output, indent=2, default=str))
