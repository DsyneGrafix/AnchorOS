from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from anchorinsight_pipeline import (
    CommercialIntelligencePipeline,
    PipelineRequest,
    PipelineStatus,
    ProfileRefreshStage,
    ReportRequestStage,
    RequestValidationStage,
    TargetResolutionStage,
)
from anchorinsight_registry import (
    CommercialIntelligenceRegistryService,
    OrganizationIntelligenceProfileService,
    RegistryDatabase,
)
from anchorinsight_reporting import ExecutiveReportService


class AIN107ExecutiveReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)

        self.registry = CommercialIntelligenceRegistryService(
            RegistryDatabase(root / "registry.db")
        )
        self.organization = self.registry.create_organization(
            legal_name="CPS Energy",
            common_name="CPS Energy",
            role="Target Organization",
            industry="Utilities",
            sector="Energy",
            website="https://www.cpsenergy.com/",
            actor="AIN-107 Test",
        )

        source = self.registry.create_source(
            source_type="AIN-302 Governed Source",
            title="CPS Energy Official Website",
            actor="Authorized Human Reviewer",
            publisher="CPS Energy",
            url="https://www.cpsenergy.com/",
            content="CPS Energy maintains an official public web presence.",
        )
        self.evidence = self.registry.add_evidence(
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

        self.profiles = OrganizationIntelligenceProfileService(self.registry)
        self.reports = ExecutiveReportService(self.profiles)
        self.root = root

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_committed_verified_evidence_appears_in_executive_brief(self) -> None:
        report = self.reports.generate_executive_brief(
            self.organization["cof_organization_id"]
        )

        self.assertEqual(report.organization["display_name"], "CPS Energy")
        self.assertEqual(report.evidence_summary["count"], 1)
        self.assertEqual(report.evidence_summary["verified_count"], 1)
        self.assertIn(self.evidence["cof_evidence_id"], report.evidence_basis)
        self.assertEqual(
            report.evidence_summary["items"][0]["classification"],
            "Verified",
        )

    def test_executive_brief_exposes_decision_and_next_justified_action(self) -> None:
        report = self.reports.generate_executive_brief(
            self.organization["cof_organization_id"]
        )

        self.assertEqual(report.executive_summary["decision"], "Validate")
        self.assertTrue(report.executive_summary["next_justified_action"])
        self.assertIn("readiness", report.executive_summary)
        self.assertIn("classification_counts", report.evidence_summary)

    def test_report_id_is_stable_for_same_governed_intelligence_state(self) -> None:
        first = self.reports.generate_executive_brief(
            self.organization["cof_organization_id"]
        )
        second = self.reports.generate_executive_brief(
            self.organization["cof_organization_id"]
        )

        self.assertEqual(first.report_id, second.report_id)
        self.assertNotEqual(first.generated_at, "")
        self.assertEqual(len(first.integrity_hash), 64)

    def test_ain201_pipeline_generates_requested_executive_brief(self) -> None:
        pipeline = CommercialIntelligencePipeline(
            services={
                "registry": self.registry,
                "profiles": self.profiles,
                "reports": self.reports,
            },
            stages=(
                RequestValidationStage(),
                TargetResolutionStage(),
                ProfileRefreshStage(),
                ReportRequestStage(),
            ),
            receipt_directory=self.root / "pipeline_receipts",
        )
        request = PipelineRequest(
            workspace_id="WS-EXEC-001",
            organization_identifier=self.organization["cof_organization_id"],
            requested_by="Executive User",
            research_objective=(
                "Produce a governed executive intelligence brief for this organization."
            ),
            requested_outputs=("Organization Profile", "Executive Brief"),
        )

        receipt = pipeline.run(request)

        self.assertEqual(receipt.status, PipelineStatus.COMPLETED)
        report_stage = receipt.stage_results[-1]
        self.assertEqual(report_stage.stage_name, "Report Generation")
        self.assertEqual(report_stage.details["evidence_count"], 1)
        self.assertEqual(report_stage.details["verified_evidence_count"], 1)
        self.assertIn(self.evidence["cof_evidence_id"], report_stage.details["evidence_basis"])
        self.assertTrue(report_stage.output_references[0].startswith("EXR-"))


if __name__ == "__main__":
    unittest.main()
