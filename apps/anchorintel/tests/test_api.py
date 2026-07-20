import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from anchorintel_api.anchoros import AnchorIntelAnchorOSService
from anchorintel_api.app import AnchorIntelApplication
from anchorintel_api.repository import Repository
from anchorintel_api.server import create_server
from anchorintel_api.service import AnchorIntelService


ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = ROOT.parent / "spatial-opportunity-engine"


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["ANCHORINTEL_ACCESS_LOG"] = "0"
        self.tempdir = tempfile.TemporaryDirectory()
        self.repository = Repository(Path(self.tempdir.name) / "test.db")
        application = AnchorIntelApplication(AnchorIntelService(self.repository))
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
        status, contract, _ = self.request("GET", "/v1/openapi.json")
        self.assertEqual(status, 200)
        self.assertIn("/v1/assessments/run", contract["paths"])
        self.assertIn("/v1/lifecycle/revalidate", contract["paths"])

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
