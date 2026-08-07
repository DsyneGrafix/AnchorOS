from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from anchorinsight_web import create_app
from anchorinsight_web.boot import (
    BootEventStatus,
    BootOverallStatus,
    BootStatusService,
)


class BootStatusModelTests(unittest.TestCase):
    def test_completed_successful_boot_is_online(self) -> None:
        service = BootStatusService()
        service.start()
        service.record(
            component="Test Service",
            stage="Initialization",
            status=BootEventStatus.PASSED,
            message="Initialized.",
        )
        service.complete()

        snapshot = service.snapshot()
        self.assertEqual(snapshot["status"], BootOverallStatus.ONLINE.value)
        self.assertEqual(snapshot["summary"]["events"], 1)
        self.assertEqual(snapshot["summary"]["passed"], 1)
        self.assertEqual(snapshot["events"][0]["sequence"], 1)

    def test_failed_event_marks_boot_degraded(self) -> None:
        service = BootStatusService()
        service.start()
        service.record(
            component="Test Service",
            stage="Health",
            status=BootEventStatus.FAILED,
            message="Health check failed.",
        )
        service.complete()

        snapshot = service.snapshot()
        self.assertEqual(snapshot["status"], BootOverallStatus.DEGRADED.value)
        self.assertEqual(snapshot["summary"]["failed"], 1)


class BootStatusWebTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "anchorinsight.db"
        self.app = create_app(self.db_path, testing=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_boot_status_api_reports_observed_initialization(self) -> None:
        response = self.client.get("/api/boot/status")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["boot"], "BOOT-0028")
        self.assertEqual(payload["status"], "ONLINE")
        self.assertGreaterEqual(payload["summary"]["passed"], 4)
        self.assertEqual(payload["summary"]["failed"], 0)
        self.assertEqual(
            [event["sequence"] for event in payload["events"]],
            list(range(1, len(payload["events"]) + 1)),
        )
        self.assertIn(
            "Commercial Intelligence Registry",
            {event["component"] for event in payload["events"]},
        )

    def test_boot_screen_renders_trace(self) -> None:
        response = self.client.get("/boot")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"BOOT-0028", response.data)
        self.assertIn(b"Platform Initialization", response.data)
        self.assertIn(b"Commercial Intelligence Registry", response.data)
        self.assertIn(b"Observed Boot Trace", response.data)

    def test_health_api_includes_boot_status(self) -> None:
        response = self.client.get("/api/health")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["boot"]["status"], "ONLINE")
        self.assertEqual(payload["boot"]["version"], "1.0.0")

    def test_boot_css_is_served(self) -> None:
        response = self.client.get("/static/boot.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"boot-trace", response.data)


if __name__ == "__main__":
    unittest.main()
