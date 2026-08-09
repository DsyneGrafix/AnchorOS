from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from anchorinsight_gap_resolution import IntelligenceGapResolutionService
from anchorinsight_registry import CommercialIntelligenceRegistryService, OrganizationIntelligenceProfileService


class AIN304GapResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "anchorinsight.db"
        self.registry = CommercialIntelligenceRegistryService(self.db_path)
        self.org = self.registry.create_organization(
            legal_name="CPS Energy",
            common_name="CPS Energy",
            role="Target Organization",
            industry="Utilities",
            sector="Energy",
            website="https://www.cpsenergy.com/",
            actor="AIN-304 Test",
            cof_organization_id="COF-ORG-2026-001",
        )
        source = self.registry.create_source(
            source_type="AIN-302 Governed Source",
            title="CPS Energy Official Website",
            actor="AIN-304 Test",
            publisher="CPS Energy",
            url="https://www.cpsenergy.com/",
            content="CPS Energy maintains an official public web presence.",
        )
        self.registry.add_evidence(
            source_identifier=source["source_id"],
            assertion="CPS Energy maintains an official public web presence.",
            evidence_type="Organization Profile",
            classification="Verified",
            actor="AIN-304 Test",
            subject_type="Organization",
            subject_identifier=self.org["cof_organization_id"],
            confidence=0.95,
            reviewer="Authorized Human Reviewer",
        )
        self.profiles = OrganizationIntelligenceProfileService(self.registry)
        self.service = IntelligenceGapResolutionService(self.profiles)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_sparse_cps_profile_generates_collection_requirements(self) -> None:
        plan = self.service.build_plan("COF-ORG-2026-001")
        gaps = {item.gap_key for item in plan.requirements}
        self.assertEqual(plan.organization_name, "CPS Energy")
        self.assertEqual(plan.readiness_percent, 12.5)
        self.assertIn("market_link_missing", gaps)
        self.assertIn("evidence_coverage_low", gaps)
        self.assertIn("organization_strategic_fit_missing", gaps)
        self.assertIn("commercial_confidence_index_missing", gaps)

    def test_strategic_fit_is_highest_priority_missing_score_requirement(self) -> None:
        plan = self.service.build_plan("COF-ORG-2026-001")
        score_requirements = [r for r in plan.requirements if r.gap_key.endswith("_missing")]
        self.assertEqual(score_requirements[0].title, "Support Organization Strategic Fit")
        self.assertEqual(score_requirements[0].priority, 100)

    def test_plan_is_deterministic_for_same_governed_state(self) -> None:
        first = self.service.build_plan("COF-ORG-2026-001")
        second = self.service.build_plan("COF-ORG-2026-001")
        self.assertEqual(first.plan_id, second.plan_id)
        self.assertEqual(first.integrity_hash, second.integrity_hash)
        self.assertEqual(first.requirements, second.requirements)

    def test_requirements_handoff_to_ain3032_without_acquiring(self) -> None:
        plan = self.service.build_plan("COF-ORG-2026-001")
        self.assertTrue(plan.requirements)
        self.assertTrue(all(r.handoff_target == "AIN-303.2" for r in plan.requirements))
        self.assertTrue(all(r.completion_condition for r in plan.requirements))
        self.assertTrue(all(r.preferred_source_class for r in plan.requirements))

    def test_service_does_not_mutate_registry_state(self) -> None:
        before = self.registry.get_organization_profile("COF-ORG-2026-001")
        self.service.build_plan("COF-ORG-2026-001")
        after = self.registry.get_organization_profile("COF-ORG-2026-001")
        self.assertEqual(len(before["evidence"]), len(after["evidence"]))
        self.assertEqual(len(before["scorecards"]), len(after["scorecards"]))
        self.assertEqual(len(before["contacts"]), len(after["contacts"]))
        self.assertEqual(len(before["markets"]), len(after["markets"]))


if __name__ == "__main__":
    unittest.main()
