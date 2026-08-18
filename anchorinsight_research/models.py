"""
AIN-303.1 Research Planning & Acquisition Core models.

These models represent research requests, deterministic research plans,
candidate sources, acquired documents, and acquisition receipts.

This module contains data structures only. It does not perform discovery,
network acquisition, AI reasoning, evidence admission, or commercial scoring.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def normalize_text(value: str) -> str:
    """Normalize text for deterministic hashing and comparison."""
    return " ".join(value.split()).casefold()


def sha256_text(value: str) -> str:
    """Return a SHA-256 hash for UTF-8 text."""
    return sha256(value.encode("utf-8")).hexdigest()


class ResearchPlanStatus(StrEnum):
    """Lifecycle states for a research plan."""

    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CandidateSourceStatus(StrEnum):
    """Lifecycle states for discovered candidate sources."""

    DISCOVERED = "DISCOVERED"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    RESTRICTED = "RESTRICTED"
    ACQUIRED = "ACQUIRED"
    FAILED = "FAILED"


class AcquisitionStatus(StrEnum):
    """Possible outcomes of a source-acquisition attempt."""

    RETRIEVED = "RETRIEVED"
    NOT_FOUND = "NOT_FOUND"
    ACCESS_DENIED = "ACCESS_DENIED"
    TIMEOUT = "TIMEOUT"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    HASH_MISMATCH = "HASH_MISMATCH"
    DUPLICATE = "DUPLICATE"
    SOURCE_RESTRICTED = "SOURCE_RESTRICTED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ResearchRequest:
    """A bounded request for commercial research acquisition."""

    workspace_id: str
    organization_identifier: str
    objective: str
    requested_outputs: tuple[str, ...]
    constraints: tuple[str, ...] = ()
    request_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)

    @property
    def request_fingerprint(self) -> str:
        """Create a deterministic fingerprint for the logical request."""
        payload = {
            "workspace_id": normalize_text(self.workspace_id),
            "organization_identifier": normalize_text(
                self.organization_identifier
            ),
            "objective": normalize_text(self.objective),
            "requested_outputs": sorted(self.requested_outputs),
            "constraints": sorted(self.constraints),
        }
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256_text(canonical)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "request_id": self.request_id,
            "workspace_id": self.workspace_id,
            "organization_identifier": self.organization_identifier,
            "objective": self.objective,
            "requested_outputs": list(self.requested_outputs),
            "constraints": list(self.constraints),
            "created_at": self.created_at.isoformat(),
            "request_fingerprint": self.request_fingerprint,
        }


@dataclass(frozen=True)
class ResearchPlan:
    """A deterministic execution plan derived from a ResearchRequest."""

    plan_id: str
    request_id: str
    organization_identifier: str
    research_categories: tuple[str, ...]
    priority_sources: tuple[str, ...]
    maximum_sources: int
    time_window: str
    acquisition_strategy: str
    expected_outputs: tuple[str, ...]
    workspace: str
    pipeline_id: str
    status: ResearchPlanStatus = ResearchPlanStatus.PLANNED
    created_at: datetime = field(default_factory=utc_now)

    @property
    def organization(self) -> str:
        """Return the canonical identifier through the legacy field name."""
        return self.organization_identifier

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "plan_id": self.plan_id,
            "request_id": self.request_id,
            "organization_identifier": self.organization_identifier,
            # Preserve the historical serialized key for readers that have
            # not yet migrated. Its value is the canonical identifier.
            "organization": self.organization_identifier,
            "research_categories": list(self.research_categories),
            "priority_sources": list(self.priority_sources),
            "maximum_sources": self.maximum_sources,
            "time_window": self.time_window,
            "acquisition_strategy": self.acquisition_strategy,
            "expected_outputs": list(self.expected_outputs),
            "workspace": self.workspace,
            "pipeline_id": self.pipeline_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class CandidateSource:
    """A discovered but not yet authoritative research source."""

    plan_id: str
    title: str
    url: str
    organization: str
    source_type: str
    authority_score: float
    discovery_reason: str
    source_id: str = field(default_factory=lambda: str(uuid4()))
    discovered_at: datetime = field(default_factory=utc_now)
    status: CandidateSourceStatus = CandidateSourceStatus.DISCOVERED

    @property
    def normalized_url(self) -> str:
        """Return a normalized URL value for duplicate checks."""
        return self.url.strip().casefold().rstrip("/")

    @property
    def source_fingerprint(self) -> str:
        """Create a deterministic fingerprint for duplicate suppression."""
        payload = {
            "plan_id": self.plan_id,
            "normalized_url": self.normalized_url,
            "title": normalize_text(self.title),
            "organization": normalize_text(self.organization),
        }
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256_text(canonical)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "source_id": self.source_id,
            "plan_id": self.plan_id,
            "title": self.title,
            "url": self.url,
            "organization": self.organization,
            "source_type": self.source_type,
            "authority_score": self.authority_score,
            "discovery_reason": self.discovery_reason,
            "discovered_at": self.discovered_at.isoformat(),
            "status": self.status.value,
            "source_fingerprint": self.source_fingerprint,
        }


@dataclass(frozen=True)
class AcquiredDocument:
    """Immutable original content acquired from a candidate source."""

    plan_id: str
    source_id: str
    raw_content: bytes
    media_type: str
    acquisition_method: str
    original_url: str
    document_id: str = field(default_factory=lambda: str(uuid4()))
    acquired_at: datetime = field(default_factory=utc_now)

    @property
    def content_length(self) -> int:
        """Return the acquired content size in bytes."""
        return len(self.raw_content)

    @property
    def content_hash(self) -> str:
        """Return the immutable SHA-256 hash of the original content."""
        return sha256(self.raw_content).hexdigest()

    def metadata_dict(self) -> dict[str, Any]:
        """Return metadata without embedding raw document bytes."""
        return {
            "document_id": self.document_id,
            "plan_id": self.plan_id,
            "source_id": self.source_id,
            "media_type": self.media_type,
            "acquisition_method": self.acquisition_method,
            "original_url": self.original_url,
            "acquired_at": self.acquired_at.isoformat(),
            "content_length": self.content_length,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True)
class AcquisitionReceipt:
    """Immutable receipt describing one source-acquisition result."""

    plan_id: str
    source_id: str
    acquisition_method: str
    status: AcquisitionStatus
    source_hash: str
    content_length: int
    parent_research_request_id: str
    document_id: str | None = None
    failure_reason: str | None = None
    receipt_id: str = field(default_factory=lambda: str(uuid4()))
    acquired_at: datetime = field(default_factory=utc_now)

    @property
    def integrity_hash(self) -> str:
        """Create an integrity hash for the receipt contents."""
        payload = {
            "receipt_id": self.receipt_id,
            "plan_id": self.plan_id,
            "source_id": self.source_id,
            "document_id": self.document_id,
            "acquisition_method": self.acquisition_method,
            "status": self.status.value,
            "source_hash": self.source_hash,
            "content_length": self.content_length,
            "parent_research_request_id": self.parent_research_request_id,
            "failure_reason": self.failure_reason,
            "acquired_at": self.acquired_at.isoformat(),
        }
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256_text(canonical)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "receipt_id": self.receipt_id,
            "plan_id": self.plan_id,
            "source_id": self.source_id,
            "document_id": self.document_id,
            "acquisition_method": self.acquisition_method,
            "status": self.status.value,
            "source_hash": self.source_hash,
            "content_length": self.content_length,
            "parent_research_request_id": self.parent_research_request_id,
            "failure_reason": self.failure_reason,
            "acquired_at": self.acquired_at.isoformat(),
            "integrity_hash": self.integrity_hash,
        }
