"""Non-production Security Core interface adapter for the demonstration."""

from pipelines.customer_onboarding.models import canonical_hash


class DemonstrationSecurityCore:
    """
    Deterministic test adapter for the future Security Core public API.

    This adapter issues integration receipts only. It does not authenticate,
    authorize, evaluate policy, manage credentials, or provide tenant
    isolation and must not be used as a production Security Core.
    """

    def __init__(self, operational: bool = True) -> None:
        self.operational = operational

    def health(self) -> dict[str, object]:
        return {
            "service": "Demonstration Security Core Adapter",
            "operational": self.operational,
            "production": False,
        }

    def assign_identity_and_roles(
        self,
        *,
        organization_id: str,
        identity_id: str,
        roles: tuple[str, ...],
        idempotency_key: str,
    ) -> dict[str, object]:
        return self._receipt(
            organization_id=organization_id,
            assignment_type="identity_roles",
            assignment={
                "identity_id": identity_id,
                "roles": roles,
            },
            idempotency_key=idempotency_key,
        )

    def assign_policy(
        self,
        *,
        organization_id: str,
        policy_id: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        return self._receipt(
            organization_id=organization_id,
            assignment_type="security_policy",
            assignment={"policy_id": policy_id},
            idempotency_key=idempotency_key,
        )

    def _receipt(
        self,
        *,
        organization_id: str,
        assignment_type: str,
        assignment: dict[str, object],
        idempotency_key: str,
    ) -> dict[str, object]:
        if not self.operational:
            raise RuntimeError(
                "Demonstration Security Core is unavailable."
            )
        evidence = {
            "organization_id": organization_id,
            "assignment_type": assignment_type,
            "assignment": assignment,
            "idempotency_key": idempotency_key,
        }
        return {
            **evidence,
            "receipt_id": (
                "SEC-" + canonical_hash(evidence)[:16].upper()
            ),
            "status": "Assigned",
            "production": False,
        }
