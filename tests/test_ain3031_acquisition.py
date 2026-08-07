from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from anchorinsight_research.acquisition import (
    AcquisitionService,
    AcquisitionValidationError,
    UnsupportedMediaTypeError,
)
from anchorinsight_research.models import (
    AcquisitionStatus,
    CandidateSource,
    CandidateSourceStatus,
)
from anchorinsight_research.storage import ResearchArtifactStore


class AcquisitionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.store = ResearchArtifactStore(
            Path(self.temporary_directory.name)
        )
        self.service = AcquisitionService(store=self.store)

        self.source = CandidateSource(
            plan_id="PLAN-001",
            title="CPS Energy Modernization",
            url="https://example.com/cps-modernization",
            organization="CPS Energy",
            source_type="Corporate",
            authority_score=0.95,
            discovery_reason="Official organization source",
        )

        self.store.save_candidate_source(self.source)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_text_content_can_be_acquired(self) -> None:
        document, receipt = self.service.acquire_text(
            source=self.source,
            text=(
                "CPS Energy announced an infrastructure "
                "modernization initiative."
            ),
            parent_research_request_id="REQ-001",
        )

        self.assertIsNotNone(document)
        self.assertEqual(
            receipt.status,
            AcquisitionStatus.RETRIEVED,
        )
        self.assertEqual(
            receipt.document_id,
            document.document_id,
        )

    def test_binary_content_can_be_acquired(self) -> None:
        document, receipt = self.service.acquire_bytes(
            source=self.source,
            raw_content=b'{"status": "modernization announced"}',
            media_type="application/json",
            acquisition_method="Manual File Import",
            parent_research_request_id="REQ-001",
        )

        self.assertIsNotNone(document)
        self.assertEqual(
            document.media_type,
            "application/json",
        )
        self.assertEqual(
            receipt.content_length,
            document.content_length,
        )

    def test_acquired_document_is_persisted(self) -> None:
        document, _ = self.service.acquire_text(
            source=self.source,
            text="CPS Energy announced a modernization program.",
            parent_research_request_id="REQ-001",
        )

        loaded_content = (
            self.store.load_acquired_document_content(
                document.document_id
            )
        )
        loaded_metadata = (
            self.store.load_acquired_document_metadata(
                document.document_id
            )
        )

        self.assertEqual(
            loaded_content,
            document.raw_content,
        )
        self.assertEqual(
            loaded_metadata["content_hash"],
            document.content_hash,
        )

    def test_acquisition_receipt_is_persisted(self) -> None:
        _, receipt = self.service.acquire_text(
            source=self.source,
            text="CPS Energy announced a modernization program.",
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

    def test_document_hash_verification_passes(self) -> None:
        document, _ = self.service.acquire_text(
            source=self.source,
            text="CPS Energy announced a modernization program.",
            parent_research_request_id="REQ-001",
        )

        self.assertTrue(
            self.service.verify_document(document)
        )

    def test_duplicate_content_is_not_stored_twice(self) -> None:
        second_source = CandidateSource(
            plan_id="PLAN-001",
            title="Second CPS Energy Source",
            url="https://example.com/cps-second",
            organization="CPS Energy",
            source_type="Corporate",
            authority_score=0.90,
            discovery_reason="Secondary approved source",
        )
        self.store.save_candidate_source(second_source)

        content = "Identical modernization announcement."

        first_document, first_receipt = (
            self.service.acquire_text(
                source=self.source,
                text=content,
                parent_research_request_id="REQ-001",
            )
        )

        second_document, second_receipt = (
            self.service.acquire_text(
                source=second_source,
                text=content,
                parent_research_request_id="REQ-001",
            )
        )

        self.assertIsNotNone(first_document)
        self.assertEqual(
            first_receipt.status,
            AcquisitionStatus.RETRIEVED,
        )
        self.assertIsNone(second_document)
        self.assertEqual(
            second_receipt.status,
            AcquisitionStatus.DUPLICATE,
        )
        self.assertEqual(
            len(
                list(
                    self.store.acquired_documents.glob(
                        "*.bin"
                    )
                )
            ),
            1,
        )

    def test_blank_text_is_rejected(self) -> None:
        with self.assertRaises(
            AcquisitionValidationError
        ):
            self.service.acquire_text(
                source=self.source,
                text="   ",
                parent_research_request_id="REQ-001",
            )

    def test_empty_bytes_are_rejected(self) -> None:
        with self.assertRaises(
            AcquisitionValidationError
        ):
            self.service.acquire_bytes(
                source=self.source,
                raw_content=b"",
                media_type="text/plain",
                acquisition_method="Manual Import",
                parent_research_request_id="REQ-001",
            )

    def test_unsupported_media_type_is_rejected(self) -> None:
        with self.assertRaises(
            UnsupportedMediaTypeError
        ):
            self.service.acquire_bytes(
                source=self.source,
                raw_content=b"binary source",
                media_type="application/octet-stream",
                acquisition_method="Manual Import",
                parent_research_request_id="REQ-001",
            )

    def test_restricted_source_is_rejected(self) -> None:
        restricted_source = replace(
            self.source,
            status=CandidateSourceStatus.RESTRICTED,
        )

        with self.assertRaises(
            AcquisitionValidationError
        ):
            self.service.acquire_text(
                source=restricted_source,
                text="Restricted content",
                parent_research_request_id="REQ-001",
            )

    def test_rejected_source_is_rejected(self) -> None:
        rejected_source = replace(
            self.source,
            status=CandidateSourceStatus.REJECTED,
        )

        with self.assertRaises(
            AcquisitionValidationError
        ):
            self.service.acquire_text(
                source=rejected_source,
                text="Rejected content",
                parent_research_request_id="REQ-001",
            )

    def test_parent_request_id_is_required(self) -> None:
        with self.assertRaises(
            AcquisitionValidationError
        ):
            self.service.acquire_text(
                source=self.source,
                text="Valid content",
                parent_research_request_id="",
            )

    def test_acquisition_method_is_required(self) -> None:
        with self.assertRaises(
            AcquisitionValidationError
        ):
            self.service.acquire_bytes(
                source=self.source,
                raw_content=b"Valid content",
                media_type="text/plain",
                acquisition_method="",
                parent_research_request_id="REQ-001",
            )

    def test_provider_success_is_acquired(self) -> None:
        def provider(
            source: CandidateSource,
        ) -> tuple[bytes, str]:
            return (
                b"CPS Energy modernization source",
                "text/plain",
            )

        document, receipt = (
            self.service.acquire_with_provider(
                source=self.source,
                provider=provider,
                acquisition_method="Test Provider",
                parent_research_request_id="REQ-001",
            )
        )

        self.assertIsNotNone(document)
        self.assertEqual(
            receipt.status,
            AcquisitionStatus.RETRIEVED,
        )

    def test_provider_not_found_creates_failure_receipt(
        self,
    ) -> None:
        def provider(
            source: CandidateSource,
        ) -> tuple[bytes, str]:
            raise FileNotFoundError("Source not found")

        document, receipt = (
            self.service.acquire_with_provider(
                source=self.source,
                provider=provider,
                acquisition_method="Test Provider",
                parent_research_request_id="REQ-001",
            )
        )

        self.assertIsNone(document)
        self.assertEqual(
            receipt.status,
            AcquisitionStatus.NOT_FOUND,
        )
        self.assertEqual(
            receipt.failure_reason,
            "Source not found",
        )

    def test_provider_permission_failure_creates_receipt(
        self,
    ) -> None:
        def provider(
            source: CandidateSource,
        ) -> tuple[bytes, str]:
            raise PermissionError("Access denied")

        document, receipt = (
            self.service.acquire_with_provider(
                source=self.source,
                provider=provider,
                acquisition_method="Test Provider",
                parent_research_request_id="REQ-001",
            )
        )

        self.assertIsNone(document)
        self.assertEqual(
            receipt.status,
            AcquisitionStatus.ACCESS_DENIED,
        )

    def test_provider_timeout_creates_failure_receipt(
        self,
    ) -> None:
        def provider(
            source: CandidateSource,
        ) -> tuple[bytes, str]:
            raise TimeoutError("Provider timed out")

        document, receipt = (
            self.service.acquire_with_provider(
                source=self.source,
                provider=provider,
                acquisition_method="Test Provider",
                parent_research_request_id="REQ-001",
            )
        )

        self.assertIsNone(document)
        self.assertEqual(
            receipt.status,
            AcquisitionStatus.TIMEOUT,
        )

    def test_provider_unknown_failure_creates_receipt(
        self,
    ) -> None:
        def provider(
            source: CandidateSource,
        ) -> tuple[bytes, str]:
            raise RuntimeError("Unexpected failure")

        document, receipt = (
            self.service.acquire_with_provider(
                source=self.source,
                provider=provider,
                acquisition_method="Test Provider",
                parent_research_request_id="REQ-001",
            )
        )

        self.assertIsNone(document)
        self.assertEqual(
            receipt.status,
            AcquisitionStatus.FAILED,
        )
        self.assertEqual(
            receipt.failure_reason,
            "Unexpected failure",
        )

    def test_failure_receipt_retry_is_idempotent(
        self,
    ) -> None:
        first = self.service.record_failure(
            source=self.source,
            parent_research_request_id="REQ-001",
            acquisition_method="Test Provider",
            status=AcquisitionStatus.TIMEOUT,
            failure_reason="Provider timed out",
        )

        second = self.service.record_failure(
            source=self.source,
            parent_research_request_id="REQ-001",
            acquisition_method="Test Provider",
            status=AcquisitionStatus.TIMEOUT,
            failure_reason="Provider timed out",
        )

        self.assertEqual(
            first.receipt_id,
            second.receipt_id,
        )

    def test_success_receipt_integrity_is_valid(self) -> None:
        _, receipt = self.service.acquire_text(
            source=self.source,
            text="CPS Energy modernization evidence.",
            parent_research_request_id="REQ-001",
        )

        self.assertTrue(
            self.service.receipt_service.verify_integrity(
                receipt
            )
        )


if __name__ == "__main__":
    unittest.main()
