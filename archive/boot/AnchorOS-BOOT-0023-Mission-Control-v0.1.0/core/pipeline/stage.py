"""Immutable pipeline stage definitions and outcomes."""
from dataclasses import dataclass, field
from typing import Any, Callable

StageHandler = Callable[[Any], Any]
StageValidator = Callable[[Any], bool]

@dataclass(frozen=True, slots=True)
class StageOutcome:
    success: bool
    resulting_state: str
    output: Any = field(default_factory=dict)
    reason_code: str = "PASS"
    message: str = ""

@dataclass(frozen=True, slots=True)
class PipelineStage:
    stage_id: str
    name: str
    position: int
    success_state: str
    handler: StageHandler
    entry_validator: StageValidator | None = None
    completion_validator: StageValidator | None = None
    failure_behavior: str = "HALT"
    allow_skip: bool = False
