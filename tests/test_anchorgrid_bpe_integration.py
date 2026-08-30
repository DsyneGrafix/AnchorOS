from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from frameworks.anchorgrid import AnchorGrid
from frameworks.anchorgrid_bpe_adapter import (
    ANCHOROS_RUNTIME_VERSION,
    PRODUCT_COMMIT,
    PRODUCT_VERSION,
    AnchorGridBPEAdapterError,
)
from frameworks.anchorstack import AnchorStack
from services.audit import Audit
from services.eventbus import EventBus


ROOT = Path(__file__).resolve().parents[1]
REPLAY_PATH = (
    ROOT
    / "evidence"
    / "replays"
    / "AG-PR-003_AnchorOS_Integration_Replay_v0.1.json"
)
EVENT_TYPES = (
    "anchorgrid.equipment_evidence.snapshot_prepared",
    "anchorstack.continuation_validity.determined",
    "anchorgrid.equipment_evidence.determination_received",
)


def snapshot_digest(snapshot):
    material = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(material).hexdigest()


def prepared_event(snapshot, card_id):
    return {
        "event_type": "anchorgrid.equipment_evidence.snapshot_prepared",
        "schema_version": "1.0",
        "product_id": "AG-BPE-CVA",
        "card_id": card_id,
        "execution_id": snapshot["execution_id"],
        "observed_at": snapshot["observed_at"],
        "snapshot_sha256": snapshot_digest(snapshot),
        "evidence_ids": list(snapshot["evidence_ids"]),
        "action_selected": False,
    }


class AnchorGridBPEIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.audit = Audit()
        for event_type in EVENT_TYPES:
            self.event_bus.subscribe(event_type, self.audit.handle_event)
        self.anchorgrid = AnchorGrid(self.event_bus)
        self.anchorstack = AnchorStack(self.event_bus)
        self.replay = json.loads(REPLAY_PATH.read_text(encoding="utf-8"))

    def submit(self, item):
        snapshot = {
            "execution_id": item["execution_id"],
            "observed_at": item["observed_at"],
            "dimensions": dict(item["dimensions"]),
            "safe_exit_available": item["safe_exit_available"],
            "evidence_ids": list(item["evidence_ids"]),
        }
        return self.anchorgrid.submit_equipment_snapshot(
            snapshot=snapshot,
            prepared_event=prepared_event(snapshot, item["card_id"]),
            anchorstack=self.anchorstack,
            replay_id=self.replay["replay_id"],
        )

    def test_native_event_order_and_audit_capture(self):
        result = self.submit(self.replay["snapshots"][1])
        records = self.audit.get_records()

        self.assertEqual(
            [
                "anchorgrid.equipment_evidence.snapshot_prepared",
                "anchorstack.continuation_validity.determined",
                "anchorgrid.equipment_evidence.determination_received",
            ],
            [record["event_type"] for record in records],
        )
        self.assertEqual(["AnchorGrid", "AnchorStack", "AnchorGrid"], [
            record["source"] for record in records
        ])
        self.assertEqual("PROTECTIVE_HOLD", result.determination.state.value)
        self.assertFalse(result.determination.action_selected)
        self.assertEqual(result.prepared_event_id, records[0]["event_id"])
        self.assertEqual(result.receipt_event_id, records[2]["event_id"])

    def test_receipt_binds_product_runtime_snapshot_and_determination(self):
        item = self.replay["snapshots"][0]
        result = self.submit(item)
        receipt = result.receipt

        self.assertEqual(PRODUCT_VERSION, receipt["product_version"])
        self.assertEqual(PRODUCT_COMMIT, receipt["product_commit"])
        self.assertEqual(
            ANCHOROS_RUNTIME_VERSION,
            receipt["anchoros_runtime_version"],
        )
        self.assertEqual("AG-PR-003", receipt["replay_id"])
        self.assertEqual(
            result.determination.determination_id,
            receipt["determination_id"],
        )
        self.assertFalse(receipt["action_selected"])

    def test_tampered_snapshot_digest_is_rejected_before_publication(self):
        item = self.replay["snapshots"][0]
        snapshot = {
            "execution_id": item["execution_id"],
            "observed_at": item["observed_at"],
            "dimensions": dict(item["dimensions"]),
            "safe_exit_available": item["safe_exit_available"],
            "evidence_ids": list(item["evidence_ids"]),
        }
        event = prepared_event(snapshot, item["card_id"])
        event["snapshot_sha256"] = "0" * 64

        with self.assertRaises(AnchorGridBPEAdapterError):
            self.anchorgrid.submit_equipment_snapshot(
                snapshot=snapshot,
                prepared_event=event,
                anchorstack=self.anchorstack,
                replay_id="AG-PR-003",
            )
        self.assertEqual([], self.audit.get_records())

    def test_action_selecting_product_event_is_rejected(self):
        item = self.replay["snapshots"][0]
        snapshot = {
            "execution_id": item["execution_id"],
            "observed_at": item["observed_at"],
            "dimensions": dict(item["dimensions"]),
            "safe_exit_available": item["safe_exit_available"],
            "evidence_ids": list(item["evidence_ids"]),
        }
        event = prepared_event(snapshot, item["card_id"])
        event["action_selected"] = True

        with self.assertRaises(AnchorGridBPEAdapterError):
            self.anchorgrid.submit_equipment_snapshot(
                snapshot=snapshot,
                prepared_event=event,
                anchorstack=self.anchorstack,
            )
        self.assertEqual([], self.audit.get_records())

    def test_extra_snapshot_field_is_rejected(self):
        item = self.replay["snapshots"][0]
        snapshot = {
            "execution_id": item["execution_id"],
            "observed_at": item["observed_at"],
            "dimensions": dict(item["dimensions"]),
            "safe_exit_available": item["safe_exit_available"],
            "evidence_ids": list(item["evidence_ids"]),
            "selected_action": "ISOLATE",
        }
        event_snapshot = deepcopy(snapshot)
        event_snapshot.pop("selected_action")

        with self.assertRaises(AnchorGridBPEAdapterError):
            self.anchorgrid.submit_equipment_snapshot(
                snapshot=snapshot,
                prepared_event=prepared_event(
                    event_snapshot,
                    item["card_id"],
                ),
                anchorstack=self.anchorstack,
            )
        self.assertEqual([], self.audit.get_records())

    def test_released_anchorstack_instance_is_required(self):
        item = self.replay["snapshots"][0]
        snapshot = {
            "execution_id": item["execution_id"],
            "observed_at": item["observed_at"],
            "dimensions": dict(item["dimensions"]),
            "safe_exit_available": item["safe_exit_available"],
            "evidence_ids": list(item["evidence_ids"]),
        }
        with self.assertRaises(TypeError):
            self.anchorgrid.submit_equipment_snapshot(
                snapshot=snapshot,
                prepared_event=prepared_event(snapshot, item["card_id"]),
                anchorstack=object(),
            )

    def test_ag_pr_003_native_replay(self):
        observed_states = []
        for item in self.replay["snapshots"]:
            start = len(self.audit.get_records())
            result = self.submit(item)
            records = self.audit.get_records()[start:]

            observed_states.append(result.determination.state.value)
            self.assertEqual(
                item["expected"]["determination_id"],
                result.determination.determination_id,
            )
            self.assertEqual(3, len(records))
            self.assertTrue(
                all(
                    record["payload"]["action_selected"] is False
                    for record in records
                )
            )

        self.assertEqual(
            [
                "CONTINUATION_VALID",
                "PROTECTIVE_HOLD",
                "REASSESSMENT_REQUIRED",
                "CONTINUATION_VALID",
            ],
            observed_states,
        )


if __name__ == "__main__":
    unittest.main()
