from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from anchorinsight_research.discovery import SourceCatalogEntry
from anchorinsight_research.models import (
    AcquisitionStatus,
    ResearchRequest,
)
from anchorinsight_research.service import (
    ResearchAcquisitionResult,
    ResearchPlanningAcquisitionService,
)


class ResearchPlanningAcquisitionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

        self.catalog = (
            SourceCatalogEntry(
                title="CPS Energy Official Website",
                url="https://www.cpsenergy.com",
                organization="CPS Energy",
                source_type="Corporate",
                authority_score=1.00,
                categories=(
                    "Energy",
                    "Infrastructure",
                    "Technology",
                ),
                discovery_reason="Official organization source",
            ),
            SourceCatalogEntry(
                title="CPS Energy Newsroom",
                url="https://newsroom.cpsenergy.com",
                organization="CPS Energy",
                source_type="Corporate",
                authority_score=0.98,
                categories=(
                    "Energy",
                    "Infrastructure",
                    "Technology",
                ),
                discovery_reason=(
                    "Official announcements and modernization news"
                ),
            ),
            SourceCatalogEntry(
                title="Public Utility Commission of Texas",
                url="https://www.puc.texas.gov",
                organization="CPS Energy",
                source_type="Regulatory",
                authority_score=0.96,
                categories=(
                    "Energy",
                    "Infrastructure",
                ),
                discovery_reason="Relevant regulatory authority",
            ),
        )

        self.service = (
            ResearchPlanningAcquisitionService.from_directory(
                self.root,
                catalog=self.catalog,
            )
        )

        self.request = ResearchRequest(
            workspace_id="SLS-DEMO-001",
            organization_identifier="CPS Energy",
            objective=(
                "Identify evidence of infrastructure modernization, "
                "communications investment, grid technology initiatives, "
                "or related commercial signals."
            ),
            requested_outputs=(
                "Candidate Sources",
                "Acquisition Receipts",
            ),
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_service_version_is_declared(self) -> None:
        self.assertEqual(
            self.service.VERSION,
            "303.1",
        )

    def test_plan_is_created_and_persisted(self) -> None:
        plan = self.service.create_plan(
            self.request,
            pipeline_id="PIPELINE-3031-001",
        )

        persisted = self.service.store.load_plan(
            plan.plan_id
        )

        self.assertEqual(
            persisted["plan_id"],
            plan.plan_id,
        )
        self.assertEqual(
            persisted["request_id"],
            self.request.request_id,
        )
        self.assertEqual(
            persisted["pipeline_id"],
            "PIPELINE-3031-001",
        )

    def test_sources_are_discovered_and_persisted(
        self,
    ) -> None:
        plan = self.service.create_plan(
            self.request,
            pipeline_id="PIPELINE-3031-001",
        )

        sources = self.service.discover_sources(plan)

        self.assertEqual(len(sources), 3)
        self.assertEqual(
            sources[0].title,
            "CPS Energy Official Website",
        )

        persisted_files = list(
            self.service.store.candidate_sources.glob(
                "*.json"
            )
        )

        self.assertEqual(
            len(persisted_files),
            3,
        )

    def test_duplicate_discovery_loads_existing_sources(
        self,
    ) -> None:
        plan = self.service.create_plan(
            self.request,
            pipeline_id="PIPELINE-3031-001",
        )

        first = self.service.discover_sources(plan)
        second = self.service.discover_sources(plan)

        self.assertEqual(len(first), 3)
        self.assertEqual(len(second), 3)

        self.assertEqual(
            tuple(
                source.source_id
                for source in first
            ),
            tuple(
                source.source_id
                for source in second
            ),
        )

    def test_content_map_executes_complete_workflow(
        self,
    ) -> None:
        content_by_url = {
            "https://www.cpsenergy.com": (
                b"CPS Energy official infrastructure information.",
                "text/plain",
            ),
            "https://newsroom.cpsenergy.com": (
                b"CPS Energy announced modernization initiatives.",
                "text/plain",
            ),
            "https://www.puc.texas.gov": (
                b"Texas utility regulatory information.",
                "text/plain",
            ),
        }

        result = self.service.execute_with_content_map(
            request=self.request,
            content_by_url=content_by_url,
            pipeline_id="PIPELINE-3031-001",
        )

        self.assertIsInstance(
            result,
            ResearchAcquisitionResult,
        )
        self.assertEqual(
            result.sources_discovered,
            3,
        )
        self.assertEqual(
            result.documents_acquired,
            3,
        )
        self.assertEqual(
            result.receipts_generated,
            3,
        )
        self.assertTrue(
            result.ready_for_ain302
        )

    def test_missing_provider_creates_not_found_receipt(
        self,
    ) -> None:
        content_by_url = {
            "https://www.cpsenergy.com": (
                b"CPS Energy official infrastructure information.",
                "text/plain",
            ),
        }

        result = self.service.execute_with_content_map(
            request=self.request,
            content_by_url=content_by_url,
            pipeline_id="PIPELINE-3031-001",
        )

        statuses = [
            receipt.status
            for receipt in result.acquisition_receipts
        ]

        self.assertEqual(
            statuses.count(
                AcquisitionStatus.RETRIEVED
            ),
            1,
        )
        self.assertEqual(
            statuses.count(
                AcquisitionStatus.NOT_FOUND
            ),
            2,
        )
        self.assertEqual(
            result.receipts_generated,
            result.sources_discovered,
        )

    def test_provider_can_be_resolved_by_source_id(
        self,
    ) -> None:
        plan = self.service.create_plan(
            self.request,
            pipeline_id="PIPELINE-3031-001",
        )
        sources = self.service.discover_sources(plan)

        target = sources[0]

        def provider(source):
            return (
                b"Source content resolved by source ID.",
                "text/plain",
            )

        second_request = ResearchRequest(
            workspace_id=self.request.workspace_id,
            organization_identifier=(
                self.request.organization_identifier
            ),
            objective=self.request.objective,
            requested_outputs=(
                self.request.requested_outputs
            ),
        )

        result = self.service.execute_with_providers(
            request=second_request,
            providers={
                target.source_id: provider,
            },
            pipeline_id="PIPELINE-3031-002",
        )

        retrieved = [
            receipt
            for receipt in result.acquisition_receipts
            if receipt.status
            == AcquisitionStatus.RETRIEVED
        ]

        self.assertEqual(len(retrieved), 1)
        self.assertEqual(
            retrieved[0].source_id,
            target.source_id,
        )

    def test_provider_timeout_is_preserved_in_result(
        self,
    ) -> None:
        plan = self.service.create_plan(
            self.request,
            pipeline_id="PIPELINE-3031-001",
        )
        sources = self.service.discover_sources(plan)

        target = sources[0]

        def timeout_provider(source):
            raise TimeoutError(
                "Bounded provider timed out."
            )

        second_request = ResearchRequest(
            workspace_id=self.request.workspace_id,
            organization_identifier=(
                self.request.organization_identifier
            ),
            objective=self.request.objective,
            requested_outputs=(
                self.request.requested_outputs
            ),
        )

        result = self.service.execute_with_providers(
            request=second_request,
            providers={
                target.source_id: timeout_provider,
            },
            pipeline_id="PIPELINE-3031-002",
        )

        timeout_receipts = [
            receipt
            for receipt in result.acquisition_receipts
            if receipt.status
            == AcquisitionStatus.TIMEOUT
        ]

        self.assertEqual(
            len(timeout_receipts),
            1,
        )
        self.assertEqual(
            timeout_receipts[0].failure_reason,
            "Bounded provider timed out.",
        )

    def test_duplicate_content_produces_duplicate_receipt(
        self,
    ) -> None:
        identical_content = (
            b"Identical infrastructure modernization content."
        )

        content_by_url = {
            "https://www.cpsenergy.com": (
                identical_content,
                "text/plain",
            ),
            "https://newsroom.cpsenergy.com": (
                identical_content,
                "text/plain",
            ),
            "https://www.puc.texas.gov": (
                b"Independent regulatory content.",
                "text/plain",
            ),
        }

        result = self.service.execute_with_content_map(
            request=self.request,
            content_by_url=content_by_url,
            pipeline_id="PIPELINE-3031-001",
        )

        statuses = [
            receipt.status
            for receipt in result.acquisition_receipts
        ]

        self.assertEqual(
            statuses.count(
                AcquisitionStatus.RETRIEVED
            ),
            2,
        )
        self.assertEqual(
            statuses.count(
                AcquisitionStatus.DUPLICATE
            ),
            1,
        )
        self.assertEqual(
            result.documents_acquired,
            2,
        )

    def test_result_serializes_complete_summary(
        self,
    ) -> None:
        content_by_url = {
            "https://www.cpsenergy.com": (
                b"CPS Energy source content.",
                "text/plain",
            ),
        }

        result = self.service.execute_with_content_map(
            request=self.request,
            content_by_url=content_by_url,
            pipeline_id="PIPELINE-3031-001",
        )

        payload = result.to_dict()

        self.assertEqual(
            payload["summary"]["sources_discovered"],
            3,
        )
        self.assertEqual(
            payload["summary"]["documents_acquired"],
            1,
        )
        self.assertEqual(
            payload["summary"]["receipts_generated"],
            3,
        )
        self.assertTrue(
            payload["summary"]["ready_for_ain302"]
        )

        self.assertEqual(
            len(payload["candidate_sources"]),
            3,
        )
        self.assertEqual(
            len(payload["acquisition_receipts"]),
            3,
        )

    def test_all_receipts_have_integrity_hashes(
        self,
    ) -> None:
        result = self.service.execute_with_content_map(
            request=self.request,
            content_by_url={},
            pipeline_id="PIPELINE-3031-001",
        )

        for receipt in result.acquisition_receipts:
            self.assertEqual(
                len(receipt.integrity_hash),
                64,
            )
            self.assertTrue(
                self.service.acquisition
                .receipt_service
                .verify_integrity(receipt)
            )

    def test_original_acquired_content_is_preserved(
        self,
    ) -> None:
        original = (
            b"Original CPS Energy source bytes."
        )

        result = self.service.execute_with_content_map(
            request=self.request,
            content_by_url={
                "https://www.cpsenergy.com": (
                    original,
                    "text/plain",
                ),
            },
            pipeline_id="PIPELINE-3031-001",
        )

        self.assertEqual(
            result.documents_acquired,
            1,
        )

        document = result.acquired_documents[0]

        stored = (
            self.service.store
            .load_acquired_document_content(
                document.document_id
            )
        )

        self.assertEqual(stored, original)

    def test_result_is_not_ready_without_documents(
        self,
    ) -> None:
        result = self.service.execute_with_content_map(
            request=self.request,
            content_by_url={},
            pipeline_id="PIPELINE-3031-001",
        )

        self.assertEqual(
            result.documents_acquired,
            0,
        )
        self.assertEqual(
            result.receipts_generated,
            3,
        )
        self.assertFalse(
            result.ready_for_ain302
        )

    def test_same_logical_request_has_same_plan_id(
        self,
    ) -> None:
        first_request = self.request

        second_request = ResearchRequest(
            workspace_id=first_request.workspace_id,
            organization_identifier=(
                first_request.organization_identifier
            ),
            objective=first_request.objective,
            requested_outputs=(
                first_request.requested_outputs
            ),
            constraints=first_request.constraints,
        )

        first_plan = self.service.create_plan(
            first_request,
            pipeline_id="PIPELINE-ONE",
        )

        second_plan = self.service.create_plan(
            second_request,
            pipeline_id="PIPELINE-TWO",
        )

        self.assertEqual(
            first_plan.plan_id,
            second_plan.plan_id,
        )


if __name__ == "__main__":
    unittest.main()
