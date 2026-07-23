import json
import time
import unittest
from urllib.request import urlopen

from applications.mission_control.application import MissionControl
from services.audit import Audit
from services.event import AnchorEvent
from services.eventbus import EventBus


class MissionControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event_bus = EventBus()
        self.audit = Audit()
        self.event_bus.subscribe("application.started", self.audit.handle_event)
        self.event_bus.subscribe("application.stopped", self.audit.handle_event)
        self.app = MissionControl(
            event_bus=self.event_bus,
            audit=self.audit,
            port=18080,
        )
        self.app.set_snapshot_provider(
            lambda: {
                "platform_status": "HEALTHY",
                "manifest": {"product": "AnchorOS", "boot": "0023"},
                "services": ["Audit Engine"],
                "frameworks": ["AnchorStack"],
                "applications": ["Mission Control"],
                "health": {"status": "HEALTHY", "modules": []},
                "audit": self.audit.get_records(),
                "pipeline": {"verified": True, "passed": 8, "total": 8},
            }
        )

    def tearDown(self) -> None:
        if self.app.status == "Running":
            self.app.stop()

    def test_start_and_stop_lifecycle(self) -> None:
        self.app.start()
        self.assertEqual(self.app.status, "Running")
        self.assertTrue(self.app.url.startswith("http://127.0.0.1:"))
        self.app.stop()
        self.assertEqual(self.app.status, "Stopped")

    def test_status_and_health_endpoints(self) -> None:
        self.app.start()
        time.sleep(0.05)
        with urlopen(f"{self.app.url}/api/v1/status", timeout=2) as response:
            payload = json.load(response)
        self.assertEqual(payload["platform_status"], "HEALTHY")
        self.assertEqual(payload["manifest"]["boot"], "0023")
        with urlopen(f"{self.app.url}/api/v1/health", timeout=2) as response:
            health = json.load(response)
        self.assertEqual(health["status"], "HEALTHY")

    def test_dashboard_is_served(self) -> None:
        self.app.start()
        with urlopen(self.app.url, timeout=2) as response:
            html = response.read().decode("utf-8")
        self.assertIn("AnchorOS", html)
        self.assertIn("Mission Control", html)

    def test_event_bus_updates_runtime(self) -> None:
        event = AnchorEvent(
            source="Test Framework",
            event_type="framework.started",
            message="Test Framework entered the Running state.",
        )
        self.event_bus.publish(event)
        events = self.app.runtime.events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_id"], event.event_id)


if __name__ == "__main__":
    unittest.main()
