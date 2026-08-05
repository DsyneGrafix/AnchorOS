"""AIN-201 pipeline exceptions."""


class PipelineError(Exception):
    """Base exception for pipeline failures."""


class PipelineValidationError(PipelineError):
    """Raised when a request or stage input is invalid."""


class StageExecutionError(PipelineError):
    """Raised when a pipeline stage cannot complete."""


class ContinuationInvalidError(PipelineError):
    """Raised when continuation is not valid."""
