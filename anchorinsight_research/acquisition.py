"""
AIN-303.1 Deterministic Source Acquisition.

Acquires supplied source content, preserves the original artifact,
detects duplicate content, and generates immutable acquisition receipts.

This module SHALL NOT:
- crawl the web
- call AI models
- create findings
- admit evidence
- make commercial decisions
"""

from __future__ import annotations

from dataclasses import replace
from typing import Callable

from .models import (
    AcquisitionReceipt,
    AcquisitionStatus,
    AcquiredDocument,
    CandidateSource,
    CandidateSourceStatus,
)
from .receipts import AcquisitionReceiptService
from .storage import ResearchArtifactStore


class AcquisitionError(Exception):
    """Base exception for source-acquisition failures."""


class AcquisitionValidationError(AcquisitionError):
    """Raised when acquisition inputs are invalid."""


class UnsupportedMediaTypeError(AcquisitionError):
    """Raised when supplied content uses an unsupported media type."""


class AcquisitionService:
    """Acquire candidate-source content and generate governed receipts."""

    SUPPORTED_MEDIA_TYPES = {
        "text/plain",
        "text/html",
        "application/json",
        "application/pdf",
        "application/xml",
        "text/xml",
    }

    def __init__(
        self,
        *,
        store: ResearchArtifactStore,
        receipt_service: AcquisitionReceiptService | None = None,
    ) -> None:
        self.store = store
        self.receipt_service = (
            receipt_service
            or AcquisitionReceiptService(store=store)
        )

    def acquire_bytes(
        self,
        *,
        source: CandidateSource,
        raw_content: bytes,
        media_type: str,
        acquisition_method: str,
        parent_research_request_id: str,
    ) -> tuple[AcquiredDocument | None, AcquisitionReceipt]:
        """
        Acquire supplied bytes for one candidate source.

        Returns:
            A tuple containing:
            - the newly stored AcquiredDocument, or None for a duplicate;
            - the immutable AcquisitionReceipt.
        """
        self._validate_inputs(
            source=source,
            raw_content=raw_content,
            media_type=media_type,
            acquisition_method=acquisition_method,
            parent_research_request_id=parent_research_request_id,
        )

        document = AcquiredDocument(
            plan_id=source.plan_id,
            source_id=source.source_id,
            raw_content=raw_content,
            media_type=media_type,
            acquisition_method=acquisition_method,
            original_url=source.url,
        )

        existing_document = self.store.find_document_by_hash(
            document.content_hash
        )

        if existing_document is not None:
            receipt = self.receipt_service.create_failure_receipt(
                source=source,
                parent_research_request_id=parent_research_request_id,
                acquisition_method=acquisition_method,
                status=AcquisitionStatus.DUPLICATE,
                failure_reason=(
                    "Content hash matches an existing acquired document: "
                    f"{existing_document['document_id']}"
                ),
            )
            return None, receipt

        self.store.save_acquired_document(document)

        receipt = self.receipt_service.create_success_receipt(
            source=source,
            document=document,
            parent_research_request_id=parent_research_request_id,
        )

        return document, receipt

    def acquire_text(
        self,
        *,
        source: CandidateSource,
        text: str,
        media_type: str = "text/plain",
        acquisition_method: str = "Manual Text Import",
        parent_research_request_id: str,
        encoding: str = "utf-8",
    ) -> tuple[AcquiredDocument | None, AcquisitionReceipt]:
        """Acquire text content by encoding it into immutable bytes."""
        if not text.strip():
            raise AcquisitionValidationError(
                "text content must not be blank"
            )

        return self.acquire_bytes(
            source=source,
            raw_content=text.encode(encoding),
            media_type=media_type,
            acquisition_method=acquisition_method,
            parent_research_request_id=parent_research_request_id,
        )

    def acquire_with_provider(
        self,
        *,
        source: CandidateSource,
        provider: Callable[
            [CandidateSource],
            tuple[bytes, str],
        ],
        acquisition_method: str,
        parent_research_request_id: str,
    ) -> tuple[AcquiredDocument | None, AcquisitionReceipt]:
        """
        Acquire content through a bounded provider adapter.

        The provider must return:
            (raw_content, media_type)

        Network behavior remains outside this service.
        """
        try:
            raw_content, media_type = provider(source)
        except FileNotFoundError as exc:
            return None, self.record_failure(
                source=source,
                parent_research_request_id=parent_research_request_id,
                acquisition_method=acquisition_method,
                status=AcquisitionStatus.NOT_FOUND,
                failure_reason=str(exc) or "Source was not found.",
            )
        except PermissionError as exc:
            return None, self.record_failure(
                source=source,
                parent_research_request_id=parent_research_request_id,
                acquisition_method=acquisition_method,
                status=AcquisitionStatus.ACCESS_DENIED,
                failure_reason=str(exc) or "Access was denied.",
            )
        except TimeoutError as exc:
            return None, self.record_failure(
                source=source,
                parent_research_request_id=parent_research_request_id,
                acquisition_method=acquisition_method,
                status=AcquisitionStatus.TIMEOUT,
                failure_reason=str(exc) or "Acquisition timed out.",
            )
        except UnsupportedMediaTypeError as exc:
            return None, self.record_failure(
                source=source,
                parent_research_request_id=parent_research_request_id,
                acquisition_method=acquisition_method,
                status=AcquisitionStatus.UNSUPPORTED_FORMAT,
                failure_reason=str(exc),
            )
        except Exception as exc:
            return None, self.record_failure(
                source=source,
                parent_research_request_id=parent_research_request_id,
                acquisition_method=acquisition_method,
                status=AcquisitionStatus.FAILED,
                failure_reason=str(exc) or "Unknown acquisition failure.",
            )

        return self.acquire_bytes(
            source=source,
            raw_content=raw_content,
            media_type=media_type,
            acquisition_method=acquisition_method,
            parent_research_request_id=parent_research_request_id,
        )

    def record_failure(
        self,
        *,
        source: CandidateSource,
        parent_research_request_id: str,
        acquisition_method: str,
        status: AcquisitionStatus,
        failure_reason: str,
    ) -> AcquisitionReceipt:
        """Create a governed receipt for a failed acquisition."""
        return self.receipt_service.create_failure_receipt(
            source=source,
            parent_research_request_id=parent_research_request_id,
            acquisition_method=acquisition_method,
            status=status,
            failure_reason=failure_reason,
        )

    def verify_document(
        self,
        document: AcquiredDocument,
    ) -> bool:
        """Verify persisted bytes against the document content hash."""
        stored_content = (
            self.store.load_acquired_document_content(
                document.document_id
            )
        )

        stored_metadata = (
            self.store.load_acquired_document_metadata(
                document.document_id
            )
        )

        persisted_hash = stored_metadata.get("content_hash")

        return (
            stored_content == document.raw_content
            and persisted_hash == document.content_hash
        )

    def _validate_inputs(
        self,
        *,
        source: CandidateSource,
        raw_content: bytes,
        media_type: str,
        acquisition_method: str,
        parent_research_request_id: str,
    ) -> None:
        if not source.plan_id.strip():
            raise AcquisitionValidationError(
                "source plan_id is required"
            )

        if not source.source_id.strip():
            raise AcquisitionValidationError(
                "source_id is required"
            )

        if source.status in {
            CandidateSourceStatus.REJECTED,
            CandidateSourceStatus.RESTRICTED,
        }:
            raise AcquisitionValidationError(
                f"source status {source.status.value} "
                "does not permit acquisition"
            )

        if not raw_content:
            raise AcquisitionValidationError(
                "raw_content must not be empty"
            )

        if media_type not in self.SUPPORTED_MEDIA_TYPES:
            raise UnsupportedMediaTypeError(
                f"unsupported media type: {media_type}"
            )

        if not acquisition_method.strip():
            raise AcquisitionValidationError(
                "acquisition_method is required"
            )

        if not parent_research_request_id.strip():
            raise AcquisitionValidationError(
                "parent_research_request_id is required"
            )
