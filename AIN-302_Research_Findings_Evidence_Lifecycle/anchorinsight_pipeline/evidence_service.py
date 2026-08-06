"""AIN-302 source, finding, review, and evidence-commit service."""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace
import hashlib
import json
from typing import Any, Iterable
from uuid import uuid4

from .evidence_models import (
    AdmittedSource,
    EvidenceCommitRecord,
    FindingReceipt,
    FindingStatus,
    ResearchFinding,
    ReviewDecision,
    ReviewerAuthority,
    ReviewRecord,
    SourceAdmissionStatus,
    utc_now,
)
from .evidence_store import EvidenceLifecycleStore
from .errors import PipelineValidationError


class EvidenceLifecycleService:
    VERSION = "302.1"

    def __init__(self, *, store: EvidenceLifecycleStore, registry: Any) -> None:
        self.store = store
        self.registry = registry

    def admit_source(self, source: AdmittedSource) -> AdmittedSource:
        if source.admission_status != SourceAdmissionStatus.SUBMITTED:
            raise PipelineValidationError("Only Submitted sources may enter source admission.")
        if not source.title.strip() or not source.publisher.strip() or not source.raw_content.strip():
            raise PipelineValidationError("Source title, publisher, and content are required.")
        admitted = replace(source, admission_status=SourceAdmissionStatus.ADMITTED)
        self.store.save_source(admitted)
        return admitted

    def reject_source(self, source: AdmittedSource) -> AdmittedSource:
        rejected = replace(source, admission_status=SourceAdmissionStatus.REJECTED)
        self.store.save_source(rejected)
        return rejected

    def create_finding(
        self,
        *,
        source: AdmittedSource,
        assertion: str,
        classification: str,
        confidence: float,
        model: str = "deterministic-seed",
        prompt_version: str = "AIN-302-proof-v1",
        extraction_engine: str = "deterministic-seed",
    ) -> tuple[ResearchFinding, FindingReceipt]:
        if source.admission_status != SourceAdmissionStatus.ADMITTED:
            raise PipelineValidationError("Only Admitted sources may produce findings.")
        if not 0 <= confidence <= 1:
            raise PipelineValidationError("Finding confidence must be between 0 and 1.")
        finding = ResearchFinding(
            workspace_id=source.workspace_id,
            organization_id=source.organization_id,
            source_id=source.source_id,
            assertion=assertion,
            classification=classification,
            confidence=confidence,
            model=model,
            prompt_version=prompt_version,
            extraction_engine=extraction_engine,
        )
        self.store.save_finding(finding)
        receipt = FindingReceipt.from_finding(finding)
        self.store.save_finding_receipt(receipt)
        return finding, receipt

    def correlate(self, findings: Iterable[ResearchFinding]) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for finding in findings:
            groups.setdefault(finding.assertion_hash, []).append(finding.finding_id)
        return groups

    def review(
        self,
        *,
        finding: ResearchFinding,
        reviewer: ReviewerAuthority,
        decision: ReviewDecision,
        reason: str,
    ) -> tuple[ResearchFinding, ReviewRecord]:
        if not reviewer.permits(
            workspace_id=finding.workspace_id,
            classification=finding.classification,
            action=decision,
        ):
            raise PermissionError("Reviewer does not hold current authority for this action.")

        state_map = {
            ReviewDecision.APPROVE: FindingStatus.APPROVED,
            ReviewDecision.REJECT: FindingStatus.REJECTED,
            ReviewDecision.DEFER: FindingStatus.DEFERRED,
            ReviewDecision.DISPUTE: FindingStatus.DISPUTED,
            ReviewDecision.RECLASSIFY: FindingStatus.PENDING_REVIEW,
            ReviewDecision.REQUEST_MORE_RESEARCH: FindingStatus.DEFERRED,
        }
        new_status = state_map[decision]
        review = ReviewRecord(
            finding_id=finding.finding_id,
            reviewer_id=reviewer.reviewer_id,
            authority_reference=reviewer.authority_id,
            decision=decision,
            reason=reason,
            previous_status=finding.status,
            new_status=new_status,
        )
        self.store.save_review(review)
        reviewed = replace(finding, status=new_status, disposition=decision.value)
        return reviewed, review

    def commit_evidence(
        self,
        *,
        source: AdmittedSource,
        finding: ResearchFinding,
        review: ReviewRecord,
        reviewer: ReviewerAuthority,
    ) -> EvidenceCommitRecord:
        if source.admission_status != SourceAdmissionStatus.ADMITTED:
            raise PipelineValidationError("Evidence source is not admitted.")
        if finding.status != FindingStatus.APPROVED:
            raise PipelineValidationError("Only Approved findings may be committed.")
        if review.decision != ReviewDecision.APPROVE:
            raise PipelineValidationError("Approval review is required for evidence commit.")
        if review.authority_reference != reviewer.authority_id:
            raise PipelineValidationError("Reviewer authority reference mismatch.")

        existing = self.store.find_commit_for_finding(
            finding.finding_id, finding.finding_version
        )
        if existing is not None:
            return EvidenceCommitRecord(**existing)

        evidence_id = str(uuid4())
        payload = {
            "source_id": source.source_id,
            "finding_id": finding.finding_id,
            "finding_version": finding.finding_version,
            "review_id": review.review_id,
            "reviewer_authority_reference": reviewer.authority_id,
            "evidence_classification": finding.classification,
            "confidence": finding.confidence,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        integrity_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        transaction = (
            self.registry.transaction()
            if hasattr(self.registry, "transaction")
            else nullcontext()
        )
        with transaction:
            registry_identifier = self.registry.create_evidence(
                evidence_id=evidence_id,
                organization_id=finding.organization_id,
                source_id=source.source_id,
                finding_id=finding.finding_id,
                finding_version=finding.finding_version,
                assertion=finding.assertion,
                classification=finding.classification,
                confidence=finding.confidence,
                review_id=review.review_id,
                reviewer_id=review.reviewer_id,
                authority_reference=review.authority_reference,
                source_url=source.url,
                source_title=source.title,
                source_hash=source.content_hash,
            )
            commit = EvidenceCommitRecord(
                evidence_id=evidence_id,
                registry_identifier=str(registry_identifier),
                source_id=source.source_id,
                finding_id=finding.finding_id,
                finding_version=finding.finding_version,
                review_id=review.review_id,
                reviewer_authority_reference=review.authority_reference,
                evidence_classification=finding.classification,
                confidence=finding.confidence,
                committed_at=utc_now(),
                audit_reference=f"AUD-{uuid4()}",
                integrity_hash=integrity_hash,
            )
            self.store.save_commit(commit)
        return commit
