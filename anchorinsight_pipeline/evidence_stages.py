"""AIN-302 pipeline stages."""
from __future__ import annotations

from .context import PipelineContext
from .evidence_models import ReviewDecision, SourceAdmissionStatus
from .stage import PipelineStage, StageExecution


class SourceAdmissionStage(PipelineStage):
    name = "Source Admission"
    version = "302.1"

    def execute(self, context: PipelineContext) -> StageExecution:
        lifecycle = context.service("evidence_lifecycle")
        sources = context.data.get("submitted_sources", [])
        admitted = []
        rejected = []
        for source in sources:
            if source.admission_status == SourceAdmissionStatus.RESTRICTED:
                rejected.append(source)
                continue
            admitted.append(lifecycle.admit_source(source))
        context.data["admitted_sources"] = admitted
        context.data["rejected_sources"] = rejected
        return StageExecution(
            input_references=[item.source_id for item in sources],
            output_references=[item.source_id for item in admitted],
            details={
                "sources_submitted": len(sources),
                "sources_admitted": len(admitted),
                "sources_rejected": len(rejected),
            },
        )


class FindingExtractionStage(PipelineStage):
    name = "Finding Extraction"
    version = "302.1"

    def execute(self, context: PipelineContext) -> StageExecution:
        lifecycle = context.service("evidence_lifecycle")
        seeds = context.data.get("finding_seeds", [])
        source_by_id = {item.source_id: item for item in context.data["admitted_sources"]}
        findings = []
        receipts = []
        for seed in seeds:
            source = source_by_id[seed["source_id"]]
            finding, receipt = lifecycle.create_finding(
                source=source,
                assertion=seed["assertion"],
                classification=seed["classification"],
                confidence=seed["confidence"],
                model=seed.get("model", "deterministic-seed"),
                prompt_version=seed.get("prompt_version", "AIN-302-proof-v1"),
            )
            findings.append(finding)
            receipts.append(receipt)
        context.data["findings"] = findings
        context.data["finding_receipts"] = receipts
        return StageExecution(
            input_references=list(source_by_id),
            output_references=[item.finding_id for item in findings],
            details={"draft_findings_created": len(findings)},
        )


class HumanReviewStage(PipelineStage):
    name = "Human Evidence Review"
    version = "302.1"

    def execute(self, context: PipelineContext) -> StageExecution:
        lifecycle = context.service("evidence_lifecycle")
        reviewer = context.data["reviewer_authority"]
        decisions = context.data["review_decisions"]
        reviewed = []
        reviews = []
        for finding in context.data["findings"]:
            decision_spec = decisions[finding.finding_id]
            finding_after, review = lifecycle.review(
                finding=finding,
                reviewer=reviewer,
                decision=ReviewDecision(decision_spec["decision"]),
                reason=decision_spec["reason"],
            )
            reviewed.append(finding_after)
            reviews.append(review)
        context.data["reviewed_findings"] = reviewed
        context.data["reviews"] = reviews
        return StageExecution(
            input_references=[item.finding_id for item in context.data["findings"]],
            output_references=[item.review_id for item in reviews],
            details={
                "findings_approved": sum(item.decision == ReviewDecision.APPROVE for item in reviews),
                "findings_rejected": sum(item.decision == ReviewDecision.REJECT for item in reviews),
                "findings_deferred": sum(item.decision == ReviewDecision.DEFER for item in reviews),
            },
        )


class EvidenceCommitStage(PipelineStage):
    name = "Approved Evidence Commit"
    version = "302.1"

    def execute(self, context: PipelineContext) -> StageExecution:
        lifecycle = context.service("evidence_lifecycle")
        reviewer = context.data["reviewer_authority"]
        source_by_id = {item.source_id: item for item in context.data["admitted_sources"]}
        review_by_finding = {item.finding_id: item for item in context.data["reviews"]}
        commits = []
        rejected = 0
        for finding in context.data["reviewed_findings"]:
            review = review_by_finding[finding.finding_id]
            if review.decision != ReviewDecision.APPROVE:
                rejected += 1
                continue
            commits.append(
                lifecycle.commit_evidence(
                    source=source_by_id[finding.source_id],
                    finding=finding,
                    review=review,
                    reviewer=reviewer,
                )
            )
        context.data["evidence_commits"] = commits
        return StageExecution(
            input_references=[item.finding_id for item in context.data["reviewed_findings"]],
            output_references=[item.evidence_id for item in commits],
            evidence_references=[item.registry_identifier for item in commits],
            details={
                "evidence_records_committed": len(commits),
                "non_approved_findings_excluded": rejected,
            },
        )
