from __future__ import annotations

from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tempfile
import threading
import unittest
from pathlib import Path

from anchorinsight_pipeline.evidence_models import SourceAdmissionStatus
from anchorinsight_pipeline.evidence_service import EvidenceLifecycleService
from anchorinsight_pipeline.evidence_store import EvidenceLifecycleStore
from anchorinsight_research.acquisition import AcquisitionService
from anchorinsight_research.bridge import LiveEvidenceBridgeService
from anchorinsight_research.discovery import SourceCatalogEntry
from anchorinsight_research.handoff import (
    EvidenceHandoffService,
    HandoffIntegrityError,
    UnsupportedEvidenceContent,
)
from anchorinsight_research.live import (
    LiveHTTPAcquisitionProvider,
    UnsupportedLiveSource,
)
from anchorinsight_research.models import (
    AcquisitionStatus,
    AcquiredDocument,
    CandidateSource,
    ResearchRequest,
)
from anchorinsight_research.service import ResearchPlanningAcquisitionService
from anchorinsight_research.storage import ResearchArtifactStore


class _Handler(BaseHTTPRequestHandler):
    body = b"<html><body><h1>CPS Energy</h1><p>Material public development.</p></body></html>"

    def do_GET(self):  # noqa: N802
        if self.path == "/source":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(self.body)))
            self.end_headers()
            self.wfile.write(self.body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):  # noqa: A003
        return


