"""Narrow optional framework integration ports."""
from typing import Protocol

class PipelineEventPublisher(Protocol):
    def publish_pipeline_event(self, event_type: str, payload: dict) -> None: ...

class PipelineAuditSink(Protocol):
    def record_pipeline_transition(self, transition: dict) -> None: ...

class PipelineTransitionRepository(Protocol):
    def save(self, result) -> None: ...
    def get(self, pipeline_run_id: str): ...

class InMemoryPipelineTransitionRepository:
    def __init__(self): self._results = {}
    def save(self, result): self._results[result.pipeline_run_id] = result
    def get(self, pipeline_run_id): return self._results[pipeline_run_id]
