"""AnchorOS Customer Onboarding Pipeline (CP-001 through CP-009)."""

from .engine import CustomerPipelineEngine
from .lifecycle import CustomerLifecycleManager
from .models import (
    CustomerRecord,
    CustomerState,
    OnboardingRequest,
    ReplayResult,
)
from .security import SecurityCoreGateway
from .stages import CUSTOMER_PIPELINE_STAGES, StageDefinition

__all__ = [
    "CUSTOMER_PIPELINE_STAGES",
    "CustomerLifecycleManager",
    "CustomerPipelineEngine",
    "CustomerRecord",
    "CustomerState",
    "OnboardingRequest",
    "ReplayResult",
    "SecurityCoreGateway",
    "StageDefinition",
]
