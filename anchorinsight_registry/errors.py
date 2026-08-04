"""AIN-101 domain errors."""
from __future__ import annotations


class RegistryServiceError(RuntimeError):
    """Base error for Registry Service failures."""


class ValidationError(RegistryServiceError):
    """Raised when a command violates service-level validation."""


class NotFoundError(RegistryServiceError):
    """Raised when a requested registry record cannot be found."""


class ConflictError(RegistryServiceError):
    """Raised when a command conflicts with an existing registry record."""


class LifecycleError(RegistryServiceError):
    """Raised when a requested lifecycle transition is invalid."""
