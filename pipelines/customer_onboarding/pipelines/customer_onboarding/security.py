"""Public Security Core consumer contract for customer onboarding."""

from typing import Protocol


class SecurityCoreGateway(Protocol):
    """
    Narrow public interface consumed by CP-003 and CP-006.

    Implementations belong to the Security Core integration layer. The
    Customer Onboarding Pipeline does not authenticate identities, authorize
    roles, evaluate policies, or store credentials.
    """

    def health(self) -> dict[str, object]:
        """Return Security Core availability for fail-closed checks."""

    def assign_identity_and_roles(
        self,
        *,
        organization_id: str,
        identity_id: str,
        roles: tuple[str, ...],
        idempotency_key: str,
    ) -> dict[str, object]:
        """Request identity and role assignment from Security Core."""

    def assign_policy(
        self,
        *,
        organization_id: str,
        policy_id: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        """Request security-policy assignment from Security Core."""
