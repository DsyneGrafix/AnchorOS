"""AIN-201 replay support."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .store import JsonPipelineStore


@dataclass(frozen=True)
class ReplayComparison:
    original_pipeline_id: str
    replay_pipeline_id: str
    status_changed: bool
    integrity_changed: bool
    details: dict[str, Any]


class ReplayManager:
    """Loads immutable proof artifacts and compares receipts."""

    def __init__(self, store: JsonPipelineStore) -> None:
        self.store = store

    def load_original(self, pipeline_id: str) -> dict[str, Any]:
        return {
            "manifest": self.store.load_manifest(pipeline_id),
            "receipt": self.store.load_receipt(pipeline_id),
        }

    def compare(self, original_pipeline_id: str, replay_pipeline_id: str) -> ReplayComparison:
        original = self.store.load_receipt(original_pipeline_id)
        replay = self.store.load_receipt(replay_pipeline_id)
        return ReplayComparison(
            original_pipeline_id=original_pipeline_id,
            replay_pipeline_id=replay_pipeline_id,
            status_changed=original["status"] != replay["status"],
            integrity_changed=original["integrity_hash"] != replay["integrity_hash"],
            details={
                "original_status": original["status"],
                "replay_status": replay["status"],
                "original_required_passed": original["required_stages_passed"],
                "replay_required_passed": replay["required_stages_passed"],
            },
        )
