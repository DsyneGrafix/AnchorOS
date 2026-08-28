import json
from pathlib import Path
import unittest

from frameworks.anchorstack import AnchorStack
from frameworks.anchorstack_validity import (
    ContinuationEvaluator,
    ContinuationSnapshot,
    DeterminationState,
    Validity,
)
from services.audit import Audit
from services.eventbus import EventBus


DIMENSION_NAMES = (
    "authority", "assumptions", "dependencies", "evidence",
    "constraints", "conditions", "scope", "communications",
)
VALID = {name: Validity.VALID for name in DIMENSION_NAMES}


class AnchorStackContinuationValidityTests(unittest.TestCase):
    def evaluate(self, **changes):
        dimensions = dict(VALID)
        dimensions.update(changes)
        snapshot = ContinuationSnapshot(
            execution_id="X-1",
            observed_at="2026-08-28T00:00:00Z",
            dimensions=dimensions,
            safe_exit_available=True,
            evidence_ids=("E2", "E1", "E1"),
        )
        return ContinuationEvaluator().evaluate(snapshot)

    def test_all_valid(self):
        self.assertEqual(
            self.evaluate().state,
            DeterminationState.CONTINUATION_VALID,
        )

    def test_invalid_authority_has_highest_precedence(self):
        result = self.evaluate(
            authority=Validity.INVALID,
            scope=Validity.INVALID,
        )
        self.assertEqual(
            result.state,
            DeterminationState.AUTHORITY_SUSPENDED,
        )

    def test_invalid_scope_requires_protective_hold(self):
        self.assertEqual(
            self.evaluate(scope=Validity.INVALID).state,
            DeterminationState.PROTECTIVE_HOLD,
        )

    def test_stale_assumption_requires_reassessment(self):
        self.assertEqual(
            self.evaluate(assumptions=Validity.STALE).state,
            DeterminationState.REASSESSMENT_REQUIRED,
        )

    def test_unknown_prevents_valid_determination(self):
        self.assertEqual(
            self.evaluate(evidence=Validity.UNKNOWN).state,
            DeterminationState.DETERMINATION_NOT_ESTABLISHED,
        )

    def test_no_safe_exit_escalates_degraded_state(self):
        dimensions = dict(VALID)
        dimensions["dependencies"] = Validity.STALE
        result = ContinuationEvaluator().evaluate(
            ContinuationSnapshot(
                execution_id="X-2",
                observed_at="2026-08-28T00:00:00Z",
                dimensions=dimensions,
                safe_exit_available=False,
            )
        )
        self.assertEqual(
            result.state,
            DeterminationState.PROTECTIVE_HOLD,
        )

    def test_determination_is_stable_and_never_selects_action(self):
        first = self.evaluate(scope=Validity.INVALID)
        second = self.evaluate(scope=Validity.INVALID)
        self.assertEqual(first.determination_id, second.determination_id)
        self.assertFalse(first.action_selected)

    def test_native_event_is_audited(self):
        event_bus = EventBus()
        audit = Audit()
        event_bus.subscribe(
            "anchorstack.continuation_validity.determined",
            audit.handle_event,
        )
        framework = AnchorStack(event_bus)
        result = framework.determine_continuation(
            execution_id="X-3",
            observed_at="2026-08-28T00:00:00Z",
            dimensions={name: "VALID" for name in DIMENSION_NAMES},
            safe_exit_available=True,
            evidence_ids=("E1",),
        )
        records = audit.get_records()
        self.assertTrue(result.continuation_valid)
        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0]["payload"]["determination_id"],
            result.determination_id,
        )
        self.assertFalse(records[0]["payload"]["action_selected"])

    def test_incident_replay(self):
        replay_path = (
            Path(__file__).parents[1]
            / "evidence"
            / "replays"
            / "AS-PR-HF-001.json"
        )
        replay = json.loads(replay_path.read_text())
        for item in replay["snapshots"]:
            result = ContinuationEvaluator().evaluate(
                ContinuationSnapshot(
                    execution_id=item["execution_id"],
                    observed_at=item["observed_at"],
                    dimensions={
                        name: Validity(value)
                        for name, value in item["dimensions"].items()
                    },
                    safe_exit_available=item["safe_exit_available"],
                    evidence_ids=tuple(item["evidence_ids"]),
                )
            )
            self.assertEqual(result.state.value, item["expected_state"])


if __name__ == "__main__":
    unittest.main()
