"""Bounded pipeline execution context."""
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping
from .hashing import normalize

@dataclass(slots=True)
class PipelineContext:
    pipeline_run_id: str
    normalized_input: Any
    current_state: str
    stage_position: int = 0
    outputs: dict[str, Any] = field(default_factory=dict)
    execution_metadata: Mapping[str, Any] = field(default_factory=dict)
    domain_context: Any = None

    def __post_init__(self) -> None:
        self.normalized_input = normalize(self.normalized_input)
        self.execution_metadata = MappingProxyType(dict(normalize(dict(self.execution_metadata))))
