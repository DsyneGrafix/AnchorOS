"""Initial bounded role-based authorization policy."""

from .models import AuthorizationDecision


def decide_role_authorization(
    *,
    identity_registered: bool,
    assigned_roles: tuple[str, ...],
    required_role: str,
) -> tuple[AuthorizationDecision, str]:
    """Default-DENY decision for the BOOT-0021 role model."""

    if not identity_registered:
        return AuthorizationDecision.DENY, "UNKNOWN_IDENTITY"
    if not required_role:
        return AuthorizationDecision.DENY, "INCOMPLETE_REQUIREMENTS"
    if required_role not in assigned_roles:
        return AuthorizationDecision.DENY, "REQUIRED_ROLE_NOT_ASSIGNED"
    return AuthorizationDecision.ALLOW, "REQUIRED_ROLE_ASSIGNED"
