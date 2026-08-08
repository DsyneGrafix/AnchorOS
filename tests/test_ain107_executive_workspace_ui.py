from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from anchorinsight_registry import CommercialIntelligenceRegistryService
from anchorinsight_web import create_app


class AIN107ExecutiveWorkspaceUITests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "anchorinsight.db"
        registry = CommercialIntelligenceRegistryService(self.db_path)
        self.organization = registry.create_organization(
            legal_name="City Public Service Board of San Antonio",
            common_name="CPS Energy",
            role="Infrastructure Owner",
            industry="Energy",
            sector="Municipal Utility",
            website="https://www.cpsenergy.com/",
            headquarters="San Antonio, Texas",
            actor="AIN-107 UI Test",
            cof_organization_id="COF-ORG-2026-001",
        )
        source = registry.create_source(
            source_type="AIN-302 Governed Source",
            title="CPS Energy Official Website",
            actor="Authorized Human Reviewer",
            publisher="CPS Energy",
            url="https://www.cpsenergy.com/",
            content="CPS Energy maintains an official public web presence.",
        )
        self.evidence = registry.add_evidence(
            source_identifier=source["source_id"],
            assertion="CPS Energy maintains an official public web presence.",
            evidence_type="Organization Profile",
            classification="Verified",
            actor="Authorized Human Reviewer",
            subject_type="Organization",
            subject_identifier=self.organization["cof_organization_id"],
            confidence=0.95,
            reviewer="Authorized Human Reviewer",
        )
        self.app = create_app(self.db_path, testing=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_profile_links_to_executive_brief(self) -> None:
        response = self.client.get("/organizations/COF-ORG-2026-001")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Open Executive Brief", response.data)
        self.assertIn(b"/organizations/COF-ORG-2026-001/executive-brief", response.data)

    def test_executive_brief_renders_governed_evidence(self) -> None:
        response = self.client.get("/organizations/COF-ORG-2026-001/executive-brief")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Executive Intelligence Brief", response.data)
        self.assertIn(b"CPS Energy", response.data)
        self.assertIn(b"Next justified action", response.data)
        self.assertIn(b"Governed Evidence", response.data)
        self.assertIn(self.evidence["cof_evidence_id"].encode(), response.data)
        self.assertIn(b"Verified", response.data)

    def test_executive_brief_api_exposes_evidence_basis_and_integrity(self) -> None:
        response = self.client.get("/api/organizations/COF-ORG-2026-001/executive-brief")
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["organization"]["display_name"], "CPS Energy")
        self.assertIn(self.evidence["cof_evidence_id"], payload["evidence_basis"])
        self.assertEqual(payload["evidence_summary"]["verified_count"], 1)
        self.assertEqual(len(payload["integrity_hash"]), 64)

    def test_missing_executive_brief_returns_404(self) -> None:
        response = self.client.get("/organizations/COF-ORG-2026-999/executive-brief")
        self.assertEqual(response.status_code, 404)

    def test_health_reports_ain107_service(self) -> None:
        response = self.client.get("/api/health")
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["reporting"]["status"], "HEALTHY")
        self.assertEqual(payload["reporting"]["version"], "107.1")


if __name__ == "__main__":
    unittest.main()
