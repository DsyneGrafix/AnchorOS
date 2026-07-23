"""Customer Onboarding Pipeline errors."""


class CustomerPipelineError(RuntimeError):
    """Base error for Customer Onboarding Pipeline failures."""


class StageRequirementError(CustomerPipelineError):
    """Raised when a stage cannot satisfy an entry or exit criterion."""
