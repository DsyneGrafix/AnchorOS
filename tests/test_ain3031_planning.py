from __future__ import annotations

import unittest

from anchorinsight_research.planning import (
    ResearchPlanningService,
    ResearchRequest,
    ValidationError,
)


class ResearchPlanningServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ResearchPlanningService()

    def make_request(self) -> ResearchRequest:
        return ResearchRequest(
            request_id="REQ-001",
            workspace_id="SLS-DEMO-001",
            organization_identifier="CPS Energy",
            objective=(
                "Identify evidence of infrastructure modernization, "
                "communications investment, and grid technology initiatives."
            ),
            requested_outputs=[
                "Candidate Sources",
                "Acquisition Receipts",
            ],
        )

    def test_research_plan_is_created(self) -> None:
        plan = self.service.create_plan(
            self.make_request(),
            pipeline_id="PIPELINE-001",
        )

        self.assertEqual(plan.organization, "CPS Energy")
        self.assertEqual(plan.workspace, "SLS-DEMO-001")
        self.assertEqual(plan.pipeline_id, "PIPELINE-001")
        self.assertEqual(plan.status, "PLANNED")

    def test_plan_id_is_deterministic(self) -> None:
        request = self.make_request()

        first = self.service.create_plan(
            request,
            pipeline_id="PIPELINE-001",
        )
        second = self.service.create_plan(
            request,
            pipeline_id="PIPELINE-002",
        )

        self.assertEqual(first.plan_id, second.plan_id)

    def test_categories_are_detected(self) -> None:
        plan = self.service.create_plan(
            self.make_request(),
            pipeline_id="PIPELINE-001",
        )

        self.assertEqual(
            plan.research_categories,
            (
                "Communications",
                "Energy",
                "Infrastructure",
                "Technology",
            ),
        )
def test_categories_are_detected(self) -> None:
    plan = self.service.create_plan(
        self.make_request(),
        pipeline_id="PIPELINE-001",
    )

    self.assertEqual(
        plan.research_categories,
        (
            "Communications",
            "Energy",
            "Infrastructure",
            "Technology",
        ),
    )
    def test_short_objective_is_rejected(self) -> None:
        request = ResearchRequest(
            request_id="REQ-002",
            workspace_id="SLS-DEMO-001",
            organization_identifier="CPS Energy",
            objective="Research CPS",
            requested_outputs=["Candidate Sources"],
        )

        with self.assertRaises(ValidationError):
            self.service.create_plan(request)

    def test_blank_workspace_is_rejected(self) -> None:
        request = ResearchRequest(
            request_id="REQ-003",
            workspace_id="",
            organization_identifier="CPS Energy",
            objective=(
                "Identify recent infrastructure modernization initiatives."
            ),
            requested_outputs=["Candidate Sources"],
        )

        with self.assertRaises(ValidationError):
            self.service.create_plan(request)

    def test_requested_outputs_are_required(self) -> None:
        request = ResearchRequest(
            request_id="REQ-004",
            workspace_id="SLS-DEMO-001",
            organization_identifier="CPS Energy",
            objective=(
                "Identify recent infrastructure modernization initiatives."
            ),
            requested_outputs=[],
        )

        with self.assertRaises(ValidationError):
            self.service.create_plan(request)


if __name__ == "__main__":
    unittest.main()
