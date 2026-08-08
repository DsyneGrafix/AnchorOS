"""AIN-303.2 acquisition-to-evidence handoff.

This module bridges immutable AIN-303 acquisition artifacts into the AIN-302
source-admission lifecycle without granting AIN-303 authority to create or
approve findings.

Boundary:
    AIN-303 acquires and proves provenance.
    AIN-302 governs source admission, findings, review, and evidence commit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from urllib.parse import urlparse
from uuid import uuid4

from anchorinsight_pipeline.evidence_models import AdmittedSource
from anchorinsight_pipeline.evidence_service import EvidenceLifecycleService

from .models import AcquisitionReceipt, AcquisitionStatus, AcquiredDocument, CandidateSource


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceHandoffError(Exception):
    """Base exception for AIN-303.2 handoff failures."""


class HandoffIntegrityError(EvidenceHandoffError):
    """Raised when acquisition artifacts do not form one valid provenance chain."""


class UnsupportedEvidenceContent(EvidenceHandoffError):
    """Raised when acquired bytes cannot enter the text-based AIN-302 source model."""


@dataclass(frozen=True)
class EvidenceHandoffReceipt:
    """Immutable receipt proving one AIN-303 -> AIN-302 source handoff."""

    plan_id: str
    research_request_id: str
    candidate_source_id: str
    acquisition_receipt_id: str
    acquired_document_id: str
    acquired_content_hash: str
    ain302_source_id: str
    organization_id: str
    workspace_id: str
    status: str = "ADMITTED"
    handoff_id: str = field(default_factory=lambda: str(uuid4()))
    handed_off_at: datetime = field(default_factory=utc_now)

    @property
    def integrity_hash(self) -> str:
        payload = {
            "handoff_id": self.handoff_id,
            "plan_id": self.plan_id,
            "research_request_id": self.research_request_id,
            "candidate_source_id": self.candidate_source_id,
            "acquisition_receipt_id": self.acquisition_receipt_id,
            "acquired_document_id": self.acquired_document_id,
            "acquired_content_hash": self.acquired_content_hash,
            "ain302_source_id": self.ain302_source_id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "status": self.status,
            "handed_off_at": self.handed_off_at.isoformat(),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, str]:
        return {
            "handoff_id": self.handoff_id,
            "plan_id": self.plan_id,
            "research_request_id": self.research_request_id,
            "candidate_source_id": self.candidate_source_id,
            "acquisition_receipt_id": self.acquisition_receipt_id,
            "acquired_document_id": self.acquired_document_id,
            "acquired_content_hash": self.acquired_content_hash,
            "ain302_source_id": self.ain302_source_id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "status": self.status,
            "handed_off_at": self.handed_off_at.isoformat(),
            "integrity_hash": self.integrity_hash,
        }


@dataclass(frozen=True)
class EvidenceHandoffResult:
    """AIN-302 source produced from one verified AIN-303 acquisition."""

    source: AdmittedSource
    receipt: EvidenceHandoffReceipt


class EvidenceHandoffService:
    """Validate provenance and submit acquired content into AIN-302 admission."""

    VERSION = "303.2"

    TEXT_MEDIA_TYPES = frozenset(
        {
            "text/html",
            "text/plain",
            "text/markdown",
            "application/json",
            "application/xml",
            "text/xml",
            "application/xhtml+xml",
        }
    )

    def __init__(self, *, evidence_service: EvidenceLifecycleService) -> None:
        self.evidence_service = evidence_service

    def handoff(
        self,
        *,
        source: CandidateSource,
        document: AcquiredDocument,
        acquisition_receipt: AcquisitionReceipt,
        workspace_id: str,
        organization_id: str,
        publisher: str | None = None,
        authority_classification: str = "Acquired Source — Pending Finding Review",
    ) -> EvidenceHandoffResult:
        """Admit one verified acquired document as an AIN-302 source.

        This method performs source admission only. It does not create findings,
        review findings, commit evidence, score organizations, or authorize action.
        """
        self._validate_chain(
            source=source,
            document=document,
            receipt=acquisition_receipt,
        )

        raw_content = self._decode_document(document)
        resolved_publisher = publisher or self._publisher_from_url(source.url)

        submitted = AdmittedSource(
            workspace_id=workspace_id,
            organization_id=organization_id,
            title=source.title,
            publisher=resolved_publisher,
            url=source.url,
            raw_content=raw_content,
            source_type=source.source_type,
            acquisition_method=document.acquisition_method,
            authority_classification=authority_classification,
        )

        admitted = self.evidence_service.admit_source(submitted)

        handoff_receipt = EvidenceHandoffReceipt(
            plan_id=document.plan_id,
            research_request_id=acquisition_receipt.parent_research_request_id,
            candidate_source_id=source.source_id,
            acquisition_receipt_id=acquisition_receipt.receipt_id,
            acquired_document_id=document.document_id,
            acquired_content_hash=document.content_hash,
            ain302_source_id=admitted.source_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
        )

        return EvidenceHandoffResult(source=admitted, receipt=handoff_receipt)

    def _validate_chain(
        self,
        *,
        source: CandidateSource,
        document: AcquiredDocument,
        receipt: AcquisitionReceipt,
    ) -> None:
        if receipt.status != AcquisitionStatus.RETRIEVED:
            raise HandoffIntegrityError(
                f"Only RETRIEVED acquisitions may be handed to AIN-302; got {receipt.status.value}."
            )
        if source.plan_id != document.plan_id or source.plan_id != receipt.plan_id:
            raise HandoffIntegrityError("Plan identifiers do not match across handoff artifacts.")
        if source.source_id != document.source_id or source.source_id != receipt.source_id:
            raise HandoffIntegrityError("Source identifiers do not match across handoff artifacts.")
        if receipt.document_id != document.document_id:
            raise HandoffIntegrityError("Acquisition receipt does not reference the acquired document.")
        if receipt.source_hash != document.content_hash:
            raise HandoffIntegrityError("Acquisition receipt hash does not match acquired content.")
        if receipt.content_length != document.content_length:
            raise HandoffIntegrityError("Acquisition receipt length does not match acquired content.")
        if document.original_url.strip().casefold().rstrip("/") != source.normalized_url:
            raise HandoffIntegrityError("Acquired document URL does not match candidate source URL.")

    def _decode_document(self, document: AcquiredDocument) -> str:
        media_type = document.media_type.split(";", 1)[0].strip().casefold()
        if media_type not in self.TEXT_MEDIA_TYPES:
            raise UnsupportedEvidenceContent(
                f"AIN-302 text source admission does not support media type: {document.media_type}"
            )
        try:
            return document.raw_content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnsupportedEvidenceContent(
                "Acquired source is not valid UTF-8 text and cannot enter AIN-302 source admission."
            ) from exc

    @staticmethod
    def _publisher_from_url(url: str) -> str:
        host = urlparse(url).hostname
        if not host:
            raise HandoffIntegrityError("Publisher could not be derived from source URL.")
        return host.removeprefix("www.")
