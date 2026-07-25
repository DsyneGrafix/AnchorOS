"""Explicit failures raised by the AnchorOS Pipeline Framework."""

class PipelineFrameworkError(RuntimeError):
    """Base framework error."""

class InvalidPipelineDefinition(PipelineFrameworkError):
    pass

class DuplicateStageIdentifier(InvalidPipelineDefinition):
    pass

class InvalidStageOrder(InvalidPipelineDefinition):
    pass

class PipelineEntryRejected(PipelineFrameworkError):
    pass

class StageExecutionFailed(PipelineFrameworkError):
    pass

class StageValidationFailed(PipelineFrameworkError):
    pass

class TransitionChainInvalid(PipelineFrameworkError):
    pass

class ReplayMismatch(PipelineFrameworkError):
    pass

class PipelineAlreadyExecuted(PipelineFrameworkError):
    pass
