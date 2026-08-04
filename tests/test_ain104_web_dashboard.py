from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from anchorinsight_registry import (
    CommercialIntelligenceRegistryService,
    ScoringDecisionService,
)
from anchorinsight_web import create_app


class AIN104WebDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "anchorinsight.db"
        registry = CommercialIntelligenceRegistryService(self.db_path)
        scoring = ScoringDecisionService(registry)

        market = registry.create_market(
            name="Texas Infrastructure Utilities",
            definition="Texas utilities and ecosystem organizations.",
            actor="Ricky",
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
            actor="Ricky",
            cof_organization_id="COF-ORG-2026-001",
        )
        registry.add_market_membership(
            market_identifier=market["cof_market_id"],
            organization_identifier=organization["cof_organization_id"],
            actor="Ricky",
        )
        registry.add_action(
            subject_type="Organization",
            subject_identifier="COF-ORG-2026-001",
            description="Identify engineering leadership.",
            actor="Ricky",
            owner="Ricky",
            priority="High",
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
                reviewer="Ricky",
                actor="Ricky",
            )
        scoring.calculate_cci(
            organization_identifier="COF-ORG-2026-001",
            reviewer="Ricky",
            actor="Ricky",
        )

        self.app = create_app(self.db_path, testing=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_dashboard_renders(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Commercial Intelligence Command Center", response.data)
        self.assertIn(b"CPS Energy", response.data)

    def test_organization_list_renders(self) -> None:
        response = self.client.get("/organizations")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"COF-ORG-2026-001", response.data)

    def test_organization_profile_renders(self) -> None:
        response = self.client.get("/organizations/COF-ORG-2026-001")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Commercial Confidence Index", response.data)
        self.assertIn(b"81.94", response.data)
        self.assertIn(b"Identify engineering leadership", response.data)

    def test_missing_profile_returns_404(self) -> None:
        response = self.client.get("/organizations/COF-ORG-2026-999")
        self.assertEqual(response.status_code, 404)

    def test_health_api(self) -> None:
        response = self.client.get("/api/health")
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["web"]["status"], "HEALTHY")
        self.assertEqual(payload["profile"]["status"], "HEALTHY")

    def test_organizations_api(self) -> None:
        response = self.client.get("/api/organizations")
        payload = response.get_json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["name"], "CPS Energy")

    def test_profile_api(self) -> None:
        response = self.client.get("/api/organizations/COF-ORG-2026-001")
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["organization"]["display_name"], "CPS Energy")
        self.assertEqual(payload["commercial_confidence"]["score"], 81.94)

    def test_search_filter(self) -> None:
        response = self.client.get("/organizations?q=CPS")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CPS Energy", response.data)

    def test_static_css_is_served(self) -> None:
        response = self.client.get("/static/app.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"--blue", response.data)


if __name__ == "__main__":
    unittest.main()
