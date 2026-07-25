"""Normative stage definitions for Customer Onboarding Pipeline v1."""

from dataclasses import dataclass

from .models import CustomerState


@dataclass(frozen=True, slots=True)
class StageDefinition:
    """Purpose and transition contract for one pipeline stage."""

    code: str
    name: str
    purpose: str
    entry_state: CustomerState
    exit_state: CustomerState
    entry_criteria: tuple[str, ...]
    exit_criteria: tuple[str, ...]


CUSTOMER_PIPELINE_STAGES: tuple[StageDefinition, ...] = (
    StageDefinition(
        code="CP-001",
        name="Customer Registration",
        purpose="Accept a bounded organization onboarding request.",
        entry_state=CustomerState.PENDING,
        exit_state=CustomerState.REGISTERED,
        entry_criteria=(
            "Unique onboarding identifier is supplied.",
            "Organization name and canonical slug are supplied.",
        ),
        exit_criteria=(
            "Registration evidence is recorded.",
            "Request is eligible for organization provisioning.",
        ),
    ),
    StageDefinition(
        code="CP-002",
        name="Organization Provisioning",
        purpose="Create a deterministic AnchorOS organization identity.",
        entry_state=CustomerState.REGISTERED,
        exit_state=CustomerState.PROVISIONED,
        entry_criteria=("Registration evidence is valid.",),
        exit_criteria=(
            "Stable organization identifier is generated.",
            "Provisioning evidence is recorded.",
        ),
    ),
    StageDefinition(
        code="CP-003",
        name="Identity & Role Assignment",
        purpose=(
            "Request identity and role assignment through the public "
            "Security Core interface."
        ),
        entry_state=CustomerState.PROVISIONED,
        exit_state=CustomerState.IDENTITY_ASSIGNED,
        entry_criteria=(
            "Organization is provisioned.",
            "Security Core is operational.",
            "Primary identity and requested roles are supplied.",
        ),
        exit_criteria=(
            "Security Core returns a verifiable assignment receipt.",
        ),
    ),
    StageDefinition(
        code="CP-004",
        name="License Assignment",
        purpose=(
            "Assign a configured platform license entitlement without "
            "billing or payment processing."
        ),
        entry_state=CustomerState.IDENTITY_ASSIGNED,
        exit_state=CustomerState.LICENSE_ASSIGNED,
        entry_criteria=(
            "Identity assignment is complete.",
            "Requested license exists in Configuration.",
        ),
        exit_criteria=("License assignment evidence is recorded.",),
    ),
    StageDefinition(
        code="CP-005",
        name="Framework Enablement",
        purpose="Enable requested, registered, healthy AnchorOS frameworks.",
        entry_state=CustomerState.LICENSE_ASSIGNED,
        exit_state=CustomerState.FRAMEWORKS_ENABLED,
        entry_criteria=(
            "License assignment is complete.",
            "Requested frameworks are present in Manifest and Health.",
        ),
        exit_criteria=("Framework enablement evidence is recorded.",),
    ),
    StageDefinition(
        code="CP-006",
        name="Security Policy Assignment",
        purpose=(
            "Request organization policy assignment through the public "
            "Security Core interface."
        ),
        entry_state=CustomerState.FRAMEWORKS_ENABLED,
        exit_state=CustomerState.SECURITY_POLICY_ASSIGNED,
        entry_criteria=(
            "Framework enablement is complete.",
            "Security Core is operational.",
            "A security policy identifier is supplied.",
        ),
        exit_criteria=(
            "Security Core returns a verifiable policy receipt.",
        ),
    ),
    StageDefinition(
        code="CP-007",
        name="Deployment Preparation",
        purpose="Build a deterministic deployment-readiness plan.",
        entry_state=CustomerState.SECURITY_POLICY_ASSIGNED,
        exit_state=CustomerState.DEPLOYMENT_PREPARED,
        entry_criteria=(
            "Security policy assignment is complete.",
            "Deployment environment is allowed by Configuration.",
        ),
        exit_criteria=(
            "Deployment plan is bound to the Platform Manifest.",
            "No external deployment is performed.",
        ),
    ),
    StageDefinition(
        code="CP-008",
        name="Validation",
        purpose="Verify onboarding evidence and platform readiness.",
        entry_state=CustomerState.DEPLOYMENT_PREPARED,
        exit_state=CustomerState.VALIDATED,
        entry_criteria=(
            "All prior stage evidence is present.",
            "Required Platform Services are running.",
            "The existing Boot Pipeline has passed every stage.",
        ),
        exit_criteria=(
            "Validation receipt is generated.",
            "Transition chain is internally verifiable.",
        ),
    ),
    StageDefinition(
        code="CP-009",
        name="Operational",
        purpose="Declare the provisioned organization operational.",
        entry_state=CustomerState.VALIDATED,
        exit_state=CustomerState.OPERATIONAL,
        entry_criteria=("Validation receipt reports PASS.",),
        exit_criteria=(
            "Organization is explicitly marked Operational.",
            "Final audit and replay evidence is available.",
        ),
    ),
)


STAGES_BY_CODE = {
    stage.code: stage
    for stage in CUSTOMER_PIPELINE_STAGES
}