class AIN3032LiveAcquisitionHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.research_store = ResearchArtifactStore(root / "research")
        self.evidence_store = EvidenceLifecycleStore(root / "evidence")
        self.evidence_service = EvidenceLifecycleService(
            store=self.evidence_store,
            registry=object(),
        )
        self.handoff = EvidenceHandoffService(
            evidence_service=self.evidence_service,
            artifact_store=self.research_store,
        )
        self.acquisition = AcquisitionService(store=self.research_store)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.url = f"http://{host}:{port}/source"

        self.source = CandidateSource(
            plan_id="PLAN-AIN3032",
            title="CPS Energy Public Development",
            url=self.url,
            organization="CPS Energy",
            source_type="News",
            authority_score=0.90,
            discovery_reason="Material external development relevant to active research.",
        )

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def _acquire(self):
        provider = LiveHTTPAcquisitionProvider(timeout_seconds=2.0)
        return self.acquisition.acquire_with_provider(
            source=self.source,
            provider=provider,
            acquisition_method="AIN-303.2 Live HTTP",
            parent_research_request_id="REQ-AIN3032",
        )

    def test_live_http_provider_retrieves_real_http_content(self) -> None:
        provider = LiveHTTPAcquisitionProvider(timeout_seconds=2.0)
        content, media_type = provider(self.source)
        self.assertIn(b"CPS Energy", content)
        self.assertEqual(media_type, "text/html")

    def test_live_provider_rejects_non_http_source(self) -> None:
        source = replace(self.source, url="file:///tmp/source.html")
        with self.assertRaises(UnsupportedLiveSource):
            LiveHTTPAcquisitionProvider()(source)

    def test_live_acquisition_generates_retrieved_receipt(self) -> None:
        document, receipt = self._acquire()
        self.assertIsNotNone(document)
        self.assertEqual(receipt.status, AcquisitionStatus.RETRIEVED)
        self.assertEqual(receipt.document_id, document.document_id)
        self.assertEqual(receipt.source_hash, document.content_hash)

    def test_verified_acquisition_is_admitted_to_ain302(self) -> None:
        document, receipt = self._acquire()
        result = self.handoff.handoff(
            source=self.source,
            document=document,
            acquisition_receipt=receipt,
            workspace_id="WS-EXEC-001",
            organization_id="COF-ORG-2026-001",
            publisher="Local Test Publisher",
        )
        self.assertEqual(result.source.admission_status, SourceAdmissionStatus.ADMITTED)
        self.assertEqual(result.source.organization_id, "COF-ORG-2026-001")
        self.assertIn("CPS Energy", result.source.raw_content)
        self.assertEqual(result.receipt.status, "ADMITTED")
        self.assertEqual(result.receipt.acquired_content_hash, document.content_hash)
        self.assertTrue(result.receipt.integrity_hash)

    def test_handoff_receipt_is_persisted(self) -> None:
        document, receipt = self._acquire()
        result = self.handoff.handoff(
            source=self.source,
            document=document,
            acquisition_receipt=receipt,
            workspace_id="WS-EXEC-001",
            organization_id="COF-ORG-2026-001",
        )
        payload = self.research_store.load_evidence_handoff_receipt(
            result.receipt.handoff_id
        )
        self.assertEqual(payload["ain302_source_id"], result.source.source_id)
        self.assertEqual(payload["integrity_hash"], result.receipt.integrity_hash)

    def test_hash_mismatch_blocks_handoff(self) -> None:
        document, receipt = self._acquire()
        tampered = replace(receipt, source_hash="0" * 64)
        with self.assertRaises(HandoffIntegrityError):
            self.handoff.handoff(
                source=self.source,
                document=document,
                acquisition_receipt=tampered,
                workspace_id="WS-EXEC-001",
                organization_id="COF-ORG-2026-001",
            )

    def test_failed_acquisition_cannot_enter_ain302(self) -> None:
        document, receipt = self._acquire()
        failed = replace(receipt, status=AcquisitionStatus.FAILED)
        with self.assertRaises(HandoffIntegrityError):
            self.handoff.handoff(
                source=self.source,
                document=document,
                acquisition_receipt=failed,
                workspace_id="WS-EXEC-001",
                organization_id="COF-ORG-2026-001",
            )

    def test_binary_document_cannot_enter_text_source_admission(self) -> None:
        document, receipt = self._acquire()
        binary_document = AcquiredDocument(
            plan_id=document.plan_id,
            source_id=document.source_id,
            raw_content=b"%PDF-test",
            media_type="application/pdf",
            acquisition_method=document.acquisition_method,
            original_url=document.original_url,
            document_id=document.document_id,
            acquired_at=document.acquired_at,
        )
        binary_receipt = replace(
            receipt,
            source_hash=binary_document.content_hash,
            content_length=binary_document.content_length,
        )
        with self.assertRaises(UnsupportedEvidenceContent):
            self.handoff.handoff(
                source=self.source,
                document=binary_document,
                acquisition_receipt=binary_receipt,
                workspace_id="WS-EXEC-001",
                organization_id="COF-ORG-2026-001",
            )

    def test_handoff_does_not_create_findings_or_commit_evidence(self) -> None:
        document, receipt = self._acquire()
        self.handoff.handoff(
            source=self.source,
            document=document,
            acquisition_receipt=receipt,
            workspace_id="WS-EXEC-001",
            organization_id="COF-ORG-2026-001",
        )
        self.assertEqual(list((self.evidence_store.root / "findings").glob("*.json")), [])
        self.assertEqual(list((self.evidence_store.root / "commits").glob("*.json")), [])

    def test_bridge_executes_plan_live_acquisition_and_ain302_handoff(self) -> None:
        catalog = (
            SourceCatalogEntry(
                title="CPS Energy Local Proof Source",
                url=self.url,
                organization="CPS Energy",
                source_type="Corporate",
                authority_score=1.0,
                categories=("Energy", "Infrastructure"),
                discovery_reason="AIN-303.2 local live-acquisition proof source",
            ),
        )
        research = ResearchPlanningAcquisitionService(
            store=self.research_store,
            catalog=catalog,
        )
        bridge = LiveEvidenceBridgeService(
            research_service=research,
            handoff_service=self.handoff,
        )
        request = ResearchRequest(
            workspace_id="WS-EXEC-001",
            organization_identifier="CPS Energy",
            objective="Research CPS Energy infrastructure and energy developments.",
            requested_outputs=("Evidence",),
            request_id="REQ-AIN3032-BRIDGE",
        )

        result = bridge.execute(
            request=request,
            workspace_id="WS-EXEC-001",
            organization_id="COF-ORG-2026-001",
            provider=LiveHTTPAcquisitionProvider(timeout_seconds=2.0),
            acquisition_method="AIN-303.2 Live HTTP",
            pipeline_id="AIN-303.2-PROOF",
        )

        self.assertTrue(result.complete)
        self.assertEqual(result.acquisition.documents_acquired, 1)
        self.assertEqual(result.sources_admitted_to_ain302, 1)
        self.assertEqual(
            result.handoffs[0].source.admission_status,
            SourceAdmissionStatus.ADMITTED,
        )
        self.assertEqual(result.handoffs[0].receipt.research_request_id, request.request_id)


if __name__ == "__main__":
    unittest.main()
