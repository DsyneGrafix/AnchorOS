"""Native AnchorGrid-to-AnchorStack submission seam for AG-BPE-CVA.

The adapter verifies and transports product evidence. It does not determine
continuation validity or select, recommend, route, block, or execute an action.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from frameworks.anchorstack import AnchorStack
from frameworks.anchorstack_validity import (
    ContinuationDetermination,
    MATERIAL_DIMENSIONS,
)
from services.event import AnchorEvent
from services.eventbus import EventBus


PRODUCT_ID = "AG-BPE-CVA"
PRODUCT_VERSION = "0.1.0"
PRODUCT_COMMIT = "c31964acc3543e346b8222e68ec87f40c3afbf9f"
PRODUCT_SCHEMA_VERSION = "1.0"
ANCHOROS_RUNTIME_VERSION = "0.1.0 Alpha"
VALIDITY_VALUES = frozenset({"VALID", "INVALID", "STALE", "UNKNOWN"})
SNAPSHOT_FIELDS = frozenset(
    {
        "execution_id",
        "observed_at",
        "dimensions",
        "safe_exit_available",
        "evidence_ids",
    }
)
PREPARED_EVENT_FIELDS = frozenset(
    {
        "event_type",
        "schema_version",
        "product_id",
        "card_id",
        "execution_id",
        "observed_at",
        "snapshot_sha256",
        "evidence_ids",
        "action_selected",
    }
)


class AnchorGridBPEAdapterError(ValueError):
    """Raised before publication when the integration contract is violated."""


@dataclass(frozen=True, slots=True)
class AnchorGridBPEResult:
    """Evidence returned by a completed native submission."""

    determination: ContinuationDetermination
    prepared_event_id: str
    receipt_event_id: str
    receipt: Mapping[str, Any]


class AnchorGridBPEAdapter:
    """Verify a product snapshot and delegate determination to AnchorStack."""

    def __init__(self, event_bus: EventBus) -> None:
        if not isinstance(event_bus, EventBus):
            raise TypeError("event_bus must be an EventBus")
        self.event_bus = event_bus

    def submit(
        self,
        *,
        snapshot: Mapping[str, Any],
        prepared_event: Mapping[str, Any],
        anchorstack: AnchorStack,
        replay_id: str | None = None,
    ) -> AnchorGridBPEResult:
        """Publish evidence, delegate determination, and issue a bound receipt."""

        if not isinstance(anchorstack, AnchorStack):
            raise TypeError("anchorstack must be the released AnchorStack framework")

        normalized = self._validate_snapshot(snapshot)
        domain_event = self._validate_prepared_event(prepared_event, normalized)
        replay_reference = self._validate_replay_id(replay_id)

        prepared_payload = dict(domain_event)
        prepared_payload.update(
            {
                "product_version": PRODUCT_VERSION,
                "product_commit": PRODUCT_COMMIT,
                "anchoros_runtime_version": ANCHOROS_RUNTIME_VERSION,
                "replay_id": replay_reference,
                "action_selected": False,
            }
        )
        native_prepared_event = AnchorEvent(
            source="AnchorGrid",
            event_type="anchorgrid.equipment_evidence.snapshot_prepared",
            message=(
                "Equipment evidence snapshot prepared for "
                "continuation-validity determination."
            ),
            severity="INFO",
            payload=prepared_payload,
        )
        self.event_bus.publish(native_prepared_event)

        determination = anchorstack.determine_continuation(
            execution_id=normalized["execution_id"],
            observed_at=normalized["observed_at"],
            dimensions=normalized["dimensions"],
            safe_exit_available=normalized["safe_exit_available"],
            evidence_ids=tuple(normalized["evidence_ids"]),
        )
        if determination.action_selected:
            raise RuntimeError("AnchorStack returned an action-selecting determination")

        receipt_material = {
            "schema_version": PRODUCT_SCHEMA_VERSION,
            "product_id": PRODUCT_ID,
            "product_version": PRODUCT_VERSION,
            "product_commit": PRODUCT_COMMIT,
            "anchoros_runtime_version": ANCHOROS_RUNTIME_VERSION,
            "card_id": domain_event["card_id"],
            "execution_id": normalized["execution_id"],
            "snapshot_sha256": domain_event["snapshot_sha256"],
            "determination_id": determination.determination_id,
            "determination_state": determination.state.value,
            "replay_id": replay_reference,
            "action_selected": False,
        }
        receipt_id = "AG-CVR-" + sha256(
            json.dumps(
                receipt_material,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:24]
        receipt = {
            "receipt_id": receipt_id,
            "prepared_event_id": native_prepared_event.event_id,
            **receipt_material,
        }
        receipt_event = AnchorEvent(
            source="AnchorGrid",
            event_type="anchorgrid.equipment_evidence.determination_received",
            message=(
                "AnchorStack continuation-validity determination received "
                f"for equipment evidence card {domain_event['card_id']}."
            ),
            severity=("INFO" if determination.continuation_valid else "WARNING"),
            payload=receipt,
        )
        self.event_bus.publish(receipt_event)

        return AnchorGridBPEResult(
            determination=determination,
            prepared_event_id=native_prepared_event.event_id,
            receipt_event_id=receipt_event.event_id,
            receipt=receipt.copy(),
        )

    @staticmethod
    def _validate_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(snapshot, Mapping):
            raise AnchorGridBPEAdapterError("snapshot must be an object")
        if frozenset(snapshot.keys()) != SNAPSHOT_FIELDS:
            raise AnchorGridBPEAdapterError("snapshot field contract mismatch")

        execution_id = snapshot["execution_id"]
        observed_at = snapshot["observed_at"]
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise AnchorGridBPEAdapterError("snapshot execution_id is required")
        if not isinstance(observed_at, str) or not observed_at.strip():
            raise AnchorGridBPEAdapterError("snapshot observed_at is required")
        if not isinstance(snapshot["safe_exit_available"], bool):
            raise AnchorGridBPEAdapterError("safe_exit_available must be boolean")

        dimensions = snapshot["dimensions"]
        if not isinstance(dimensions, Mapping):
            raise AnchorGridBPEAdapterError("dimensions must be an object")
        if tuple(dimensions.keys()) != MATERIAL_DIMENSIONS:
            raise AnchorGridBPEAdapterError(
                "dimensions must contain all eight fields in canonical order"
            )
        if any(value not in VALIDITY_VALUES for value in dimensions.values()):
            raise AnchorGridBPEAdapterError("snapshot contains an invalid validity value")

        evidence_ids = snapshot["evidence_ids"]
        if not isinstance(evidence_ids, list):
            raise AnchorGridBPEAdapterError("evidence_ids must be an array")
        if (
            any(not isinstance(item, str) or not item.strip() for item in evidence_ids)
            or evidence_ids != sorted(set(evidence_ids))
        ):
            raise AnchorGridBPEAdapterError(
                "evidence_ids must be unique non-empty strings in sorted order"
            )

        return {
            "execution_id": execution_id,
            "observed_at": observed_at,
            "dimensions": dict(dimensions),
            "safe_exit_available": snapshot["safe_exit_available"],
            "evidence_ids": list(evidence_ids),
        }

    @staticmethod
    def _validate_prepared_event(
        event: Mapping[str, Any],
        snapshot: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(event, Mapping):
            raise AnchorGridBPEAdapterError("prepared_event must be an object")
        if frozenset(event.keys()) != PREPARED_EVENT_FIELDS:
            raise AnchorGridBPEAdapterError("prepared_event field contract mismatch")
        if event["event_type"] != "anchorgrid.equipment_evidence.snapshot_prepared":
            raise AnchorGridBPEAdapterError("prepared_event type is invalid")
        if event["schema_version"] != PRODUCT_SCHEMA_VERSION:
            raise AnchorGridBPEAdapterError("prepared_event schema version is invalid")
        if event["product_id"] != PRODUCT_ID:
            raise AnchorGridBPEAdapterError("prepared_event product ID is invalid")
        if event["action_selected"] is not False:
            raise AnchorGridBPEAdapterError("prepared_event selected an action")
        if not isinstance(event["card_id"], str) or not event["card_id"].strip():
            raise AnchorGridBPEAdapterError("prepared_event card_id is required")
        for field in ("execution_id", "observed_at", "evidence_ids"):
            if event[field] != snapshot[field]:
                raise AnchorGridBPEAdapterError(
                    f"prepared_event {field} does not match the snapshot"
                )

        expected_digest = sha256(
            json.dumps(
                snapshot,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        if event["snapshot_sha256"] != expected_digest:
            raise AnchorGridBPEAdapterError("prepared_event snapshot digest mismatch")
        return dict(event)

    @staticmethod
    def _validate_replay_id(replay_id: str | None) -> str | None:
        if replay_id is None:
            return None
        if not isinstance(replay_id, str) or not replay_id.strip():
            raise AnchorGridBPEAdapterError("replay_id must be non-empty when supplied")
        return replay_id.strip()
