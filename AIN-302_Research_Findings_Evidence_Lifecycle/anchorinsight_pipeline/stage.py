"""AIN-201 pipeline stage contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .context import PipelineContext
from .models import StageDefinition, StageResult, StageStatus, utc_now


@dataclass
class StageExecution:
    status: StageStatus = StageStatus.PASSED
    decision: str = "CONTINUE"
    reason_code: str = "STAGE_COMPLETE"
    input_references: list[str] | None = None
    output_references: list[str] | None = None
    warnings: list[str] | None = None
    evidence_references: list[str] | None = None
    details: dict[str, Any] | None = None


class PipelineStage(ABC):
    name = "Unnamed Stage"
    version = "1.0"
    always_required = True
    requested_output: str | None = None

    def definition(self, requested_outputs: tuple[str, ...]) -> StageDefinition:
        required = self.always_required or (
            self.requested_output is not None and self.requested_output in requested_outputs
        )
        return StageDefinition(
            name=self.name,
            version=self.version,
            required=required,
            requested_output=self.requested_output,
        )

    def validate(self, context: PipelineContext) -> None:
        """Validate inputs before executing."""

    @abstractmethod
    def execute(self, context: PipelineContext) -> StageExecution:
        """Execute the stage."""

    def rollback(self, context: PipelineContext) -> None:
        """Compensating action for stages that support rollback."""

    def run(self, context: PipelineContext, retry_count: int = 0) -> StageResult:
        definition = self.definition(context.request.requested_outputs)
        started = utc_now()
        self.validate(context)
        execution = self.execute(context)
        result = StageResult(
            stage_id=str(uuid4()),
            pipeline_request_id=context.request.pipeline_request_id,
            stage_name=self.name,
            stage_version=self.version,
            required=definition.required,
            status=execution.status,
            started_at=started,
            completed_at=utc_now(),
            input_references=execution.input_references or [],
            output_references=execution.output_references or [],
            decision=execution.decision,
            reason_code=execution.reason_code,
            warnings=execution.warnings or [],
            evidence_references=execution.evidence_references or [],
            audit_reference=f"AUD-{uuid4()}",
            retry_count=retry_count,
            details=execution.details or {},
        )
        context.stage_results.append(result)
        context.warnings.extend(result.warnings)
        return result
