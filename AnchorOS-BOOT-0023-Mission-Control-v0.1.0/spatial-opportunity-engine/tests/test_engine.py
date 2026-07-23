import json
import unittest
from copy import deepcopy
from pathlib import Path

from spatial_engine.engine import InputError, SpatialEngine
from spatial_engine.models import Decision
from spatial_engine.report import render_markdown


ROOT = Path(__file__).resolve().parents[1]


def example():
    return json.loads((ROOT / "examples" / "rural_broadband.json").read_text())


class SpatialEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = SpatialEngine()

    def test_example_is_provisional_monitor(self):
        result = self.engine.analyze(example())
        self.assertEqual(result.recommendation, Decision.MONITOR)
        self.assertTrue(result.provisional)
        self.assertAlmostEqual(result.score, 62.5)
        self.assertEqual(result.gates["L"].status.value, "pass")

    def test_high_score_and_high_confidence_pursues(self):
        raw = example()
        for item in raw["evidence"]:
            item["state"] = "V"
            item["source"] = item["source"] or "Authoritative source"
        for item in raw["dimensions"].values():
            item["score"] = 4.5
        for gate in raw["gates"].values():
            gate["status"] = "pass"
        result = self.engine.analyze(raw)
        self.assertEqual(result.recommendation, Decision.PURSUE)
        self.assertFalse(result.provisional)
        self.assertEqual(result.score, 90.0)

    def test_failed_gate_overrides_high_score(self):
        raw = example()
        for item in raw["evidence"]:
            item["state"] = "V"
            item["source"] = item["source"] or "Authoritative source"
        for item in raw["dimensions"].values():
            item["score"] = 5
        for gate in raw["gates"].values():
            gate["status"] = "pass"
        raw["gates"]["A1"]["status"] = "fail"
        result = self.engine.analyze(raw)
        self.assertEqual(result.recommendation, Decision.HOLD)
        self.assertIn("A1", result.recommendation_reason)

    def test_fatal_reject_overrides_everything(self):
        raw = example()
        raw["fatal_constraints"] = [
            {
                "constraint_id": "F-001",
                "description": "Controlling authority prohibits the proposed use.",
                "disposition": "reject",
                "evidence_refs": ["E-001"]
            }
        ]
        result = self.engine.analyze(raw)
        self.assertEqual(result.recommendation, Decision.REJECT)

    def test_unknown_reference_is_rejected(self):
        raw = example()
        raw["dimensions"]["technical_fit"]["evidence_refs"].append("E-404")
        with self.assertRaises(InputError):
            self.engine.analyze(raw)

    def test_missing_lifecycle_control_fails_l_gate(self):
        raw = example()
        raw["lifecycle"]["owner"] = ""
        result = self.engine.analyze(raw)
        self.assertEqual(result.gates["L"].status.value, "fail")
        self.assertEqual(result.recommendation, Decision.HOLD)

    def test_expired_review_date_fails_l_gate(self):
        raw = example()
        raw["lifecycle"]["review_date"] = raw["assessment_date"]
        result = self.engine.analyze(raw)
        self.assertEqual(result.gates["L"].status.value, "fail")
        self.assertEqual(result.recommendation, Decision.HOLD)

    def test_markdown_contains_boundary_and_traceability(self):
        report = render_markdown(self.engine.analyze(example()))
        self.assertIn("## Mandatory gates", report)
        self.assertIn("`E-001`", report)
        self.assertIn("not engineering", report)


if __name__ == "__main__":
    unittest.main()
