"""Bounded, safe errors raised by Security Core v0.1."""


class SecurityCoreError(Exception):
    """Base error carrying a stable, non-sensitive reason code."""

    reason_code = "SECURITY_CORE_ERROR"

    def __init__(self, message: str, *, reason_code: str | None = None) -> None:
        super().__init__(message)
        if reason_code is not None:
            self.reason_code = reason_code


class SecurityConfigurationError(SecurityCoreError):
    reason_code = "INVALID_CONFIGURATION"


class SecurityValidationError(SecurityCoreError):
    reason_code = "INVALID_INPUT"


class SecurityUnavailableError(SecurityCoreError):
    reason_code = "SERVICE_UNAVAILABLE"


class IdempotencyConflictError(SecurityCoreError):
    reason_code = "IDEMPOTENCY_CONFLICT"


class EvidenceVerificationError(SecurityCoreError):
    reason_code = "EVIDENCE_VERIFICATION_FAILED"
