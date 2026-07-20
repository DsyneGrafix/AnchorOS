import hashlib
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from anchorintel_api.anchoros import AnchorIntelAnchorOSService
from anchorintel_api.app import AnchorIntelApplication
from anchorintel_api.repository import Repository
from anchorintel_api.reference import ensure_reference_opportunity, ensure_reference_records
from anchorintel_api.server import create_server
from anchorintel_api.service import AnchorIntelService


ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = ROOT.parent / "spatial-opportunity-engine"


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["ANCHORINTEL_ACCESS_LOG"] = "0"
        self.tempdir = tempfile.TemporaryDirectory()
        self.repository = Repository(Path(self.tempdir.name) / "test.db")
        self.service = AnchorIntelService(self.repository)
        application = AnchorIntelApplication(self.service)
        self.server = create_server(application, "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.repository.close()
        self.tempdir.cleanup()

    def request(self, method, path, payload=None, headers=None):
        body = json.dumps(payload).encode() if payload is not None else None
        request_headers = {"X-Actor": "api-test", **(headers or {})}
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        request = Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as exc:
            content = exc.read()
            parsed = json.loads(content) if content else None
            return exc.code, parsed, dict(exc.headers)
        content = response.read()
        content_type = response.headers.get("Content-Type", "")
        parsed = json.loads(content) if "application/json" in content_type else content.decode()
        return response.status, parsed, dict(response.headers)

    def request_form(self, path, fields):
        body = urlencode(fields).encode()
        request = Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=body,
            headers={
                "X-Actor": "ui-test",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        response = urlopen(request, timeout=5)
        return response.status, response.read().decode(), dict(response.headers)

    def request_multipart(
        self,
        path,
        fields,
        filename=None,
        content=b"",
        content_type="application/octet-stream",
    ):
        boundary = "----AnchorIntelEvidenceBoundary"
        chunks = []
        for name, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                    str(value).encode(),
                    b"\r\n",
                ]
            )
        if filename is not None:
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
                    f"Content-Type: {content_type}\r\n\r\n".encode(),
                    content,
                    b"\r\n",
                ]
            )
        chunks.append(f"--{boundary}--\r\n".encode())
        request = Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=b"".join(chunks),
            headers={
                "X-Actor": "upload-test",
                "Accept": "application/json",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as exc:
            return exc.code, json.loads(exc.read()), dict(exc.headers)
        return response.status, json.loads(response.read()), dict(response.headers)

    @staticmethod
    def managed_evidence_payload(**overrides):
        payload = {
            "title": "Utility asset context",
            "evidence_type": "Technical Record",
            "source": "Sirius Logic Systems",
            "source_date": "2026-07-19",
            "date_collected": "2026-07-19",
            "description": "Reference context for utility asset intelligence.",
            "evidence_status": "Collected",
            "evidence_confidence": "Moderate",
            "notes": "Test evidence.",
        }
        payload.update(overrides)
        return payload

    def profile(self):
        return json.loads((ENGINE_ROOT / "input" / "OPP-FL-0001.json").read_text())

    def create_profile(self):
        raw = self.profile()
        evidence = raw.pop("evidence")
        status, opportunity, _ = self.request("POST", "/v1/opportunities", raw)
        self.assertEqual(status, 201)
        for item in evidence:
            item["opportunity_id"] = opportunity["opportunity_id"]
            status, _, _ = self.request("POST", "/v1/evidence", item)
            self.assertEqual(status, 201)
        return opportunity

    def test_health_and_openapi_contract(self):
        status, health, _ = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["version"], "0.2.0")
        status, contract, _ = self.request("GET", "/v1/openapi.json")
        self.assertEqual(status, 200)
        self.assertIn("/opportunities/{opportunity_id}/evidence", contract["paths"])
        self.assertIn(
            "/opportunities/{opportunity_id}/evidence/{evidence_id}/archive",
            contract["paths"],
        )
        self.assertIn("/v1/assessments/run", contract["paths"])
        self.assertIn("/v1/lifecycle/revalidate", contract["paths"])

    def test_oi_000001_reference_opportunity_and_workspace_flow(self):
        reference, created = ensure_reference_opportunity(self.service)
        self.assertTrue(created)
        self.assertEqual(reference["opportunity_id"], "OI-000001")
        self.assertEqual(reference["organization"], "Florida Power & Light")

        same_reference, created_again = ensure_reference_opportunity(self.service)
        self.assertFalse(created_again)
        self.assertEqual(same_reference["revision"], reference["revision"])

        status, listing, headers = self.request("GET", "/opportunities")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("OI-000001", listing)
        self.assertIn("Florida Power &amp; Light Asset Intelligence Opportunity", listing)

        status, detail, _ = self.request("GET", "/opportunities/OI-000001")
        self.assertEqual(status, 200)
        self.assertIn("Attach Evidence", detail)
        self.assertIn("Generate Executive Opportunity Dossier", detail)

        status, edit, _ = self.request("GET", "/opportunities/OI-000001/edit")
        self.assertEqual(status, 200)
        self.assertIn("Save changes", edit)

        status, edited_page, _ = self.request_form(
            "/opportunities/OI-000001/edit",
            {
                "revision": reference["revision"],
                "title": reference["title"],
                "organization": reference["organization"],
                "sector": reference["sector"],
                "status": "Discovery",
                "geography": reference["geography"],
                "infrastructure_class": reference["infrastructure_class"],
                "description": reference["description"],
            },
        )
        self.assertEqual(status, 200)
        self.assertIn("Discovery", edited_page)
        updated = self.repository.get_opportunity("OI-000001")
        self.assertEqual(updated["status"], "Discovery")
        self.assertEqual(updated["revision"], 2)

        status, archived_page, _ = self.request_form(
            "/opportunities/OI-000001/archive", {}
        )
        self.assertEqual(status, 200)
        self.assertIn("Opportunity archived", archived_page)
        archived = self.repository.get_opportunity("OI-000001", include_archived=True)
        self.assertTrue(archived["archived"])

        status, records, _ = self.request(
            "GET", "/v1/opportunities?include_archived=true"
        )
        self.assertEqual(status, 200)
        self.assertEqual(records["items"][0]["opportunity_id"], "OI-000001")

    def test_reference_evidence_seed_is_bounded_and_idempotent(self):
        first = ensure_reference_records(self.service)
        self.assertTrue(first["opportunity_created"])
        self.assertTrue(first["evidence_created"])
        self.assertEqual(first["evidence"]["evidence_id"], "EV-000001")
        self.assertEqual(first["evidence"]["evidence_confidence"], "Moderate")
        self.assertIn("not an official Florida Power & Light document", first["evidence"]["notes"])

        second = ensure_reference_records(self.service)
        self.assertFalse(second["opportunity_created"])
        self.assertFalse(second["evidence_created"])
        self.assertEqual(second["evidence"]["revision"], 1)
        opportunity = self.service.get_opportunity("OI-000001")
        evidence_step = next(
            step for step in opportunity["workflow"] if step["key"] == "evidence"
        )
        self.assertEqual(evidence_step["state"], "complete")

    def test_managed_evidence_metadata_crud_archive_and_lifecycle(self):
        ensure_reference_opportunity(self.service)
        status, add_page, _ = self.request(
            "GET",
            "/opportunities/OI-000001/evidence/new",
            headers={"Accept": "text/html"},
        )
        self.assertEqual(status, 200)
        self.assertIn("Add Evidence", add_page)
        self.assertIn("Technical Record", add_page)

        status, created, _ = self.request(
            "POST",
            "/opportunities/OI-000001/evidence",
            self.managed_evidence_payload(),
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["evidence_id"], "EV-000001")
        self.assertEqual(created["revision"], 1)
        self.assertFalse(created["archived"])
        self.assertIsInstance(created["internal_id"], int)

        status, listing, _ = self.request(
            "GET",
            "/opportunities/OI-000001/evidence",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(listing["items"][0]["title"], "Utility asset context")

        status, retrieved, _ = self.request(
            "GET", "/opportunities/OI-000001/evidence/EV-000001"
        )
        self.assertEqual(status, 200)
        self.assertEqual(retrieved["source"], "Sirius Logic Systems")

        status, detail, _ = self.request(
            "GET",
            "/opportunities/OI-000001/evidence/EV-000001",
            headers={"Accept": "text/html"},
        )
        self.assertEqual(status, 200)
        self.assertIn("Metadata-only evidence", detail)
        self.assertIn("Utility asset context", detail)

        status, edit_page, _ = self.request(
            "GET",
            "/opportunities/OI-000001/evidence/EV-000001/edit",
            headers={"Accept": "text/html"},
        )
        self.assertEqual(status, 200)
        self.assertIn("Save metadata", edit_page)

        status, updated, _ = self.request(
            "PATCH",
            "/opportunities/OI-000001/evidence/EV-000001",
            {"evidence_status": "Under Review", "notes": "Metadata reviewed."},
            {"If-Match": "1"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(updated["evidence_status"], "Under Review")

        page_status, detail_page, _ = self.request(
            "GET", "/opportunities/OI-000001", headers={"Accept": "text/html"}
        )
        self.assertEqual(page_status, 200)
        self.assertIn("EV-000001", detail_page)
        self.assertIn('class="complete"', detail_page)

        status, archived, _ = self.request(
            "POST",
            "/opportunities/OI-000001/evidence/EV-000001/archive",
            {"revision": 2},
        )
        self.assertEqual(status, 200)
        self.assertTrue(archived["archived"])
        self.assertEqual(archived["revision"], 3)

        opportunity = self.service.get_opportunity("OI-000001")
        evidence_step = next(
            step for step in opportunity["workflow"] if step["key"] == "evidence"
        )
        self.assertEqual(evidence_step["state"], "pending")
        actions = [item["action"] for item in self.repository.list_audit(20)]
        self.assertIn("evidence.created", actions)
        self.assertIn("evidence.metadata_updated", actions)
        self.assertIn("evidence.archived", actions)

    def test_managed_evidence_file_upload_hash_and_download(self):
        ensure_reference_opportunity(self.service)
        content = b"bounded reference evidence\n"
        status, created, _ = self.request_multipart(
            "/opportunities/OI-000001/evidence",
            self.managed_evidence_payload(title="File-backed evidence"),
            filename="utility-context.txt",
            content=content,
            content_type="text/plain",
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(created["file_name"], "utility-context.txt")
        self.assertNotIn("utility-context", created["storage_name"])
        self.assertTrue(
            (self.service.evidence_storage_dir / created["storage_name"]).is_file()
        )

        status, downloaded, headers = self.request(
            "GET", "/opportunities/OI-000001/evidence/EV-000001/file"
        )
        self.assertEqual(status, 200)
        self.assertEqual(downloaded, content.decode())
        self.assertIn("text/plain", headers["Content-Type"])
        actions = [item["action"] for item in self.repository.list_audit(20)]
        self.assertIn("evidence.file_uploaded", actions)

    def test_managed_evidence_validation_and_path_safety(self):
        status, error, _ = self.request(
            "POST",
            "/opportunities/MISSING/evidence",
            self.managed_evidence_payload(),
        )
        self.assertEqual(status, 404)
        self.assertEqual(error["error"]["code"], "opportunity_not_found")

        ensure_reference_opportunity(self.service)
        for field, value, code in (
            ("evidence_type", "Rumor", "invalid_evidence_type"),
            ("evidence_status", "Published", "invalid_evidence_status"),
        ):
            status, error, _ = self.request(
                "POST",
                "/opportunities/OI-000001/evidence",
                self.managed_evidence_payload(**{field: value}),
            )
            self.assertEqual(status, 400)
            self.assertEqual(error["error"]["code"], code)

        status, error, _ = self.request_multipart(
            "/opportunities/OI-000001/evidence",
            self.managed_evidence_payload(),
            filename="../outside.txt",
            content=b"unsafe",
            content_type="text/plain",
        )
        self.assertEqual(status, 400)
        self.assertEqual(error["error"]["code"], "unsafe_filename")

        self.service.max_file_size = 4
        status, error, _ = self.request_multipart(
            "/opportunities/OI-000001/evidence",
            self.managed_evidence_payload(),
            filename="bounded.txt",
            content=b"12345",
            content_type="text/plain",
        )
        self.assertEqual(status, 413)
        self.assertEqual(error["error"]["code"], "file_too_large")

    def test_existing_database_schema_is_migrated_without_data_loss(self):
        migration_db = Path(self.tempdir.name) / "migration.db"
        connection = sqlite3.connect(migration_db)
        connection.executescript(
            """
            CREATE TABLE opportunities (
                opportunity_id TEXT PRIMARY KEY, record_json TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL DEFAULT 'Unassessed',
                archived INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE evidence (
                evidence_id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL,
                record_json TEXT NOT NULL, classification TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO opportunities VALUES (
                'OI-LEGACY', '{"opportunity_id":"OI-LEGACY","title":"Legacy","geography":"Florida","infrastructure_class":"Utility"}',
                'Unassessed', 0, 1, '2026-07-19T00:00:00Z', '2026-07-19T00:00:00Z'
            );
            INSERT INTO evidence VALUES (
                'E-LEGACY', 'OI-LEGACY', '{"evidence_id":"E-LEGACY","claim":"Legacy claim","state":"A"}',
                'A', 1, '2026-07-19T00:00:00Z', '2026-07-19T00:00:00Z'
            );
            """
        )
        connection.close()
        migrated = Repository(migration_db)
        try:
            evidence = migrated.get_evidence("E-LEGACY")
            self.assertEqual(evidence["description"], "Legacy claim")
            self.assertFalse(evidence["archived"])
            self.assertIsNone(evidence["archived_at"])
        finally:
            migrated.close()

    def test_managed_evidence_persists_after_repository_restart(self):
        persistence_db = Path(self.tempdir.name) / "persistence.db"
        first_repository = Repository(persistence_db)
        first_service = AnchorIntelService(first_repository)
        ensure_reference_opportunity(first_service)
        created = first_service.create_managed_evidence(
            "OI-000001",
            self.managed_evidence_payload(title="Restart persistence evidence"),
            "restart-test",
        )
        first_repository.close()

        second_repository = Repository(persistence_db)
        try:
            persisted = second_repository.get_evidence(created["evidence_id"])
            self.assertEqual(persisted["title"], "Restart persistence evidence")
            self.assertEqual(persisted["revision"], 1)
        finally:
            second_repository.close()

    def test_anchoros_lifecycle_adapter(self):
        adapter = AnchorIntelAnchorOSService(
            database_path=Path(self.tempdir.name) / "anchoros.db", port=0
        )
        self.assertEqual(adapter.register()["state"], "Registered")
        try:
            health = adapter.start()
            self.assertEqual(health["state"], "Running")
            with urlopen(f"http://127.0.0.1:{health['port']}/health", timeout=5) as response:
                self.assertEqual(response.status, 200)
        finally:
            self.assertEqual(adapter.stop()["state"], "Stopped")

    def test_complete_assessment_and_reporting_lifecycle(self):
        opportunity = self.create_profile()
        status, assessment, _ = self.request(
            "POST",
            "/v1/assessments/run",
            {"opportunity_id": opportunity["opportunity_id"], "assessment_date": "2026-07-18"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(assessment["result"]["recommendation"], "Hold")
        self.assertEqual(assessment["result"]["score"], 37.5)
        assessment_id = assessment["assessment_id"]

        status, report_json, _ = self.request(
            "POST", "/v1/reports/json", {"assessment_id": assessment_id}
        )
        self.assertEqual(status, 200)
        self.assertEqual(report_json["confidence"], "Low")
        status, report_markdown, headers = self.request(
            "POST", "/v1/reports/markdown", {"assessment_id": assessment_id}
        )
        self.assertEqual(status, 200)
        self.assertIn("text/markdown", headers["Content-Type"])
        self.assertIn("**Hold**", report_markdown)

        status, holds, _ = self.request("GET", "/v1/lifecycle/holds")
        self.assertEqual(status, 200)
        self.assertEqual(len(holds["items"]), 1)
        status, due, _ = self.request("GET", "/v1/lifecycle/reviews/due?as_of=2026-08-01")
        self.assertEqual(status, 200)
        self.assertEqual(due["items"][0]["opportunity_id"], opportunity["opportunity_id"])

    def test_controlled_evidence_promotion(self):
        raw = self.profile()
        raw.pop("evidence")
        _, opportunity, _ = self.request("POST", "/v1/opportunities", raw)
        evidence = {
            "evidence_id": "E-PROMOTE",
            "opportunity_id": opportunity["opportunity_id"],
            "claim": "A current filing supports the opportunity.",
            "state": "A",
            "material": True,
            "source": "Working note",
        }
        status, created, _ = self.request("POST", "/v1/evidence", evidence)
        self.assertEqual(status, 201)

        status, error, _ = self.request("PATCH", "/v1/evidence/E-PROMOTE", {"state": "S"})
        self.assertEqual(status, 409)
        self.assertEqual(error["error"]["code"], "verification_required")

        status, supported, _ = self.request(
            "POST",
            "/v1/evidence/E-PROMOTE/verify",
            {"verification_note": "Matched to the identified filing.", "source": "FPSC filing"},
            {"If-Match": str(created["revision"])},
        )
        self.assertEqual(status, 200)
        self.assertEqual(supported["state"], "S")
        status, verified, _ = self.request(
            "POST",
            "/v1/evidence/E-PROMOTE/verify",
            {"verification_note": "Authority, date, and claim were independently checked.", "source": "FPSC filing"},
            {"If-Match": str(supported["revision"])},
        )
        self.assertEqual(status, 200)
        self.assertEqual(verified["state"], "V")

    def test_revision_conflict_is_visible(self):
        raw = self.profile()
        raw.pop("evidence")
        _, opportunity, _ = self.request("POST", "/v1/opportunities", raw)
        raw["title"] = "Updated title"
        status, _, _ = self.request(
            "PUT",
            f"/v1/opportunities/{opportunity['opportunity_id']}",
            raw,
            {"If-Match": "999"},
        )
        self.assertEqual(status, 409)

    def test_incomplete_assessment_returns_422(self):
        payload = {
            "opportunity_id": "OPP-DRAFT",
            "title": "Draft opportunity",
            "geography": "Florida",
            "infrastructure_class": "Electric utility"
        }
        status, _, _ = self.request("POST", "/v1/opportunities", payload)
        self.assertEqual(status, 201)
        status, error, _ = self.request(
            "POST", "/v1/assessments/run", {"opportunity_id": "OPP-DRAFT"}
        )
        self.assertEqual(status, 422)
        self.assertEqual(error["error"]["code"], "assessment_input_incomplete")

    def test_revalidation_supersedes_prior_assessment(self):
        opportunity = self.create_profile()
        _, first, _ = self.request(
            "POST",
            "/v1/assessments/run",
            {"opportunity_id": opportunity["opportunity_id"], "assessment_date": "2026-07-18"},
        )
        status, second, _ = self.request(
            "POST",
            "/v1/lifecycle/revalidate",
            {
                "opportunity_id": opportunity["opportunity_id"],
                "assessment_date": "2026-08-01",
                "reason": "Scheduled evidence review",
                "lifecycle": {"review_date": "2026-09-01"}
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(second["supersedes_assessment_id"], first["assessment_id"])

    def test_archive_and_audit(self):
        opportunity = self.create_profile()
        status, archived, _ = self.request(
            "DELETE", f"/v1/opportunities/{opportunity['opportunity_id']}"
        )
        self.assertEqual(status, 200)
        self.assertTrue(archived["archived"])
        status, error, _ = self.request(
            "GET", f"/v1/opportunities/{opportunity['opportunity_id']}"
        )
        self.assertEqual(status, 404)
        status, audit, _ = self.request("GET", "/v1/admin/audit?limit=50")
        self.assertEqual(status, 200)
        self.assertTrue(any(item["action"] == "opportunity.archived" for item in audit["items"]))


if __name__ == "__main__":
    unittest.main()
