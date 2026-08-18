from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from anchorinsight_research.models import (
    AcquisitionReceipt,
    AcquisitionStatus,
    AcquiredDocument,
    CandidateSource,
    ResearchRequest,
)
from anchorinsight_research.planning import ResearchPlanningService
from anchorinsight_research.storage import (
    ArtifactNotFound,
    ImmutableArtifactConflict,
    ResearchArtifactStore,
)


class ResearchArtifactStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.store = ResearchArtifactStore(self.root)

        self.request = ResearchRequest(
            workspace_id="SLS-DEMO-001",
            organization_identifier="COF-ORG-2026-001",
            objective=(
                "Identify evidence of infrastructure modernization, "
                "communications investment, and grid technology initiatives."
            ),
            requested_outputs=(
                "Candidate Sources",
                "Acquisition Receipts",
            ),
        )

        self.plan = ResearchPlanningService().create_plan(
            self.request,
            pipeline_id="PIPELINE-001",
        )

        self.source = CandidateSource(
            plan_id=self.plan.plan_id,
            title="CPS Energy Modernization",
            url="https://example.com/cps-modernization",
            organization="CPS Energy",
            source_type="Corporate",
            authority_score=0.95,
            discovery_reason="Official organization source",
        )

        self.document = AcquiredDocument(
            plan_id=self.plan.plan_id,
            source_id=self.source.source_id,
            raw_content=(
                b"CPS Energy announced a modernization initiative."
            ),
            media_type="text/plain",
            acquisition_method="Manual Upload",
            original_url=self.source.url,
        )

        self.receipt = AcquisitionReceipt(
            plan_id=self.plan.plan_id,
            source_id=self.source.source_id,
            document_id=self.document.document_id,
            acquisition_method=self.document.acquisition_method,
            status=AcquisitionStatus.RETRIEVED,
            source_hash=self.document.content_hash,
            content_length=self.document.content_length,
            parent_research_request_id=self.request.request_id,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_repository_directories_are_created(self) -> None:
        self.assertTrue(self.store.research_plans.is_dir())
        self.assertTrue(self.store.candidate_sources.is_dir())
        self.assertTrue(self.store.acquired_documents.is_dir())
        self.assertTrue(self.store.acquisition_receipts.is_dir())

    def test_plan_can_be_saved_and_loaded(self) -> None:
        path = self.store.save_plan(self.plan)
        loaded = self.store.load_plan(self.plan.plan_id)

        self.assertTrue(path.exists())
        self.assertEqual(loaded["plan_id"], self.plan.plan_id)
        self.assertEqual(
            loaded["organization_identifier"],
            "COF-ORG-2026-001",
        )
        self.assertEqual(
            loaded["organization"],
            "COF-ORG-2026-001",
        )
        self.assertEqual(loaded["status"], "PLANNED")

    def test_saving_identical_plan_is_idempotent(self) -> None:
        first = self.store.save_plan(self.plan)
        second = self.store.save_plan(self.plan)

        self.assertEqual(first, second)
        self.assertEqual(
            len(list(self.store.research_plans.glob("*.json"))),
            1,
        )

    def test_candidate_source_can_be_saved_and_loaded(self) -> None:
        path = self.store.save_candidate_source(self.source)
        loaded = self.store.load_candidate_source(
            self.source.source_id
        )

        self.assertTrue(path.exists())
        self.assertEqual(loaded["source_id"], self.source.source_id)
        self.assertEqual(
            loaded["source_fingerprint"],
            self.source.source_fingerprint,
        )

    def test_candidate_source_can_be_found_by_fingerprint(self) -> None:
        self.store.save_candidate_source(self.source)

        found = self.store.find_candidate_by_fingerprint(
            self.source.source_fingerprint
        )

        self.assertIsNotNone(found)
        self.assertEqual(found["source_id"], self.source.source_id)

    def test_unknown_candidate_fingerprint_returns_none(self) -> None:
        found = self.store.find_candidate_by_fingerprint(
            "0" * 64
        )

        self.assertIsNone(found)

    def test_acquired_document_content_and_metadata_are_preserved(
        self,
    ) -> None:
        content_path, metadata_path = (
            self.store.save_acquired_document(self.document)
        )

        loaded_content = (
            self.store.load_acquired_document_content(
                self.document.document_id
            )
        )
        loaded_metadata = (
            self.store.load_acquired_document_metadata(
                self.document.document_id
            )
        )

        self.assertTrue(content_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            loaded_content,
            self.document.raw_content,
        )
        self.assertEqual(
            loaded_metadata["content_hash"],
            self.document.content_hash,
        )
        self.assertEqual(
            loaded_metadata["content_length"],
            self.document.content_length,
        )

    def test_acquired_document_can_be_found_by_hash(self) -> None:
        self.store.save_acquired_document(self.document)

        found = self.store.find_document_by_hash(
            self.document.content_hash
        )

        self.assertIsNotNone(found)
        self.assertEqual(
            found["document_id"],
            self.document.document_id,
        )

    def test_unknown_document_hash_returns_none(self) -> None:
        found = self.store.find_document_by_hash(
            "f" * 64
        )

        self.assertIsNone(found)

    def test_acquisition_receipt_can_be_saved_and_loaded(
        self,
    ) -> None:
        path = self.store.save_acquisition_receipt(
            self.receipt
        )
        loaded = self.store.load_acquisition_receipt(
            self.receipt.receipt_id
        )

        self.assertTrue(path.exists())
        self.assertEqual(
            loaded["receipt_id"],
            self.receipt.receipt_id,
        )
        self.assertEqual(
            loaded["status"],
            AcquisitionStatus.RETRIEVED.value,
        )
        self.assertEqual(
            loaded["integrity_hash"],
            self.receipt.integrity_hash,
        )

    def test_receipt_can_be_found_for_replay(self) -> None:
        self.store.save_acquisition_receipt(
            self.receipt
        )

        found = self.store.find_receipt(
            plan_id=self.plan.plan_id,
            source_id=self.source.source_id,
            source_hash=self.document.content_hash,
        )

        self.assertIsNotNone(found)
        self.assertEqual(
            found["receipt_id"],
            self.receipt.receipt_id,
        )

    def test_unknown_receipt_returns_none(self) -> None:
        found = self.store.find_receipt(
            plan_id="PLAN-UNKNOWN",
            source_id="SOURCE-UNKNOWN",
            source_hash="0" * 64,
        )

        self.assertIsNone(found)

    def test_missing_plan_raises_clear_error(self) -> None:
        with self.assertRaises(ArtifactNotFound):
            self.store.load_plan("PLAN-MISSING")

    def test_missing_document_content_raises_clear_error(
        self,
    ) -> None:
        with self.assertRaises(ArtifactNotFound):
            self.store.load_acquired_document_content(
                "DOCUMENT-MISSING"
            )

    def test_conflicting_json_artifact_is_rejected(self) -> None:
        self.store.save_plan(self.plan)

        path = (
            self.store.research_plans
            / f"{self.plan.plan_id}.json"
        )
        path.write_text(
            '{"tampered": true}',
            encoding="utf-8",
        )

        with self.assertRaises(
            ImmutableArtifactConflict
        ):
            self.store.save_plan(self.plan)

    def test_conflicting_binary_artifact_is_rejected(
        self,
    ) -> None:
        self.store.save_acquired_document(self.document)

        content_path = (
            self.store.acquired_documents
            / f"{self.document.document_id}.bin"
        )
        content_path.write_bytes(b"tampered content")

        with self.assertRaises(
            ImmutableArtifactConflict
        ):
            self.store.save_acquired_document(
                self.document
            )

    def test_full_artifact_chain_persists(self) -> None:
        self.store.save_plan(self.plan)
        self.store.save_candidate_source(self.source)
        self.store.save_acquired_document(self.document)
        self.store.save_acquisition_receipt(
            self.receipt
        )

        self.assertEqual(
            self.store.load_plan(
                self.plan.plan_id
            )["request_id"],
            self.request.request_id,
        )
        self.assertEqual(
            self.store.load_candidate_source(
                self.source.source_id
            )["plan_id"],
            self.plan.plan_id,
        )
        self.assertEqual(
            self.store.load_acquired_document_metadata(
                self.document.document_id
            )["source_id"],
            self.source.source_id,
        )
        self.assertEqual(
            self.store.load_acquisition_receipt(
                self.receipt.receipt_id
            )["document_id"],
            self.document.document_id,
        )


if __name__ == "__main__":
    unittest.main()
