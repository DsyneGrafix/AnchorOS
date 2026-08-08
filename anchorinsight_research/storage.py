"""
AIN-303 Research Artifact Storage.

Provides filesystem persistence for Research Plans, Candidate Sources,
Acquired Documents, Acquisition Receipts, and AIN-303.2 Evidence Handoff
Receipts.

Stored metadata is JSON. Original acquired content is preserved as immutable
binary data and is never silently overwritten.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    AcquisitionReceipt,
    AcquiredDocument,
    CandidateSource,
    ResearchPlan,
)


class ResearchStorageError(Exception):
    """Base exception for research-storage failures."""


class ImmutableArtifactConflict(ResearchStorageError):
    """Raised when an immutable artifact would be overwritten."""


class ArtifactNotFound(ResearchStorageError):
    """Raised when a requested artifact does not exist."""


class ResearchArtifactStore:
    """Filesystem-backed persistence for AIN-303 research artifacts."""

    PLAN_DIRECTORY = "research_plans"
    SOURCE_DIRECTORY = "candidate_sources"
    DOCUMENT_DIRECTORY = "acquired_documents"
    RECEIPT_DIRECTORY = "acquisition_receipts"
    HANDOFF_RECEIPT_DIRECTORY = "evidence_handoff_receipts"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

        self.research_plans = self.root / self.PLAN_DIRECTORY
        self.candidate_sources = self.root / self.SOURCE_DIRECTORY
        self.acquired_documents = self.root / self.DOCUMENT_DIRECTORY
        self.acquisition_receipts = self.root / self.RECEIPT_DIRECTORY
        self.evidence_handoff_receipts = self.root / self.HANDOFF_RECEIPT_DIRECTORY

        for directory in (
            self.research_plans,
            self.candidate_sources,
            self.acquired_documents,
            self.acquisition_receipts,
            self.evidence_handoff_receipts,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def save_plan(self, plan: ResearchPlan) -> Path:
        """Persist an immutable Research Plan."""
        path = self.research_plans / f"{plan.plan_id}.json"
        return self._write_json_once(path, plan.to_dict())

    def load_plan(self, plan_id: str) -> dict[str, Any]:
        """Load a persisted Research Plan."""
        return self._read_json(
            self.research_plans / f"{plan_id}.json"
        )

    def save_candidate_source(
        self,
        source: CandidateSource,
    ) -> Path:
        """Persist an immutable Candidate Source."""
        path = self.candidate_sources / f"{source.source_id}.json"
        return self._write_json_once(path, source.to_dict())

    def load_candidate_source(
        self,
        source_id: str,
    ) -> dict[str, Any]:
        """Load a persisted Candidate Source."""
        return self._read_json(
            self.candidate_sources / f"{source_id}.json"
        )

    def find_candidate_by_fingerprint(
        self,
        source_fingerprint: str,
    ) -> dict[str, Any] | None:
        """Return an existing source with the same deterministic fingerprint."""
        for path in self.candidate_sources.glob("*.json"):
            payload = self._read_json(path)

            if payload.get("source_fingerprint") == source_fingerprint:
                return payload

        return None

    def save_acquired_document(
        self,
        document: AcquiredDocument,
    ) -> tuple[Path, Path]:
        """Preserve original source bytes and immutable metadata."""
        content_path = (
            self.acquired_documents / f"{document.document_id}.bin"
        )
        metadata_path = (
            self.acquired_documents / f"{document.document_id}.json"
        )

        self._write_bytes_once(content_path, document.raw_content)
        self._write_json_once(
            metadata_path,
            document.metadata_dict(),
        )

        return content_path, metadata_path

    def load_acquired_document_metadata(
        self,
        document_id: str,
    ) -> dict[str, Any]:
        """Load metadata for an acquired document."""
        return self._read_json(
            self.acquired_documents / f"{document_id}.json"
        )

    def load_acquired_document_content(
        self,
        document_id: str,
    ) -> bytes:
        """Load the immutable original document bytes."""
        path = self.acquired_documents / f"{document_id}.bin"

        if not path.exists():
            raise ArtifactNotFound(
                f"Acquired document content was not found: {document_id}"
            )

        return path.read_bytes()

    def find_document_by_hash(
        self,
        content_hash: str,
    ) -> dict[str, Any] | None:
        """Return existing document metadata with the same content hash."""
        for path in self.acquired_documents.glob("*.json"):
            payload = self._read_json(path)

            if payload.get("content_hash") == content_hash:
                return payload

        return None

    def save_acquisition_receipt(
        self,
        receipt: AcquisitionReceipt,
    ) -> Path:
        """Persist an immutable Acquisition Receipt."""
        path = (
            self.acquisition_receipts
            / f"{receipt.receipt_id}.json"
        )
        return self._write_json_once(path, receipt.to_dict())

    def load_acquisition_receipt(
        self,
        receipt_id: str,
    ) -> dict[str, Any]:
        """Load a persisted Acquisition Receipt."""
        return self._read_json(
            self.acquisition_receipts / f"{receipt_id}.json"
        )

    def find_receipt(
        self,
        *,
        plan_id: str,
        source_id: str,
        source_hash: str,
    ) -> dict[str, Any] | None:
        """Locate an existing receipt for deterministic acquisition replay."""
        for path in self.acquisition_receipts.glob("*.json"):
            payload = self._read_json(path)

            if (
                payload.get("plan_id") == plan_id
                and payload.get("source_id") == source_id
                and payload.get("source_hash") == source_hash
            ):
                return payload

        return None

    def save_evidence_handoff_receipt(self, receipt: Any) -> Path:
        """Persist an immutable AIN-303.2 evidence-handoff receipt."""
        payload = receipt.to_dict()
        path = self.evidence_handoff_receipts / f"{payload['handoff_id']}.json"
        return self._write_json_once(path, payload)

    def load_evidence_handoff_receipt(self, handoff_id: str) -> dict[str, Any]:
        """Load an AIN-303.2 evidence-handoff receipt."""
        return self._read_json(
            self.evidence_handoff_receipts / f"{handoff_id}.json"
        )

    def _write_json_once(
        self,
        path: Path,
        payload: dict[str, Any],
    ) -> Path:
        """Write JSON once or verify the existing immutable payload."""
        serialized = json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )

        if path.exists():
            existing = path.read_text(encoding="utf-8")

            if existing != serialized:
                raise ImmutableArtifactConflict(
                    f"Immutable artifact already exists with "
                    f"different content: {path}"
                )

            return path

        path.write_text(serialized, encoding="utf-8")
        return path

    def _write_bytes_once(
        self,
        path: Path,
        payload: bytes,
    ) -> Path:
        """Write binary content once or verify the existing bytes."""
        if path.exists():
            existing = path.read_bytes()

            if existing != payload:
                raise ImmutableArtifactConflict(
                    f"Immutable binary artifact already exists with "
                    f"different content: {path}"
                )

            return path

        path.write_bytes(payload)
        return path

    def _read_json(
        self,
        path: Path,
    ) -> dict[str, Any]:
        """Read a JSON artifact or raise a clear error."""
        if not path.exists():
            raise ArtifactNotFound(
                f"Research artifact was not found: {path}"
            )

        return json.loads(path.read_text(encoding="utf-8"))
