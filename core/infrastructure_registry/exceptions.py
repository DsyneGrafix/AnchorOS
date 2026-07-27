"""Domain exceptions for AOS-140 registry services."""


class RegistryServiceError(Exception):
    """Base class for registry service failures."""


class RegistryValidationError(RegistryServiceError, ValueError):
    """Raised when a requested operation violates a registry rule."""


class DuplicateEntityError(RegistryValidationError):
    """Raised when a unique registry value is already in use."""


class InvalidLifecycleTransitionError(RegistryValidationError):
    """Raised when an entity lifecycle transition is not permitted."""
