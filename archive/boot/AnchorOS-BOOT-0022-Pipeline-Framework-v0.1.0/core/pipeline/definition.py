"""Immutable deterministic pipeline definition."""
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping
from .errors import DuplicateStageIdentifier, InvalidPipelineDefinition, InvalidStageOrder
from .stage import PipelineStage

@dataclass(frozen=True, slots=True)
class PipelineDefinition:
    pipeline_id: str
    name: str
    version: str
    stages: tuple[PipelineStage, ...]
    initial_state: str
    terminal_success_state: str
    terminal_failure_state: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "stages", tuple(self.stages))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        self.validate()

    def validate(self) -> None:
        if not self.pipeline_id.strip() or not self.name.strip() or not self.version.strip():
            raise InvalidPipelineDefinition("Pipeline identity, name, and version are required.")
        if not self.stages:
            raise InvalidPipelineDefinition("At least one stage is required.")
        ids = [s.stage_id for s in self.stages]
        if len(ids) != len(set(ids)):
            raise DuplicateStageIdentifier("Stage identifiers must be unique.")
        positions = [s.position for s in self.stages]
        if positions != list(range(1, len(self.stages) + 1)):
            raise InvalidStageOrder("Stage positions must be contiguous and declared in execution order.")
