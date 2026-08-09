from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from anchorinsight_gap_resolution import (
    CollectionRequirementAdapterError,
    CollectionRequirementResearchAdapter,
    IntelligenceGapResolutionService,
)
from anchorinsight_registry import CommercialIntelligenceRegistryService, OrganizationIntelligenceProfileService


class AIN304ResearchRequestAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        db_path = Path(self.tmp.name) / "anchorinsight.db"
        registry = CommercialIntelligenceRegistryService(db_path)
        org = registry.create_organization(
            legal_name="CPS Energy",
            common_name="CPS Energy",
            role="Target Organization",
            industry="Utilities",
            sector="Energy",
            website="https://www.cpsenergy.com/",
            actor="AIN-304 Adapter Test",
            cof_organization_id="COF-ORG-2026-001",
        )
        source = registry.create_source(
            source_type="AIN-302 Governed Source",
            title="CPS Energy Official Website",
            actor="AIN-304 Adapter Test",
            publisher="CPS Energy",
            url="https://www.cpsenergy.com/",
            content="CPS Energy maintains an official public web presence.",
        )
        registry.add_evidence(
            source_identifier=source["source_id"],
            assertion="CPS Energy maintains an official public web presence.",
            evidence_type="Organization Profile",
            classification="Verified",
            actor="AIN-304 Adapter Test",
            subject_type="Organization",
            subject_identifier=org["cof_organization_id"],
            confidence=0.95,
            reviewer="Authorized Human Reviewer",
        )
        profiles = OrganizationIntelligenceProfileService(registry)
        resolver = IntelligenceGapResolutionService(profiles)
        plan = resolver.build_plan("COF-ORG-2026-001")
        self.requirement = next(
            item for item in plan.requirements if item.obligation_id == "OSF-01"
        )
        self.adapter = CollectionRequirementResearchAdapter()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_osf01_adapts_to_existing_research_request_model(self) -> None:
        handoff = self.adapter.adapt(
            requirement=self.requirement,
            workspace_id="WS-EXEC-001",
            organization_identifier="COF-ORG-2026-001",
            organization_name="CPS Energy",
        )
        request = handoff.research_request
        self.assertEqual(handoff.contract_id, "OSF-EC-001")
        self.assertEqual(handoff.obligation_id, "OSF-01")
        self.assertEqual(handoff.capability_registry_id, "SLS-CAP-001")
        self.assertEqual(request.workspace_id, "WS-EXEC-001")
        self.assertEqual(request.organization_identifier, "COF-ORG-2026-001")
        self.assertIn("CPS Energy", request.objective)
        self.assertIn("OSF-EC-001", request.objective)
        self.assertIn("OSF-01", request.objective)

    def test_osf01_request_preserves_capability_whitelist(self) -> None:
        handoff = self.adapter.adapt(
            requirement=self.requirement,
            workspace_id="WS-EXEC-001",
            organization_identifier="COF-ORG-2026-001",
            organization_name="CPS Energy",
        )
        expected = tuple(f"CAP-{index:03d}" for index in range(1, 11))
        self.assertEqual(handoff.allowed_capability_ids, expected)
        constraints = "\n".join(handoff.research_request.constraints)
        self.assertIn("SLS-CAP-001", constraints)
        self.assertIn("CAP-001", constraints)
        self.assertIn("CAP-010", constraints)
        self.assertIn("future", constraints)

    def test_request_forbids_inference_and_authoritative_evidence_actions(self) -> None:
        handoff = self.adapter.adapt(
            requirement=self.requirement,
            workspace_id="WS-EXEC-001",
            organization_identifier="COF-ORG-2026-001",
            organization_name="CPS Energy",
        )
        constraints = "\n".join(handoff.research_request.constraints)
        self.assertIn("Do not infer a customer problem", constraints)
        self.assertIn("Do not assert Strategic Fit", constraints)
        self.assertIn("Do not create findings", constraints)
        self.assertIn("No qualifying evidence found", constraints)
        self.assertIn("contradicts or weakens", constraints)

    def test_same_requirement_produces_same_logical_request_fingerprint(self) -> None:
        first = self.adapter.adapt(
            requirement=self.requirement,
            workspace_id="WS-EXEC-001",
            organization_identifier="COF-ORG-2026-001",
            organization_name="CPS Energy",
        )
        second = self.adapter.adapt(
            requirement=self.requirement,
            workspace_id="WS-EXEC-001",
            organization_identifier="COF-ORG-2026-001",
            organization_name="CPS Energy",
        )
        self.assertEqual(
            first.research_request.request_fingerprint,
            second.research_request.request_fingerprint,
        )
        self.assertNotEqual(first.research_request.request_id, second.research_request.request_id)

    def test_rejects_capability_bound_requirement_without_whitelist(self) -> None:
        broken = type(self.requirement)(
            requirement_id=self.requirement.requirement_id,
            gap_key=self.requirement.gap_key,
            title=self.requirement.title,
            objective=self.requirement.objective,
            priority=self.requirement.priority,
            decision_impact=self.requirement.decision_impact,
            completion_condition=self.requirement.completion_condition,
            preferred_source_class=self.requirement.preferred_source_class,
            handoff_target=self.requirement.handoff_target,
            contract_id=self.requirement.contract_id,
            obligation_id=self.requirement.obligation_id,
            capability_registry_id=self.requirement.capability_registry_id,
            allowed_capability_ids=(),
        )
        with self.assertRaises(CollectionRequirementAdapterError):
            self.adapter.adapt(
                requirement=broken,
                workspace_id="WS-EXEC-001",
                organization_identifier="COF-ORG-2026-001",
                organization_name="CPS Energy",
            )

    def test_rejects_wrong_handoff_target(self) -> None:
        broken = type(self.requirement)(
            requirement_id=self.requirement.requirement_id,
            gap_key=self.requirement.gap_key,
            title=self.requirement.title,
            objective=self.requirement.objective,
            priority=self.requirement.priority,
            decision_impact=self.requirement.decision_impact,
            completion_condition=self.requirement.completion_condition,
            preferred_source_class=self.requirement.preferred_source_class,
            handoff_target="AIN-999",
            contract_id=self.requirement.contract_id,
            obligation_id=self.requirement.obligation_id,
            capability_registry_id=self.requirement.capability_registry_id,
            allowed_capability_ids=self.requirement.allowed_capability_ids,
        )
        with self.assertRaises(CollectionRequirementAdapterError):
            self.adapter.adapt(
                requirement=broken,
                workspace_id="WS-EXEC-001",
                organization_identifier="COF-ORG-2026-001",
                organization_name="CPS Energy",
            )


if __name__ == "__main__":
    unittest.main()
