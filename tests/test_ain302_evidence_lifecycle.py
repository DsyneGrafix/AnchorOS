from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from anchorinsight_pipeline import (
    AdmittedSource,
    EvidenceLifecycleService,
    EvidenceLifecycleStore,
    FindingStatus,
    ReviewDecision,
    ReviewerAuthority,
    SourceAdmissionStatus,
)


def now_iso(offset_days: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=offset_days)).isoformat()


class FakeRegistry:
    def __init__(self):
        self.evidence = {}
        self.fail = False
        self.transactions = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        before = dict(self.evidence)
        try:
            yield
        except Exception:
            self.evidence = before
            raise

    def create_evidence(self, **payload):
        if self.fail:
            raise RuntimeError("simulated registry failure")
        evidence_id = payload["evidence_id"]
        if evidence_id in self.evidence:
            raise ValueError("duplicate evidence")
        self.evidence[evidence_id] = payload
        return f"COF-EVD-{len(self.evidence):06d}"


class AIN302EvidenceLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = EvidenceLifecycleStore(Path(self.tmp.name))
        self.registry = FakeRegistry()
        self.service = EvidenceLifecycleService(store=self.store, registry=self.registry)
        self.source = AdmittedSource(
            workspace_id="SLS-DEMO-001",
            organization_id="COF-ORG-2026-001",
            title="CPS Energy Modernization Announcement",
            publisher="CPS Energy",
            url="https://example.test/cps-modernization",
            raw_content="CPS Energy announced a grid modernization and communications investment program.",
        )
        self.reviewer = ReviewerAuthority(
            reviewer_id="Ricky Jarnagin",
            workspace_id="SLS-DEMO-001",
            role="Owner",
            review_scope=("*",),
            authority_source="Workspace Owner",
            effective_at=now_iso(-1),
            expires_at=now_iso(30),
            permitted_actions=(
                "Approve",
                "Reject",
                "Defer",
                "Dispute",
                "Reclassify",
                "Request More Research",
            ),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def finding(self, source=None, assertion="CPS Energy announced grid modernization."):
        source = source or self.service.admit_source(self.source)
        return self.service.create_finding(
            source=source,
            assertion=assertion,
            classification="Infrastructure Modernization",
            confidence=0.91,
        )[0]

    def test_source_admission_succeeds(self):
        admitted = self.service.admit_source(self.source)
        self.assertEqual(admitted.admission_status, SourceAdmissionStatus.ADMITTED)

    def test_rejected_source_cannot_create_findings(self):
        rejected = self.service.reject_source(self.source)
        with self.assertRaises(Exception):
            self.service.create_finding(
                source=rejected,
                assertion="Unsupported assertion",
                classification="Other",
                confidence=0.5,
            )

    def test_draft_finding_is_non_authoritative(self):
        finding = self.finding()
        self.assertEqual(finding.status, FindingStatus.PENDING_REVIEW)
        self.assertEqual(len(self.registry.evidence), 0)

    def test_finding_receipt_is_generated(self):
        source = self.service.admit_source(self.source)
        finding, receipt = self.service.create_finding(
            source=source,
            assertion="CPS Energy announced grid modernization.",
            classification="Infrastructure Modernization",
            confidence=0.91,
        )
        self.assertEqual(receipt.finding_id, finding.finding_id)
        self.assertEqual(len(receipt.assertion_hash), 64)

    def test_reviewer_authority_is_enforced(self):
        finding = self.finding()
        unauthorized = ReviewerAuthority(
            reviewer_id="Other",
            workspace_id="WRONG",
            role="Analyst",
            review_scope=("*",),
            authority_source="Test",
            effective_at=now_iso(-1),
            permitted_actions=("Approve",),
        )
        with self.assertRaises(PermissionError):
            self.service.review(
                finding=finding,
                reviewer=unauthorized,
                decision=ReviewDecision.APPROVE,
                reason="Attempt",
            )

    def test_unauthorized_action_fails(self):
        finding = self.finding()
        limited = ReviewerAuthority(
            reviewer_id="Ricky",
            workspace_id="SLS-DEMO-001",
            role="Analyst",
            review_scope=("*",),
            authority_source="Test",
            effective_at=now_iso(-1),
            permitted_actions=("Reject",),
        )
        with self.assertRaises(PermissionError):
            self.service.review(
                finding=finding,
                reviewer=limited,
                decision=ReviewDecision.APPROVE,
                reason="Not allowed",
            )

    def test_approved_finding_commits(self):
        source = self.service.admit_source(self.source)
        finding = self.finding(source)
        approved, review = self.service.review(
            finding=finding,
            reviewer=self.reviewer,
            decision=ReviewDecision.APPROVE,
            reason="Source supports assertion.",
        )
        commit = self.service.commit_evidence(
            source=source,
            finding=approved,
            review=review,
            reviewer=self.reviewer,
        )
        self.assertEqual(len(self.registry.evidence), 1)
        self.assertTrue(commit.registry_identifier.startswith("COF-EVD-"))

    def test_rejected_finding_cannot_commit(self):
        source = self.service.admit_source(self.source)
        finding = self.finding(source)
        rejected, review = self.service.review(
            finding=finding,
            reviewer=self.reviewer,
            decision=ReviewDecision.REJECT,
            reason="Assertion overstated.",
        )
        with self.assertRaises(Exception):
            self.service.commit_evidence(
                source=source,
                finding=rejected,
                review=review,
                reviewer=self.reviewer,
            )

    def test_atomic_commit_rolls_back_registry_failure(self):
        source = self.service.admit_source(self.source)
        finding = self.finding(source)
        approved, review = self.service.review(
            finding=finding,
            reviewer=self.reviewer,
            decision=ReviewDecision.APPROVE,
            reason="Approved",
        )
        self.registry.fail = True
        with self.assertRaises(RuntimeError):
            self.service.commit_evidence(
                source=source,
                finding=approved,
                review=review,
                reviewer=self.reviewer,
            )
        self.assertEqual(self.registry.evidence, {})
        self.assertIsNone(
            self.store.find_commit_for_finding(finding.finding_id, finding.finding_version)
        )

    def test_retry_does_not_duplicate_evidence(self):
        source = self.service.admit_source(self.source)
        finding = self.finding(source)
        approved, review = self.service.review(
            finding=finding,
            reviewer=self.reviewer,
            decision=ReviewDecision.APPROVE,
            reason="Approved",
        )
        first = self.service.commit_evidence(
            source=source, finding=approved, review=review, reviewer=self.reviewer
        )
        second = self.service.commit_evidence(
            source=source, finding=approved, review=review, reviewer=self.reviewer
        )
        self.assertEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(len(self.registry.evidence), 1)

    def test_duplicate_findings_are_correlated(self):
        source = self.service.admit_source(self.source)
        a = self.finding(source, "CPS Energy announced grid modernization.")
        b = self.finding(source, "  cps energy announced GRID modernization. ")
        groups = self.service.correlate([a, b])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(next(iter(groups.values()))), 2)

    def test_review_creates_audit_record(self):
        finding = self.finding()
        _, review = self.service.review(
            finding=finding,
            reviewer=self.reviewer,
            decision=ReviewDecision.APPROVE,
            reason="Supported",
        )
        self.assertTrue(review.audit_reference.startswith("AUD-"))
        self.assertTrue(
            (Path(self.tmp.name) / "reviews" / f"{review.review_id}.json").exists()
        )

    def test_evidence_chain_is_reconstructable(self):
        source = self.service.admit_source(self.source)
        finding = self.finding(source)
        approved, review = self.service.review(
            finding=finding,
            reviewer=self.reviewer,
            decision=ReviewDecision.APPROVE,
            reason="Supported",
        )
        commit = self.service.commit_evidence(
            source=source, finding=approved, review=review, reviewer=self.reviewer
        )
        chain = self.store.reconstruct_chain(commit.evidence_id)
        self.assertEqual(chain["source"]["source_id"], source.source_id)
        self.assertEqual(chain["finding"]["finding_id"], finding.finding_id)
        self.assertEqual(chain["review"]["review_id"], review.review_id)

    def test_finding_version_is_preserved(self):
        finding = self.finding()
        self.assertEqual(finding.finding_version, 1)
        self.assertIn(".v1.json", str(self.store.save_finding(finding)))


if __name__ == "__main__":
    unittest.main()
