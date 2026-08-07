"""
AIN-303.1 Acquisition Receipt Service.

Creates, validates, persists, and replays immutable Acquisition Receipts.

A retry involving the same plan, source, and acquired content SHALL return
the original persisted receipt rather than create a duplicate.

This module SHALL NOT:
- retrieve source content
- discover sources
- create findings
- admit evidence
- make commercial decisions
"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from typing import Any

from .models import (
    AcquisitionReceipt,
    AcquisitionStatus,
    AcquiredDocument,
    CandidateSource,
)
from .storage import ResearchArtifactStore


class ReceiptError(Exception):
    """Base exception for acquisition-receipt failures."""


class ReceiptValidationError(ReceiptError):
    """Raised when receipt inputs are invalid or inconsistent."""


class AcquisitionReceiptService:
    """Create and replay immutable acquisition receipts."""

    SUCCESS_STATUS = AcquisitionStatus.RETRIEVED

    FAILURE_STATUSES = {
        AcquisitionStatus.NOT_FOUND,
        AcquisitionStatus.ACCESS_DENIED,
        AcquisitionStatus.TIMEOUT,
        AcquisitionStatus.UNSUPPORTED_FORMAT,
        AcquisitionStatus.HASH_MISMATCH,
        AcquisitionStatus.DUPLICATE,
        AcquisitionStatus.SOURCE_RESTRICTED,
        AcquisitionStatus.FAILED,
    }

    def __init__(
        self,
        *,
        store: ResearchArtifactStore,
    ) -> None:
        self.store = store

    def create_success_receipt(
        self,
        *,
        source: CandidateSource,
        document: AcquiredDocument,
        parent_research_request_id: str,
    ) -> AcquisitionReceipt:
        """
        Create or replay a successful acquisition receipt.

        The document content hash is the source hash used for deterministic
        retry lookup.
        """
        self._validate_success_inputs(
            source=source,
            document=document,
            parent_research_request_id=parent_research_request_id,
        )

        existing = self.store.find_receipt(
            plan_id=document.plan_id,
            source_id=document.source_id,
            source_hash=document.content_hash,
        )

        if existing is not None:
            return self._receipt_from_dict(existing)

        receipt = AcquisitionReceipt(
            receipt_id=self._deterministic_receipt_id(
                plan_id=document.plan_id,
                source_id=document.source_id,
                source_hash=document.content_hash,
                status=AcquisitionStatus.RETRIEVED,
            ),
            plan_id=document.plan_id,
            source_id=document.source_id,
            document_id=document.document_id,
            acquisition_method=document.acquisition_method,
            status=AcquisitionStatus.RETRIEVED,
            source_hash=document.content_hash,
            content_length=document.content_length,
            parent_research_request_id=parent_research_request_id,
        )

        self.store.save_acquisition_receipt(receipt)
        return receipt

    def create_failure_receipt(
        self,
        *,
        source: CandidateSource,
        parent_research_request_id: str,
        acquisition_method: str,
        status: AcquisitionStatus,
        failure_reason: str,
    ) -> AcquisitionReceipt:
        """
        Create or replay a failed acquisition receipt.

        Failed acquisitions do not have an AcquiredDocument. A deterministic
        failure fingerprint is used as the source hash for retry lookup.
        """
        self._validate_failure_inputs(
            source=source,
            parent_research_request_id=parent_research_request_id,
            acquisition_method=acquisition_method,
            status=status,
            failure_reason=failure_reason,
        )

        failure_hash = self._failure_fingerprint(
            plan_id=source.plan_id,
            source_id=source.source_id,
            status=status,
            acquisition_method=acquisition_method,
            failure_reason=failure_reason,
        )

        existing = self.store.find_receipt(
            plan_id=source.plan_id,
            source_id=source.source_id,
            source_hash=failure_hash,
        )

        if existing is not None:
            return self._receipt_from_dict(existing)

        receipt = AcquisitionReceipt(
            receipt_id=self._deterministic_receipt_id(
                plan_id=source.plan_id,
                source_id=source.source_id,
                source_hash=failure_hash,
                status=status,
            ),
            plan_id=source.plan_id,
            source_id=source.source_id,
            document_id=None,
            acquisition_method=acquisition_method,
            status=status,
            source_hash=failure_hash,
            content_length=0,
            parent_research_request_id=parent_research_request_id,
            failure_reason=failure_reason,
        )

        self.store.save_acquisition_receipt(receipt)
        return receipt

    def verify_integrity(
        self,
        receipt: AcquisitionReceipt,
    ) -> bool:
        """
        Verify that a persisted receipt matches its calculated integrity hash.
        """
        stored = self.store.load_acquisition_receipt(
            receipt.receipt_id
        )

        stored_integrity = stored.get("integrity_hash")
        calculated_integrity = receipt.integrity_hash

        return stored_integrity == calculated_integrity

    def replay(
        self,
        *,
        plan_id: str,
        source_id: str,
        source_hash: str,
    ) -> AcquisitionReceipt | None:
        """Return the original receipt for a prior acquisition."""
        existing = self.store.find_receipt(
            plan_id=plan_id,
            source_id=source_id,
            source_hash=source_hash,
        )

        if existing is None:
            return None

        return self._receipt_from_dict(existing)

    def _validate_success_inputs(
        self,
        *,
        source: CandidateSource,
        document: AcquiredDocument,
        parent_research_request_id: str,
    ) -> None:
        if not parent_research_request_id.strip():
            raise ReceiptValidationError(
                "parent_research_request_id is required"
            )

        if source.plan_id != document.plan_id:
            raise ReceiptValidationError(
                "candidate source and acquired document "
                "must belong to the same research plan"
            )

        if source.source_id != document.source_id:
            raise ReceiptValidationError(
                "candidate source and acquired document "
                "must reference the same source"
            )

        if document.content_length < 1:
            raise ReceiptValidationError(
                "successful acquisition requires non-empty content"
            )

        if not document.content_hash:
            raise ReceiptValidationError(
                "successful acquisition requires a content hash"
            )

    def _validate_failure_inputs(
        self,
        *,
        source: CandidateSource,
        parent_research_request_id: str,
        acquisition_method: str,
        status: AcquisitionStatus,
        failure_reason: str,
    ) -> None:
        if not source.plan_id.strip():
            raise ReceiptValidationError(
                "source plan_id is required"
            )

        if not source.source_id.strip():
            raise ReceiptValidationError(
                "source_id is required"
            )

        if not parent_research_request_id.strip():
            raise ReceiptValidationError(
                "parent_research_request_id is required"
            )

        if not acquisition_method.strip():
            raise ReceiptValidationError(
                "acquisition_method is required"
            )

        if status not in self.FAILURE_STATUSES:
            raise ReceiptValidationError(
                f"{status.value} is not a valid failure status"
            )

        if not failure_reason.strip():
            raise ReceiptValidationError(
                "failure_reason is required"
            )

    def _deterministic_receipt_id(
        self,
        *,
        plan_id: str,
        source_id: str,
        source_hash: str,
        status: AcquisitionStatus,
    ) -> str:
        payload = {
            "plan_id": plan_id,
            "source_id": source_id,
            "source_hash": source_hash,
            "status": status.value,
        }

        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        digest = sha256(
            canonical.encode("utf-8")
        ).hexdigest()[:20]

        return f"ACQ-{digest}"

    def _failure_fingerprint(
        self,
        *,
        plan_id: str,
        source_id: str,
        status: AcquisitionStatus,
        acquisition_method: str,
        failure_reason: str,
    ) -> str:
        payload = {
            "plan_id": plan_id,
            "source_id": source_id,
            "status": status.value,
            "acquisition_method": acquisition_method.strip(),
            "failure_reason": " ".join(
                failure_reason.split()
            ).casefold(),
        }

        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        return sha256(
            canonical.encode("utf-8")
        ).hexdigest()

    def _receipt_from_dict(
        self,
        payload: dict[str, Any],
    ) -> AcquisitionReceipt:
        """Reconstruct a receipt from persisted JSON."""
        return AcquisitionReceipt(
            receipt_id=payload["receipt_id"],
            plan_id=payload["plan_id"],
            source_id=payload["source_id"],
            document_id=payload.get("document_id"),
            acquisition_method=payload[
                "acquisition_method"
            ],
            status=AcquisitionStatus(payload["status"]),
            source_hash=payload["source_hash"],
            content_length=int(payload["content_length"]),
            parent_research_request_id=payload[
                "parent_research_request_id"
            ],
            failure_reason=payload.get("failure_reason"),
            acquired_at=datetime.fromisoformat(
                payload["acquired_at"]
            ),
        )
