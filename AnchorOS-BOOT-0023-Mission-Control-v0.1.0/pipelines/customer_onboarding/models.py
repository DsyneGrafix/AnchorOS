"""State and evidence models for the Customer Onboarding Pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any


def canonical_hash(value: object) -> str:
    """Return a stable SHA-256 hash for JSON-compatible evidence."""

    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class CustomerState(Enum):
    """Deterministic Customer Onboarding Pipeline states."""

    PENDING = "Pending"
    REGISTERED = "Registered"
    PROVISIONED = "Provisioned"
    IDENTITY_ASSIGNED = "IdentityAssigned"
    LICENSE_ASSIGNED = "LicenseAssigned"
    FRAMEWORKS_ENABLED = "FrameworksEnabled"
    SECURITY_POLICY_ASSIGNED = "SecurityPolicyAssigned"
    DEPLOYMENT_PREPARED = "DeploymentPrepared"
    VALIDATED = "Validated"
    OPERATIONAL = "Operational"
    FAILED = "Failed"


@dataclass(frozen=True, slots=True)
class OnboardingRequest:
    """Bounded input contract for customer onboarding only."""

    onboarding_id: str
    organization_name: str
    organization_slug: str
    primary_identity_id: str
    requested_roles: tuple[str, ...]
    license_id: str
    frameworks: tuple[str, ...]
    security_policy_id: str
    deployment_environment: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class TransitionRecord:
    """Hash-linked evidence for one stage transition."""

    sequence: int
    stage_code: str
    stage_name: str
    from_state: str
    to_state: str
    outcome: str
    input_hash: str
    previous_hash: str
    details: dict[str, Any]
    transition_hash: str

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        stage_code: str,
        stage_name: str,
        from_state: CustomerState,
        to_state: CustomerState,
        outcome: str,
        input_hash: str,
        previous_hash: str,
        details: dict[str, Any],
    ) -> TransitionRecord:
        content = {
            "sequence": sequence,
            "stage_code": stage_code,
            "stage_name": stage_name,
            "from_state": from_state.value,
            "to_state": to_state.value,
            "outcome": outcome,
            "input_hash": input_hash,
            "previous_hash": previous_hash,
            "details": details,
        }
        return cls(
            **content,
            transition_hash=canonical_hash(content),
        )

    def verify_hash(self) -> bool:
        content = {
            "sequence": self.sequence,
            "stage_code": self.stage_code,
            "stage_name": self.stage_name,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "outcome": self.outcome,
            "input_hash": self.input_hash,
            "previous_hash": self.previous_hash,
            "details": self.details,
        }
        return self.transition_hash == canonical_hash(content)

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "stage_code": self.stage_code,
            "stage_name": self.stage_name,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "outcome": self.outcome,
            "input_hash": self.input_hash,
            "previous_hash": self.previous_hash,
            "details": self.details.copy(),
            "transition_hash": self.transition_hash,
        }


@dataclass(slots=True)
class CustomerRecord:
    """Aggregate state produced by the onboarding lifecycle."""

    request: OnboardingRequest
    state: CustomerState = CustomerState.PENDING
    last_successful_state: CustomerState = CustomerState.PENDING
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    transitions: list[TransitionRecord] = field(default_factory=list)
    failed_stage: str | None = None
    failure_reason: str | None = None

    @property
    def onboarding_id(self) -> str:
        return self.request.onboarding_id

    @property
    def final_hash(self) -> str:
        if not self.transitions:
            return ""
        return self.transitions[-1].transition_hash

    def input_snapshot(self) -> dict[str, object]:
        return {
            "request": self.request.to_dict(),
            "state": self.state.value,
            "last_successful_state": self.last_successful_state.value,
            "artifacts": self.artifacts,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "onboarding_id": self.onboarding_id,
            "state": self.state.value,
            "last_successful_state": self.last_successful_state.value,
            "failed_stage": self.failed_stage,
            "failure_reason": self.failure_reason,
            "final_hash": self.final_hash,
            "request": self.request.to_dict(),
            "artifacts": self.artifacts,
            "transitions": [
                transition.to_dict()
                for transition in self.transitions
            ],
        }


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """Result of deterministic lifecycle replay."""

    onboarding_id: str
    verified: bool
    expected_hash: str
    actual_hash: str
    expected_transitions: int
    actual_transitions: int
    message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
