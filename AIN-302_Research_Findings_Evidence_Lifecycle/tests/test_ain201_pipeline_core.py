from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from anchorinsight_pipeline import (
    CommercialIntelligencePipeline,
    PipelineRequest,
    PipelineStatus,
    ProfileRefreshStage,
    ReportRequestStage,
    RequestValidationStage,
    TargetResolutionStage,
)


class FakeRegistry:
    VERSION = "1.0"

    def get_organization(self, identifier: str):
        if identifier not in {"COF-ORG-2026-001", "CPS Energy"}:
            raise LookupError("Organization not found")
        return {
            "organization_id": "internal-001",
            "cof_organization_id": "COF-ORG-2026-001",
            "legal_name": "City Public Service Board of San Antonio",
            "common_name": "CPS Energy",
            "website": "https://www.cpsenergy.com",
            "headquarters": "San Antonio, Texas",
        }


class FakeProfiles:
    VERSION = "1.0"

    def build_profile(self, identifier: str):
        return {
            "organization": {"display_name": "CPS Energy"},
            "decision": {"decision": "Validate"},
            "readiness": {"status": "Ready"},
            "commercial_confidence": {"score": 81.94},
        }


class AIN201PipelineCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pipeline = CommercialIntelligencePipeline(
            services={"registry": FakeRegistry(), "profiles": FakeProfiles()},
            stages=[
                RequestValidationStage(),
                TargetResolutionStage(),
                ProfileRefreshStage(),
                ReportRequestStage(),
            ],
            receipt_directory=Path(self.tmp.name),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, outputs=("Organization Profile",)):
        return PipelineRequest(
            workspace_id="SLS-DEMO-001",
            organization_identifier="COF-ORG-2026-001",
            requested_by="Ricky Jarnagin",
            research_objective=(
                "Identify evidence of infrastructure modernization and "
                "communications investment announced within 24 months."
            ),
            requested_outputs=tuple(outputs),
        )

    def test_request_has_stable_idempotency_key(self):
        a = self.request()
        b = self.request()
        self.assertEqual(a.idempotency_key, b.idempotency_key)
        self.assertEqual(a.request_fingerprint, b.request_fingerprint)

    def test_request_change_changes_fingerprint(self):
        a = self.request()
        b = PipelineRequest(
            workspace_id=a.workspace_id,
            organization_identifier=a.organization_identifier,
            requested_by=a.requested_by,
            research_objective=a.research_objective + " Include grants.",
            requested_outputs=a.requested_outputs,
        )
        self.assertNotEqual(a.request_fingerprint, b.request_fingerprint)

    def test_bounded_request_completes(self):
        receipt = self.pipeline.run(self.request())
        self.assertEqual(receipt.status, PipelineStatus.COMPLETED)
        self.assertEqual(receipt.required_stages_passed, 3)

    def test_optional_report_is_skipped(self):
        receipt = self.pipeline.run(self.request())
        result = receipt.stage_results[-1]
        self.assertFalse(result.required)
        self.assertEqual(result.reason_code, "OPTIONAL_OUTPUT_NOT_REQUESTED")

    def test_requested_report_failure_is_partial(self):
        receipt = self.pipeline.run(self.request(("Organization Profile", "Executive Brief")))
        self.assertEqual(receipt.status, PipelineStatus.PARTIALLY_COMPLETED)
        self.assertTrue(receipt.stage_results[-1].required)

    def test_unresolved_target_requires_revalidation(self):
        request = self.request()
        request = PipelineRequest(
            workspace_id=request.workspace_id,
            organization_identifier="UNKNOWN",
            requested_by=request.requested_by,
            research_objective=request.research_objective,
        )
        receipt = self.pipeline.run(request)
        self.assertEqual(receipt.status, PipelineStatus.REVALIDATION_REQUIRED)
        self.assertEqual(receipt.stage_results[-1].decision, "REVALIDATE")

    def test_profile_stage_receipt_contains_cci(self):
        receipt = self.pipeline.run(self.request())
        profile = next(x for x in receipt.stage_results if x.stage_name == "Organization Profile Refresh")
        self.assertEqual(profile.details["cci"], 81.94)

    def test_receipt_and_manifest_are_persisted(self):
        receipt = self.pipeline.run(self.request())
        root = Path(self.tmp.name)
        self.assertTrue((root / f"{receipt.pipeline_id}.receipt.json").exists())
        self.assertTrue((root / f"{receipt.pipeline_id}.manifest.json").exists())

    def test_completed_retry_returns_same_receipt(self):
        request = self.request()
        first = self.pipeline.run(request)
        second = self.pipeline.run(request)
        self.assertEqual(first.pipeline_id, second.pipeline_id)

    def test_receipt_has_integrity_hash(self):
        receipt = self.pipeline.run(self.request())
        self.assertEqual(len(receipt.to_dict()["integrity_hash"]), 64)

    def test_manifest_has_integrity_hash(self):
        receipt = self.pipeline.run(self.request())
        self.assertEqual(len(receipt.manifest_hash), 64)

    def test_stage_results_have_common_contract(self):
        receipt = self.pipeline.run(self.request())
        for result in receipt.stage_results:
            self.assertTrue(result.stage_id)
            self.assertTrue(result.started_at)
            self.assertTrue(result.completed_at)
            self.assertTrue(result.audit_reference)

    def test_short_objective_fails_visibly(self):
        request = PipelineRequest(
            workspace_id="SLS-DEMO-001",
            organization_identifier="COF-ORG-2026-001",
            requested_by="Ricky",
            research_objective="Research CPS",
        )
        with self.assertRaises(Exception):
            self.pipeline.run(request)


if __name__ == "__main__":
    unittest.main()
