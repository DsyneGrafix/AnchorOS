"""Deterministic, ordered, fail-closed pipeline runner."""
from copy import deepcopy
from typing import Any
from .context import PipelineContext
from .errors import PipelineEntryRejected, StageValidationFailed
from .hashing import canonical_hash, normalize
from .result import PipelineResult
from .stage import StageOutcome
from .transition import PipelineTransition

class PipelineRunner:
    def __init__(self, *, hooks=None, event_publisher=None, audit_sink=None, repository=None):
        self.hooks = hooks
        self.event_publisher = event_publisher
        self.audit_sink = audit_sink
        self.repository = repository

    def run(self, definition, pipeline_input: Any, *, pipeline_run_id: str | None = None, domain_context=None, execution_metadata=None):
        definition.validate()
        normalized = normalize(pipeline_input)
        run_id = pipeline_run_id or f"{definition.pipeline_id}:{canonical_hash(normalized)[:16]}"
        context = PipelineContext(run_id, normalized, definition.initial_state, execution_metadata=execution_metadata or {}, domain_context=domain_context)
        transitions = []
        if self.hooks: self.hooks.before_pipeline(context)
        for stage in definition.stages:
            context.stage_position = stage.position
            prior = context.current_state
            try:
                if self.hooks: self.hooks.before_stage(context, stage)
                if stage.entry_validator and not stage.entry_validator(context):
                    raise PipelineEntryRejected(f"Entry validation rejected {stage.stage_id}.")
                raw = stage.handler(context)
                outcome = raw if isinstance(raw, StageOutcome) else StageOutcome(True, stage.success_state, raw)
                if not outcome.success:
                    raise StageValidationFailed(outcome.message or outcome.reason_code)
                context.outputs[stage.stage_id] = normalize(outcome.output)
                context.current_state = outcome.resulting_state
                if stage.completion_validator and not stage.completion_validator(context):
                    raise StageValidationFailed(f"Completion validation rejected {stage.stage_id}.")
                status, reason, message, output = "PASS", outcome.reason_code, outcome.message, outcome.output
            except Exception as error:
                context.current_state = definition.terminal_failure_state
                status, reason, message, output = "FAIL", type(error).__name__, str(error), {"error": str(error)}
            transition = PipelineTransition.create(
                transition_id=f"{run_id}:{len(transitions)+1:04d}", sequence=len(transitions)+1,
                pipeline_id=definition.pipeline_id, pipeline_run_id=run_id,
                stage_id=stage.stage_id, stage_name=stage.name, prior_state=prior,
                resulting_state=context.current_state, outcome=status, reason_code=reason,
                normalized_input_hash=canonical_hash(normalized), stage_output_hash=canonical_hash(output),
                previous_hash=transitions[-1].transition_hash if transitions else "", output=output)
            transitions.append(transition)
            if self.audit_sink: self.audit_sink.record_pipeline_transition(transition.to_dict())
            if self.event_publisher: self.event_publisher.publish_pipeline_event("pipeline.stage.completed" if status == "PASS" else "pipeline.stage.failed", transition.to_dict())
            if self.hooks:
                if status == "PASS": self.hooks.after_stage(context, stage, transition)
                else: self.hooks.on_failure(context, stage, transition)
            if status == "FAIL": break
        success = bool(transitions) and transitions[-1].outcome == "PASS" and context.current_state == definition.terminal_success_state
        if not success and context.current_state != definition.terminal_failure_state:
            context.current_state = definition.terminal_failure_state
        result = PipelineResult(definition.pipeline_id, definition.name, definition.version, run_id, normalized,
            definition.initial_state, context.current_state, success, "PASS" if success else transitions[-1].reason_code,
            "Pipeline completed successfully." if success else transitions[-1].output.get("error", "Pipeline failed."),
            deepcopy(context.outputs), transitions)
        if self.hooks:
            if not success: self.hooks.on_halt(context, result)
            self.hooks.after_pipeline(context, result)
        if self.repository: self.repository.save(result)
        return result

    def execute_ordered(self, stages, execute_stage):
        """Domain adapter: deterministic ordered iteration with immediate halt."""
        for stage in tuple(stages):
            if not execute_stage(stage):
                break
