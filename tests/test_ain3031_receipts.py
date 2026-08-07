from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from anchorinsight_research.models import (
    AcquisitionStatus,
    AcquiredDocument,
    CandidateSource,
)
from anchorinsight_research.receipts import (
    AcquisitionReceiptService,
    ReceiptValidationError,
)
from anchorinsight_research.storage import ResearchArtifactStore


class AcquisitionReceiptServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()

        self.store = ResearchArtifactStore(
            Path(self.temporary_directory.name)
        )

        self.service = AcquisitionReceiptService(
            store=self.store
        )

        self.source = CandidateSource(
            plan_id="PLAN-001",
            title="CPS Energy Modernization",
            url="https://example.com/cps-modernization",
            organization="CPS Energy",
            source_type="Corporate",
            authority_score=0.95,
            discovery_reason="Official organization source",
        )

        self.document = AcquiredDocument(
            plan_id=self.source.plan_id,
            source_id=self.source.source_id,
            raw_content=(
                b"CPS Energy announced an infrastructure "
                b"modernization initiative."
            ),
            media_type="text/plain",
            acquisition_method="Manual Upload",
            original_url=self.source.url,
        )

        self.store.save_candidate_source(self.source)
        self.store.save_acquired_document(self.document)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_success_receipt_is_created(self) -> None:
        receipt = self.service.create_success_receipt(
            source=self.source,
            document=self.document,
            parent_research_request_id="REQ-001",
        )

        self.assertEqual(
            receipt.status,
            AcquisitionStatus.RETRIEVED,
        )
        self.assertEqual(
            receipt.document_id,
            self.document.document_id,
        )
        self.assertEqual(
            receipt.source_hash,
            self.document.content_hash,
        )
        self.assertEqual(
            receipt.content_length,
            self.document.content_length,
        )

    def test_success_receipt_is_persisted(self) -> None:
        receipt = self.service.create_success_receipt(
            source=self.source,
            document=self.document,
            parent_research_request_id="REQ-001",
        )

        loaded = self.store.load_acquisition_receipt(
            receipt.receipt_id
        )

        self.assertEqual(
            loaded["receipt_id"],
            receipt.receipt_id,
        )
        self.assertEqual(
            loaded["status"],
            AcquisitionStatus.RETRIEVED.value,
        )

    def test_success_receipt_id_is_deterministic(self) -> None:
        first = self.service.create_success_receipt(
            source=self.source,
            document=self.document,
            parent_research_request_id="REQ-001",
        )

        second = self.service.create_success_receipt(
            source=self.source,
            document=self.document,
            parent_research_request_id="REQ-001",
        )

        self.assertEqual(
            first.receipt_id,
            second.receipt_id,
        )

    def test_success_retry_does_not_duplicate_receipt(
        self,
    ) -> None:
        self.service.create_success_receipt(
            source=self.source,
            document=self.document,
            parent_research_request_id="REQ-001",
        )

        self.service.create_success_receipt(
            source=self.source,
            document=self.document,
            parent_research_request_id="REQ-001",
        )

        receipt_files = list(
            self.store.acquisition_receipts.glob(
                "*.json"
            )
        )

        self.assertEqual(len(receipt_files), 1)

    def test_success_receipt_integrity_verifies(
        self,
    ) -> None:
        receipt = self.service.create_success_receipt(
            source=self.source,
            document=self.document,
            parent_research_request_id="REQ-001",
        )

        self.assertTrue(
            self.service.verify_integrity(receipt)
        )

    def test_success_receipt_can_be_replayed(self) -> None:
        original = self.service.create_success_receipt(
            source=self.source,
            document=self.document,
            parent_research_request_id="REQ-001",
        )

        replayed = self.service.replay(
            plan_id=self.source.plan_id,
            source_id=self.source.source_id,
            source_hash=self.document.content_hash,
        )

        self.assertIsNotNone(replayed)
        self.assertEqual(
            replayed.receipt_id,
            original.receipt_id,
        )
        self.assertEqual(
            replayed.integrity_hash,
            original.integrity_hash,
        )

    def test_unknown_replay_returns_none(self) -> None:
        replayed = self.service.replay(
            plan_id="PLAN-UNKNOWN",
            source_id="SOURCE-UNKNOWN",
            source_hash="0" * 64,
        )

        self.assertIsNone(replayed)

    def test_failure_receipt_is_created(self) -> None:
        receipt = self.service.create_failure_receipt(
            source=self.source,
            parent_research_request_id="REQ-001",
            acquisition_method="Website Retrieval",
            status=AcquisitionStatus.TIMEOUT,
            failure_reason="Source timed out.",
        )

        self.assertEqual(
            receipt.status,
            AcquisitionStatus.TIMEOUT,
        )
        self.assertIsNone(receipt.document_id)
        self.assertEqual(receipt.content_length, 0)
        self.assertEqual(
            receipt.failure_reason,
            "Source timed out.",
        )

    def test_failure_receipt_is_persisted(self) -> None:
        receipt = self.service.create_failure_receipt(
            source=self.source,
            parent_research_request_id="REQ-001",
            acquisition_method="Website Retrieval",
            status=AcquisitionStatus.NOT_FOUND,
            failure_reason="Source was not found.",
        )

        loaded = self.store.load_acquisition_receipt(
            receipt.receipt_id
        )

        self.assertEqual(
            loaded["status"],
            AcquisitionStatus.NOT_FOUND.value,
        )
        self.assertEqual(
            loaded["failure_reason"],
            "Source was not found.",
        )

    def test_failure_retry_is_idempotent(self) -> None:
        first = self.service.create_failure_receipt(
            source=self.source,
            parent_research_request_id="REQ-001",
            acquisition_method="Website Retrieval",
            status=AcquisitionStatus.TIMEOUT,
            failure_reason="Source timed out.",
        )

        second = self.service.create_failure_receipt(
            source=self.source,
            parent_research_request_id="REQ-001",
            acquisition_method="Website Retrieval",
            status=AcquisitionStatus.TIMEOUT,
            failure_reason="Source timed out.",
        )

        self.assertEqual(
            first.receipt_id,
            second.receipt_id,
        )

        self.assertEqual(
            len(
                list(
                    self.store.acquisition_receipts.glob(
                        "*.json"
                    )
                )
            ),
            1,
        )

    def test_different_failure_status_creates_new_receipt(
        self,
    ) -> None:
        timeout = self.service.create_failure_receipt(
            source=self.source,
            parent_research_request_id="REQ-001",
            acquisition_method="Website Retrieval",
            status=AcquisitionStatus.TIMEOUT,
            failure_reason="Source timed out.",
        )

        denied = self.service.create_failure_receipt(
            source=self.source,
            parent_research_request_id="REQ-001",
            acquisition_method="Website Retrieval",
            status=AcquisitionStatus.ACCESS_DENIED,
            failure_reason="Access was denied.",
        )

        self.assertNotEqual(
            timeout.receipt_id,
            denied.receipt_id,
        )

    def test_failure_receipt_integrity_verifies(
        self,
    ) -> None:
        receipt = self.service.create_failure_receipt(
            source=self.source,
            parent_research_request_id="REQ-001",
            acquisition_method="Website Retrieval",
            status=AcquisitionStatus.FAILED,
            failure_reason="Unexpected provider failure.",
        )

        self.assertTrue(
            self.service.verify_integrity(receipt)
        )

    def test_success_requires_parent_request_id(
        self,
    ) -> None:
        with self.assertRaises(
            ReceiptValidationError
        ):
            self.service.create_success_receipt(
                source=self.source,
                document=self.document,
                parent_research_request_id="",
            )

    def test_source_and_document_plan_must_match(
        self,
    ) -> None:
        mismatched_document = replace(
            self.document,
            plan_id="PLAN-OTHER",
        )

        with self.assertRaises(
            ReceiptValidationError
        ):
            self.service.create_success_receipt(
                source=self.source,
                document=mismatched_document,
                parent_research_request_id="REQ-001",
            )

    def test_source_and_document_id_must_match(
        self,
    ) -> None:
        mismatched_document = replace(
            self.document,
            source_id="SOURCE-OTHER",
        )

        with self.assertRaises(
            ReceiptValidationError
        ):
            self.service.create_success_receipt(
                source=self.source,
                document=mismatched_document,
                parent_research_request_id="REQ-001",
            )

    def test_success_requires_nonempty_document(
        self,
    ) -> None:
        empty_document = replace(
            self.document,
            raw_content=b"",
        )

        with self.assertRaises(
            ReceiptValidationError
        ):
            self.service.create_success_receipt(
                source=self.source,
                document=empty_document,
                parent_research_request_id="REQ-001",
            )

    def test_failure_requires_failure_status(
        self,
    ) -> None:
        with self.assertRaises(
            ReceiptValidationError
        ):
            self.service.create_failure_receipt(
                source=self.source,
                parent_research_request_id="REQ-001",
                acquisition_method="Website Retrieval",
                status=AcquisitionStatus.RETRIEVED,
                failure_reason="Invalid status.",
            )

    def test_failure_requires_reason(self) -> None:
        with self.assertRaises(
            ReceiptValidationError
        ):
            self.service.create_failure_receipt(
                source=self.source,
                parent_research_request_id="REQ-001",
                acquisition_method="Website Retrieval",
                status=AcquisitionStatus.TIMEOUT,
                failure_reason="",
            )

    def test_failure_requires_acquisition_method(
        self,
    ) -> None:
        with self.assertRaises(
            ReceiptValidationError
        ):
            self.service.create_failure_receipt(
                source=self.source,
                parent_research_request_id="REQ-001",
                acquisition_method="",
                status=AcquisitionStatus.TIMEOUT,
                failure_reason="Source timed out.",
            )

    def test_failure_requires_parent_request_id(
        self,
    ) -> None:
        with self.assertRaises(
            ReceiptValidationError
        ):
            self.service.create_failure_receipt(
                source=self.source,
                parent_research_request_id="",
                acquisition_method="Website Retrieval",
                status=AcquisitionStatus.TIMEOUT,
                failure_reason="Source timed out.",
            )


if __name__ == "__main__":
    unittest.main()
