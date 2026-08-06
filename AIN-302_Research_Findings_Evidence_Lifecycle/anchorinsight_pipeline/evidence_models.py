"""AIN-302 evidence-lifecycle models.

The source is the evidentiary foundation. AI-assisted findings remain
non-authoritative until an authorized human reviewer approves them.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(value: str) -> str:
    normalized = " ".join(value.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class SourceAdmissionStatus(StrEnum):
    SUBMITTED = "Submitted"
    ADMITTED = "Admitted"
    REJECTED = "Rejected"
    DUPLICATE = "Duplicate"
    RESTRICTED = "Restricted"


class FindingStatus(StrEnum):
    DRAFT = "Draft"
    PENDING_REVIEW = "Pending Review"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    DISPUTED = "Disputed"
    DEFERRED = "Deferred"
    SUPERSEDED = "Superseded"
    COMMITTED = "Committed"


class ReviewDecision(StrEnum):
    APPROVE = "Approve"
    REJECT = "Reject"
    DEFER = "Defer"
    DISPUTE = "Dispute"
    RECLASSIFY = "Reclassify"
    REQUEST_MORE_RESEARCH = "Request More Research"


@dataclass(frozen=True)
class AdmittedSource:
    workspace_id: str
    organization_id: str
    title: str
    publisher: str
    url: str
    raw_content: str
    source_type: str = "Corporate"
    admission_status: SourceAdmissionStatus = SourceAdmissionStatus.SUBMITTED
    captured_at: str = field(default_factory=utc_now)
    source_id: str = field(default_factory=lambda: str(uuid4()))
    acquisition_method: str = "manual"
    authority_classification: str = "Approved Source"

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.raw_content.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["admission_status"] = self.admission_status.value
        payload["content_hash"] = self.content_hash
        return payload


@dataclass
class ResearchFinding:
    workspace_id: str
    organization_id: str
    source_id: str
    assertion: str
    classification: str
    confidence: float
    model: str
    prompt_version: str
    extraction_engine: str = "deterministic-seed"
    finding_version: int = 1
    status: FindingStatus = FindingStatus.PENDING_REVIEW
    created_at: str = field(default_factory=utc_now)
    finding_id: str = field(default_factory=lambda: str(uuid4()))
    research_run_id: str = field(default_factory=lambda: str(uuid4()))
    supporting_excerpt_reference: str | None = None
    disposition: str = "Pending Review"

    @property
    def assertion_hash(self) -> str:
        return canonical_hash(self.assertion)

    @property
    def idempotency_key(self) -> str:
        payload = {
            "workspace_id": self.workspace_id,
            "organization_id": self.organization_id,
            "source_id": self.source_id,
            "assertion_hash": self.assertion_hash,
            "finding_version": self.finding_version,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["assertion_hash"] = self.assertion_hash
        payload["idempotency_key"] = self.idempotency_key
        return payload


@dataclass(frozen=True)
class FindingReceipt:
    finding_id: str
    finding_version: int
    source_id: str
    extraction_engine: str
    prompt_version: str
    model: str
    confidence: float
    assertion_hash: str
    created_at: str
    status: str
    disposition: str

    @classmethod
    def from_finding(cls, finding: ResearchFinding) -> "FindingReceipt":
        return cls(
            finding_id=finding.finding_id,
            finding_version=finding.finding_version,
            source_id=finding.source_id,
            extraction_engine=finding.extraction_engine,
            prompt_version=finding.prompt_version,
            model=finding.model,
            confidence=finding.confidence,
            assertion_hash=finding.assertion_hash,
            created_at=finding.created_at,
            status=finding.status.value,
            disposition=finding.disposition,
        )


@dataclass(frozen=True)
class ReviewerAuthority:
    reviewer_id: str
    workspace_id: str
    role: str
    review_scope: tuple[str, ...]
    authority_source: str
    effective_at: str
    permitted_actions: tuple[str, ...]
    expires_at: str | None = None
    revoked_at: str | None = None
    authority_id: str = field(default_factory=lambda: str(uuid4()))

    def permits(
        self,
        *,
        workspace_id: str,
        classification: str,
        action: ReviewDecision,
        now: str | None = None,
    ) -> bool:
        check_time = now or utc_now()
        if self.workspace_id != workspace_id:
            return False
        if self.revoked_at is not None and self.revoked_at <= check_time:
            return False
        if self.effective_at > check_time:
            return False
        if self.expires_at is not None and self.expires_at <= check_time:
            return False
        if action.value not in self.permitted_actions:
            return False
        return "*" in self.review_scope or classification in self.review_scope


@dataclass(frozen=True)
class ReviewRecord:
    finding_id: str
    reviewer_id: str
    authority_reference: str
    decision: ReviewDecision
    reason: str
    previous_status: FindingStatus
    new_status: FindingStatus
    reviewed_at: str = field(default_factory=utc_now)
    review_id: str = field(default_factory=lambda: str(uuid4()))
    audit_reference: str = field(default_factory=lambda: f"AUD-{uuid4()}")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        payload["previous_status"] = self.previous_status.value
        payload["new_status"] = self.new_status.value
        return payload


@dataclass(frozen=True)
class EvidenceCommitRecord:
    evidence_id: str
    registry_identifier: str
    source_id: str
    finding_id: str
    finding_version: int
    review_id: str
    reviewer_authority_reference: str
    evidence_classification: str
    confidence: float
    committed_at: str
    audit_reference: str
    integrity_hash: str
