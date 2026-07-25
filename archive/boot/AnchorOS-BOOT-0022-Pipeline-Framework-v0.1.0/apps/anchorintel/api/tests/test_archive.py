import hashlib
import json
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from anchorintel_api.app import AnchorIntelApplication
from anchorintel_api.archive import (
    REQUIRED_ARCHIVE_FILES,
    build_archive_package,
    canonical_json,
)
from anchorintel_api.errors import ApiError
from anchorintel_api.reference import (
    ensure_reference_evidence,
    ensure_reference_opportunity,
)
from anchorintel_api.repository import Repository
from anchorintel_api.service import AnchorIntelService


class ArchiveSprint6Tests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.repositories: list[Repository] = []

    def tearDown(self):
        for repository in self.repositories:
            repository.close()
        self.tempdir.cleanup()

    def make_service(self, name: str = "primary") -> AnchorIntelService:
        repository = Repository(self.root / f"{name}.db")
        self.repositories.append(repository)
        return AnchorIntelService(
            repository,
            evidence_storage_dir=self.root / name / "evidence-files",
            archive_storage_dir=self.root / name / "archives",
        )

    def build_boot_chain(self, name: str = "primary") -> AnchorIntelService:
        service = self.make_service(name)
        ensure_reference_opportunity(service)
        ensure_reference_evidence(service)
        first_review = service.run_knowledge_review(
            "OI-000001", "AKM-GEO-FL-001", "sprint6-test"
        )
        self.assertEqual(first_review["review_id"], "KR-000001")
        review = service.supersede_knowledge_review(
            "OI-000001", "KR-000001", "sprint6-test"
        )
        self.assertEqual(review["review_id"], "KR-000002")
        assessment = service.run_spatial_assessment(
            "OI-000001", "sprint6-test", "KR-000002"
        )
        self.assertEqual(assessment["assessment_id"], "AS-000001")
        dossier = service.generate_dossier("OI-000001", "sprint6-test")
        self.assertEqual(dossier["dossier_id"], "ED-000001")
        return service

    def test_complete_boot_0020_archive_preserves_sources_and_closes_lifecycle(self):
        service = self.build_boot_chain()
        counts_before = {
            "evidence": len(service.repository.list_evidence("OI-000001", True)),
            "reviews": len(service.repository.list_knowledge_reviews("OI-000001")),
            "assessments": len(service.repository.list_assessments("OI-000001")),
            "dossiers": len(service.repository.list_dossiers("OI-000001")),
        }
        archive = service.create_archive(
            "OI-000001", "sprint6-test", "BOOT-0020 verification"
        )
        self.assertEqual(archive["archive_id"], "AR-000001")
        self.assertEqual(archive["archive_status"], "Archived")
        self.assertEqual(archive["knowledge_review_id"], "KR-000002")
        self.assertEqual(archive["assessment_id"], "AS-000001")
        self.assertEqual(archive["dossier_id"], "ED-000001")
        self.assertEqual(archive["record_count"], 5)
        self.assertEqual(archive["file_count"], 10)
        package = (service.archive_storage_dir / "AR-000001.zip").read_bytes()
        self.assertEqual(hashlib.sha256(package).hexdigest(), archive["package_hash"])
        with zipfile.ZipFile(BytesIO(package)) as zipped:
            self.assertEqual(set(zipped.namelist()), set(REQUIRED_ARCHIVE_FILES))
            manifest = json.loads(zipped.read("manifest.json"))
            self.assertEqual(manifest, archive["package_manifest"])
            for entry in manifest["files"]:
                payload = zipped.read(entry["name"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), entry["sha256"])
                self.assertEqual(len(payload), entry["size"])
        opportunity = service.get_opportunity("OI-000001", include_archived=True)
        self.assertTrue(opportunity["archived"])
        self.assertEqual(opportunity["lifecycle_state"], "Archived")
        self.assertTrue(all(step["state"] == "complete" for step in opportunity["workflow"]))
        self.assertFalse(service.get_dossier("OI-000001", "ED-000001")["stale"])
        self.assertEqual(
            counts_before,
            {
                "evidence": len(service.repository.list_evidence("OI-000001", True)),
                "reviews": len(service.repository.list_knowledge_reviews("OI-000001")),
                "assessments": len(service.repository.list_assessments("OI-000001")),
                "dossiers": len(service.repository.list_dossiers("OI-000001")),
            },
        )
        with self.assertRaises(ApiError) as context:
            service.edit_opportunity(
                "OI-000001", {"title": "Forbidden"}, "sprint6-test", 1
            )
        self.assertEqual(context.exception.code, "opportunity_archived")
        with self.assertRaises(ApiError) as context:
            service.update_managed_evidence(
                "OI-000001", "EV-000001", {"notes": "Forbidden"}, "sprint6-test", 1
            )
        self.assertEqual(context.exception.code, "opportunity_archived")

    def test_archive_rejects_incomplete_lifecycle(self):
        service = self.make_service()
        ensure_reference_opportunity(service)
        readiness = service.archive_readiness("OI-000001")
        self.assertFalse(readiness["ready"])
        self.assertGreaterEqual(len(readiness["errors"]), 4)
        with self.assertRaises(ApiError) as context:
            service.create_archive("OI-000001", "sprint6-test")
        self.assertEqual(context.exception.code, "archive_not_ready")

    def test_archive_rejects_stale_opportunity_and_evidence(self):
        opportunity_service = self.build_boot_chain("stale-opportunity")
        opportunity = opportunity_service.repository.get_opportunity("OI-000001")
        opportunity_service.edit_opportunity(
            "OI-000001",
            {"description": opportunity["description"] + " Changed."},
            "sprint6-test",
            opportunity["revision"],
        )
        self.assertFalse(opportunity_service.archive_readiness("OI-000001")["ready"])

        evidence_service = self.build_boot_chain("stale-evidence")
        evidence = evidence_service.get_managed_evidence("OI-000001", "EV-000001")
        evidence_service.update_managed_evidence(
            "OI-000001",
            "EV-000001",
            {"notes": evidence["notes"] + " Changed."},
            "sprint6-test",
            evidence["revision"],
        )
        self.assertFalse(evidence_service.archive_readiness("OI-000001")["ready"])

    def test_archive_rejects_stale_review_assessment_and_dossier(self):
        review_service = self.build_boot_chain("stale-review")
        review_service.supersede_knowledge_review(
            "OI-000001", "KR-000002", "sprint6-test"
        )
        self.assertFalse(review_service.archive_readiness("OI-000001")["ready"])

        assessment_service = self.build_boot_chain("stale-assessment")
        assessment_service.run_spatial_assessment(
            "OI-000001", "sprint6-test", "KR-000002"
        )
        self.assertFalse(assessment_service.archive_readiness("OI-000001")["ready"])

        dossier_service = self.build_boot_chain("stale-dossier")
        with dossier_service.repository.connect() as db:
            db.execute(
                "UPDATE executive_dossiers SET input_hash = ? WHERE dossier_id = ?",
                ("0" * 64, "ED-000001"),
            )
        self.assertTrue(dossier_service.get_dossier("OI-000001", "ED-000001")["stale"])
        self.assertFalse(dossier_service.archive_readiness("OI-000001")["ready"])

    def test_archive_builder_is_deterministic(self):
        members = {
            name: (b"%PDF-1.4\n%%EOF\n" if name.endswith(".pdf") else name.encode())
            for name in REQUIRED_ARCHIVE_FILES
            if name != "manifest.json"
        }
        arguments = {
            "archive_id": "AR-000001",
            "opportunity_id": "OI-000001",
            "archive_timestamp": "2026-07-20T12:00:00Z",
            "provenance": {"chain": ["OI-000001", "AR-000001"]},
            "record_count": 5,
            "members": members,
        }
        first, first_manifest = build_archive_package(**arguments)
        second, second_manifest = build_archive_package(**arguments)
        self.assertEqual(first, second)
        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual(hashlib.sha256(first).digest(), hashlib.sha256(second).digest())

    def test_archive_persists_and_replays_after_restart(self):
        service = self.build_boot_chain()
        created = service.create_archive("OI-000001", "sprint6-test")
        database_path = Path(service.repository.database_path)
        archive_dir = service.archive_storage_dir
        service.repository.close()
        self.repositories.remove(service.repository)
        repository = Repository(database_path)
        self.repositories.append(repository)
        restarted = AnchorIntelService(
            repository,
            evidence_storage_dir=self.root / "primary" / "evidence-files",
            archive_storage_dir=archive_dir,
        )
        persisted = restarted.get_archive("OI-000001", "AR-000001")
        self.assertEqual(persisted["package_hash"], created["package_hash"])
        self.assertEqual(
            restarted.replay_archive("OI-000001", "AR-000001", "restart-test")["result"],
            "PASS",
        )

    def test_archive_replay_detects_tampering_and_duplicate_creation(self):
        service = self.build_boot_chain()
        service.create_archive("OI-000001", "sprint6-test")
        with self.assertRaises(ApiError) as context:
            service.create_archive("OI-000001", "sprint6-test")
        self.assertEqual(context.exception.code, "archive_already_exists")
        package_path = service.archive_storage_dir / "AR-000001.zip"
        package = bytearray(package_path.read_bytes())
        package[len(package) // 2] ^= 0x01
        package_path.write_bytes(package)
        replay = service.replay_archive("OI-000001", "AR-000001", "tamper-test")
        self.assertEqual(replay["result"], "FAIL")
        self.assertFalse(replay["checks"]["package_hash"])
        actions = [event["action"] for event in service.repository.list_audit(100)]
        self.assertIn("archive.replay_failed", actions)

    def test_archive_api_ui_download_replay_and_audit(self):
        service = self.build_boot_chain()
        app = AnchorIntelApplication(service)
        created_response = app.handle(
            "POST",
            "/opportunities/OI-000001/archives",
            {"Content-Type": "application/json", "X-Actor": "api-test"},
            json.dumps({"reason": "API verification"}).encode(),
        )
        self.assertEqual(created_response.status, 201)
        created = json.loads(created_response.body)
        self.assertEqual(created["archive_id"], "AR-000001")

        detail = app.handle(
            "GET",
            "/opportunities/OI-000001/archives/AR-000001",
            {"Accept": "text/html"},
        )
        self.assertEqual(detail.status, 200)
        self.assertIn(b"Read-only archive", detail.body)
        self.assertIn(b"OI-000001", detail.body)
        self.assertIn(b"KR-000002", detail.body)

        download = app.handle(
            "GET", "/opportunities/OI-000001/archives/AR-000001/download"
        )
        self.assertEqual(download.status, 200)
        self.assertEqual(download.headers["Content-Type"], "application/zip")
        self.assertEqual(hashlib.sha256(download.body).hexdigest(), created["package_hash"])

        replay = app.handle(
            "POST", "/opportunities/OI-000001/archives/AR-000001/replay"
        )
        self.assertEqual(replay.status, 200)
        self.assertEqual(json.loads(replay.body)["result"], "PASS")
        actions = [event["action"] for event in service.repository.list_audit(100)]
        for expected in (
            "archive.prepared",
            "archive.completed",
            "archive.downloaded",
            "archive.replayed",
        ):
            self.assertIn(expected, actions)


if __name__ == "__main__":
    unittest.main()
