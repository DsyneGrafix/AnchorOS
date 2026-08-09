from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from anchorinsight_gap_resolution import IntelligenceGapResolutionService
from anchorinsight_gap_resolution.capabilities import load_sls_cap_001
from anchorinsight_gap_resolution.contracts import load_osf_ec_001
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

    def test_osf_contract_is_machine_readable_and_normatively_bounded(self) -> None:
        contract = load_osf_ec_001()
        self.assertEqual(contract.contract_id, "OSF-EC-001")
        self.assertEqual(sum(item.weight for item in contract.dimensions), 100)
        self.assertEqual([item.dimension_id for item in contract.dimensions], ["OSF-01", "OSF-02", "OSF-03", "OSF-04", "OSF-05"])
        self.assertIn("UNKNOWN", contract.evidence_states)
        self.assertIn("NOT_SUPPORTED", contract.evidence_states)
        self.assertTrue(contract.contrary_evidence_required)
        self.assertEqual(len(contract.approval_conditions), 8)

    def test_sls_cap_registry_is_machine_readable_and_bounded_to_ten_capabilities(self) -> None:
        registry = load_sls_cap_001()
        self.assertEqual(registry.registry_id, "SLS-CAP-001")
        self.assertEqual(registry.admissible_capability_ids, tuple(f"CAP-{i:03d}" for i in range(1, 11)))
        self.assertEqual(len(registry.capabilities), 10)
        self.assertTrue(all(item.proof_refs for item in registry.capabilities))
        self.assertIn("Potential capability is not current capability", registry.governing_rule)

    def test_sparse_cps_profile_generates_contract_driven_osf_requirements(self) -> None:
        plan = self.service.build_plan("COF-ORG-2026-001")
        osf = [item for item in plan.requirements if item.contract_id == "OSF-EC-001"]
        self.assertEqual(plan.organization_name, "CPS Energy")
        self.assertEqual(plan.readiness_percent, 12.5)
        self.assertEqual(len(osf), 5)
        self.assertEqual([item.obligation_id for item in osf], ["OSF-01", "OSF-02", "OSF-03", "OSF-04", "OSF-05"])
        self.assertTrue(all(item.handoff_target == "AIN-303.2" for item in osf))

    def test_problem_alignment_is_highest_priority_osf_requirement(self) -> None:
        plan = self.service.build_plan("COF-ORG-2026-001")
        osf = [item for item in plan.requirements if item.contract_id == "OSF-EC-001"]
        self.assertEqual(osf[0].title, "OSF-01 — Problem Alignment")
        self.assertEqual(osf[0].priority, 100)
        self.assertIn("30%", osf[0].decision_impact)

    def test_osf01_and_osf02_are_bounded_by_sls_cap_001(self) -> None:
        plan = self.service.build_plan("COF-ORG-2026-001")
        osf = {item.obligation_id: item for item in plan.requirements if item.contract_id == "OSF-EC-001"}
        expected = tuple(f"CAP-{i:03d}" for i in range(1, 11))
        for obligation in ("OSF-01", "OSF-02"):
            req = osf[obligation]
            self.assertEqual(req.capability_registry_id, "SLS-CAP-001")
            self.assertEqual(req.allowed_capability_ids, expected)
            self.assertIn("SLS-CAP-001", req.objective)
            self.assertIn("CAP-*", req.completion_condition)

    def test_non_capability_osf_obligations_do_not_inherit_capability_whitelist(self) -> None:
        plan = self.service.build_plan("COF-ORG-2026-001")
        osf = {item.obligation_id: item for item in plan.requirements if item.contract_id == "OSF-EC-001"}
        for obligation in ("OSF-03", "OSF-04", "OSF-05"):
            self.assertIsNone(osf[obligation].capability_registry_id)
            self.assertEqual(osf[obligation].allowed_capability_ids, ())

    def test_generic_strategic_fit_requirement_is_replaced(self) -> None:
        plan = self.service.build_plan("COF-ORG-2026-001")
        titles = {item.title for item in plan.requirements}
        self.assertNotIn("Support Organization Strategic Fit", titles)
        self.assertIn("OSF-01 — Problem Alignment", titles)
        self.assertIn("OSF-05 — Adoption / Engagement Fit", titles)

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
