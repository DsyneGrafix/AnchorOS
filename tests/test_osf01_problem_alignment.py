from __future__ import annotations

import unittest

from anchorinsight_gap_resolution import (
    CapabilityMatchAssessment,
    CapabilityMatchState,
    GovernedEvidenceReference,
    OSF01ProblemAlignmentService,
    OSF01State,
)


class OSF01ProblemAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = OSF01ProblemAlignmentService()
        self.evidence = GovernedEvidenceReference(
            evidence_id="COF-EVD-2026-001",
            assertion=(
                "CPS Energy is pursuing battery storage and microgrid capability "
                "to support resiliency and critical-infrastructure needs."
            ),
            classification="OSF-01 Problem Alignment Candidate",
            verified=True,
        )

    def test_customer_evidence_without_capability_intersection_remains_unknown(self) -> None:
        determination = self.service.determine(
            organization_id="COF-ORG-2026-001",
            evidence=(self.evidence,),
        )
        self.assertEqual(determination.state, OSF01State.UNKNOWN)
        self.assertEqual(determination.evidence_ids, ("COF-EVD-2026-001",))
        self.assertEqual(determination.supported_capability_ids, ())

    def test_supported_current_capability_intersection_supports_osf01(self) -> None:
        determination = self.service.determine(
            organization_id="COF-ORG-2026-001",
            evidence=(self.evidence,),
            capability_assessments=(
                CapabilityMatchAssessment(
                    capability_id="CAP-009",
                    state=CapabilityMatchState.SUPPORTED,
                    evidence_ids=(self.evidence.evidence_id,),
                    rationale="Governed evidence establishes an operational validity problem addressed by CAP-009.",
                    evaluator_id="Authorized Human Evaluator",
                ),
            ),
        )
        self.assertEqual(determination.state, OSF01State.SUPPORTED)
        self.assertEqual(determination.supported_capability_ids, ("CAP-009",))

    def test_partial_intersection_produces_partially_supported(self) -> None:
        determination = self.service.determine(
            organization_id="COF-ORG-2026-001",
            evidence=(self.evidence,),
            capability_assessments=(
                CapabilityMatchAssessment(
                    capability_id="CAP-009",
                    state=CapabilityMatchState.PARTIALLY_SUPPORTED,
                    evidence_ids=(self.evidence.evidence_id,),
                    rationale="Evidence suggests relevance but does not establish the specific continuation-validity failure mode.",
                    evaluator_id="Authorized Human Evaluator",
                ),
            ),
        )
        self.assertEqual(determination.state, OSF01State.PARTIALLY_SUPPORTED)

    def test_not_supported_requires_all_admissible_capabilities_to_be_rejected(self) -> None:
        assessments = tuple(
            CapabilityMatchAssessment(
                capability_id=f"CAP-{index:03d}",
                state=CapabilityMatchState.NOT_SUPPORTED,
                evidence_ids=(self.evidence.evidence_id,),
                rationale="Reviewed against bounded capability claim and found not applicable.",
                evaluator_id="Authorized Human Evaluator",
            )
            for index in range(1, 11)
        )
        determination = self.service.determine(
            organization_id="COF-ORG-2026-001",
            evidence=(self.evidence,),
            capability_assessments=assessments,
        )
        self.assertEqual(determination.state, OSF01State.NOT_SUPPORTED)
        self.assertEqual(len(determination.not_supported_capability_ids), 10)

    def test_unverified_or_non_cof_evidence_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.service.determine(
                organization_id="COF-ORG-2026-001",
                evidence=(
                    GovernedEvidenceReference(
                        evidence_id="TEMP-001",
                        assertion="Uncommitted assertion",
                        classification="Draft",
                        verified=False,
                    ),
                ),
            )

    def test_assessment_cannot_reference_unknown_evidence(self) -> None:
        with self.assertRaises(ValueError):
            self.service.determine(
                organization_id="COF-ORG-2026-001",
                evidence=(self.evidence,),
                capability_assessments=(
                    CapabilityMatchAssessment(
                        capability_id="CAP-001",
                        state=CapabilityMatchState.SUPPORTED,
                        evidence_ids=("COF-EVD-MISSING",),
                        rationale="Invalid traceability test.",
                        evaluator_id="Authorized Human Evaluator",
                    ),
                ),
            )

    def test_determination_is_integrity_hashable_and_deterministic(self) -> None:
        first = self.service.determine(
            organization_id="COF-ORG-2026-001",
            evidence=(self.evidence,),
        )
        second = self.service.determine(
            organization_id="COF-ORG-2026-001",
            evidence=(self.evidence,),
        )
        self.assertEqual(first.integrity_hash, second.integrity_hash)
        self.assertEqual(len(first.integrity_hash), 64)


if __name__ == "__main__":
    unittest.main()
