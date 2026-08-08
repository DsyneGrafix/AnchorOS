from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from anchorinsight_pipeline.evidence_models import (
    AdmittedSource,
    ReviewDecision,
    ReviewerAuthority,
)
from anchorinsight_pipeline.evidence_service import EvidenceLifecycleService
from anchorinsight_pipeline.evidence_store import EvidenceLifecycleStore
from anchorinsight_pipeline.registry_adapter import CommercialRegistryEvidenceAdapter
from anchorinsight_registry import (
    CommercialIntelligenceRegistryService,
    RegistryDatabase,
)


def now_iso(offset_days: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=offset_days)).isoformat()


class AIN302CommercialRegistryAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)

        self.registry = CommercialIntelligenceRegistryService(
            RegistryDatabase(root / "commercial_registry.db")
        )
        self.organization = self.registry.create_organization(
            legal_name="CPS Energy",
            common_name="CPS Energy",
            role="Target Organization",
            industry="Utilities",
            sector="Energy",
            website="https://www.cpsenergy.com/",
            actor="AIN-302 Registry Adapter Test",
        )

        self.adapter = CommercialRegistryEvidenceAdapter(self.registry)
        self.evidence_store = EvidenceLifecycleStore(root / "evidence_lifecycle")
        self.service = EvidenceLifecycleService(
            store=self.evidence_store,
            registry=self.adapter,
        )

        self.source = AdmittedSource(
            workspace_id="WS-EXEC-001",
            organization_id=self.organization["cof_organization_id"],
            title="CPS Energy Official Website",
            publisher="CPS Energy",
            url="https://www.cpsenergy.com/",
            raw_content=(
                "CPS Energy provides electric and natural gas services and "
                "publishes public information about its operations."
            ),
            source_type="Corporate",
            acquisition_method="AIN-303.2 Live HTTP Proof",
            authority_classification="Acquired Source — Pending Finding Review",
        )

        self.reviewer = ReviewerAuthority(
            reviewer_id="Authorized Human Reviewer",
            workspace_id="WS-EXEC-001",
            role="Evidence Reviewer",
            review_scope=("*",),
            authority_source="Workspace Evidence Authority",
            effective_at=now_iso(-1),
            expires_at=now_iso(30),
            permitted_actions=("Approve",),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _approved_finding(self, *, assertion: str):
        admitted = self.service.admit_source(self.source)
        finding, _ = self.service.create_finding(
            source=admitted,
            assertion=assertion,
            classification="Infrastructure Modernization",
            confidence=0.94,
            model="deterministic-proof",
            prompt_version="AIN-302-registry-adapter-proof-v1",
            extraction_engine="deterministic-proof",
        )
        approved, review = self.service.review(
            finding=finding,
            reviewer=self.reviewer,
            decision=ReviewDecision.APPROVE,
            reason="Human reviewer confirmed the source supports the assertion.",
        )
        return admitted, approved, review

    def _rows(self, sql: str, params: tuple = ()):
        connection = self.registry.db.connect()
        try:
            return [dict(row) for row in connection.execute(sql, params).fetchall()]
        finally:
            connection.close()

    def test_approved_ain302_finding_commits_to_actual_registry(self) -> None:
        source, finding, review = self._approved_finding(
            assertion="CPS Energy maintains public operational information."
        )

        commit = self.service.commit_evidence(
            source=source,
            finding=finding,
            review=review,
            reviewer=self.reviewer,
        )

        self.assertTrue(commit.registry_identifier.startswith("COF-EVD-"))

        evidence_rows = self._rows(
            "SELECT * FROM evidence WHERE cof_evidence_id = ?",
            (commit.registry_identifier,),
        )
        self.assertEqual(len(evidence_rows), 1)
        self.assertEqual(evidence_rows[0]["classification"], "Verified")
        self.assertEqual(
            evidence_rows[0]["evidence_type"],
            "Infrastructure Modernization",
        )
        self.assertEqual(evidence_rows[0]["confidence"], 0.94)

    def test_registry_source_preserves_ain302_source_hash(self) -> None:
        source, finding, review = self._approved_finding(
            assertion="CPS Energy publishes public operational information."
        )

        self.service.commit_evidence(
            source=source,
            finding=finding,
            review=review,
            reviewer=self.reviewer,
        )

        source_rows = self._rows(
            "SELECT * FROM sources WHERE url = ?",
            (source.url,),
        )
        self.assertEqual(len(source_rows), 1)
        self.assertEqual(source_rows[0]["checksum_sha256"], source.content_hash)

    def test_registry_evidence_is_linked_to_target_organization(self) -> None:
        source, finding, review = self._approved_finding(
            assertion="CPS Energy is the organization represented by this source."
        )
        commit = self.service.commit_evidence(
            source=source,
            finding=finding,
            review=review,
            reviewer=self.reviewer,
        )

        links = self._rows(
            """
            SELECT el.*, e.cof_evidence_id
            FROM evidence_links el
            JOIN evidence e ON e.evidence_id = el.evidence_id
            WHERE e.cof_evidence_id = ?
            """,
            (commit.registry_identifier,),
        )
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["subject_type"], "Organization")
        self.assertEqual(links[0]["subject_id"], self.organization["organization_id"])

    def test_retry_does_not_duplicate_registry_evidence(self) -> None:
        source, finding, review = self._approved_finding(
            assertion="CPS Energy public information passed governed review."
        )
        first = self.service.commit_evidence(
            source=source,
            finding=finding,
            review=review,
            reviewer=self.reviewer,
        )
        second = self.service.commit_evidence(
            source=source,
            finding=finding,
            review=review,
            reviewer=self.reviewer,
        )

        self.assertEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(
            len(
                self._rows(
                    "SELECT * FROM evidence WHERE cof_evidence_id = ?",
                    (first.registry_identifier,),
                )
            ),
            1,
        )

    def test_multiple_findings_reuse_same_registry_source(self) -> None:
        first_source, first_finding, first_review = self._approved_finding(
            assertion="CPS Energy publishes operational information."
        )
        self.service.commit_evidence(
            source=first_source,
            finding=first_finding,
            review=first_review,
            reviewer=self.reviewer,
        )

        second_finding, _ = self.service.create_finding(
            source=first_source,
            assertion="CPS Energy is an energy utility organization.",
            classification="Organization Profile",
            confidence=0.92,
            model="deterministic-proof",
            prompt_version="AIN-302-registry-adapter-proof-v1",
            extraction_engine="deterministic-proof",
        )
        second_approved, second_review = self.service.review(
            finding=second_finding,
            reviewer=self.reviewer,
            decision=ReviewDecision.APPROVE,
            reason="Human reviewer confirmed the second assertion.",
        )
        self.service.commit_evidence(
            source=first_source,
            finding=second_approved,
            review=second_review,
            reviewer=self.reviewer,
        )

        self.assertEqual(
            len(self._rows("SELECT * FROM sources WHERE url = ?", (first_source.url,))),
            1,
        )
        self.assertEqual(len(self._rows("SELECT * FROM evidence")), 2)


if __name__ == "__main__":
    unittest.main()
