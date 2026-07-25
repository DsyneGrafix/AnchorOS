"""Structured pipeline execution and replay results."""
from dataclasses import dataclass, field
from typing import Any
from .transition import PipelineTransition

@dataclass(slots=True)
class PipelineResult:
    pipeline_id: str
    pipeline_name: str
    pipeline_version: str
    pipeline_run_id: str
    normalized_input: Any
    initial_state: str
    terminal_state: str
    success: bool
    reason_code: str
    message: str
    outputs: dict[str, Any] = field(default_factory=dict)
    transitions: list[PipelineTransition] = field(default_factory=list)

    @property
    def final_evidence_hash(self) -> str:
        return self.transitions[-1].transition_hash if self.transitions else ""

@dataclass(frozen=True, slots=True)
class PipelineReplayResult:
    verified: bool
    pipeline_id: str
    pipeline_run_id: str
    expected_hash: str
    actual_hash: str
    expected_transitions: int
    actual_transitions: int
    reason_code: str
    message: str
