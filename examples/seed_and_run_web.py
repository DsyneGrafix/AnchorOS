"""Seed AIN-104 demo data and run the web application."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anchorinsight_registry import (
    CommercialIntelligenceRegistryService,
    ScoringDecisionService,
)
from anchorinsight_web import create_app


def seed(database: Path) -> None:
    if database.exists():
        database.unlink()
    registry = CommercialIntelligenceRegistryService(database)
    scoring = ScoringDecisionService(registry)

    market = registry.create_market(
        name="Texas Infrastructure Utilities",
        definition="Texas utilities and ecosystem organizations.",
        actor="Ricky Jarnagin",
        cof_market_id="COF-MKT-2026-001",
    )
    organization = registry.create_organization(
        legal_name="City Public Service Board of San Antonio",
        common_name="CPS Energy",
        role="Infrastructure Owner",
        industry="Energy",
        sector="Municipal Utility",
        website="https://www.cpsenergy.com",
        headquarters="San Antonio, Texas",
        strategic_value="Pilot Candidate",
        actor="Ricky Jarnagin",
        cof_organization_id="COF-ORG-2026-001",
    )
    registry.add_market_membership(
        market_identifier=market["cof_market_id"],
        organization_identifier=organization["cof_organization_id"],
        actor="Ricky Jarnagin",
    )
    source = registry.create_source(
        source_type="Website",
        title="CPS Energy Website",
        publisher="CPS Energy",
        url="https://www.cpsenergy.com",
        content="CPS Energy public website",
        actor="Ricky Jarnagin",
    )
    registry.add_evidence(
        source_identifier=source["source_id"],
        assertion="CPS Energy is a San Antonio municipal utility.",
        evidence_type="Public Website",
        classification="Supported",
        confidence=0.90,
        subject_type="Organization",
        subject_identifier="COF-ORG-2026-001",
        actor="Ricky Jarnagin",
    )
    registry.add_action(
        subject_type="Organization",
        subject_identifier="COF-ORG-2026-001",
        description="Identify engineering and infrastructure leadership.",
        owner="Ricky Jarnagin",
        priority="High",
        actor="Ricky Jarnagin",
    )

    for key, scores in {
        "organization_fit": {
            "ICP Fit": 5, "Strategic Importance": 5, "Problem Relevance": 4,
            "Pilot Suitability": 4, "Long-Term Value": 5,
        },
        "organizational_viability": {
            "Financial Stability": 5, "Market Stability": 5,
            "Strategic Direction": 4, "Operational Continuity": 5,
            "Organizational Risk": 4,
        },
        "evidence_confidence": {
            "Quality": 4, "Authority": 4, "Recency": 4,
            "Completeness": 3, "Corroboration": 3,
        },
        "relationship_strength": {
            "Access": 3, "Trust": 3, "Influence": 2,
            "Engagement": 3, "Reciprocity": 2,
        },
    }.items():
        scoring.evaluate(
            model_key=key,
            subject_identifier="COF-ORG-2026-001",
            criterion_scores=scores,
            reviewer="Ricky Jarnagin",
            actor="Ricky Jarnagin",
        )
    scoring.calculate_cci(
        organization_identifier="COF-ORG-2026-001",
        reviewer="Ricky Jarnagin",
        actor="Ricky Jarnagin",
    )


if __name__ == "__main__":
    database = ROOT / "data" / "anchorinsight.db"
    database.parent.mkdir(parents=True, exist_ok=True)
    seed(database)
    print("AnchorInsight demo seeded.")
    print("Open: http://127.0.0.1:8080")
    create_app(database).run(host="127.0.0.1", port=8080, debug=False)
