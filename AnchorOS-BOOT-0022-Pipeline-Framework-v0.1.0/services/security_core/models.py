"""State, record, receipt, and replay models for Security Core v0.1."""

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


class SecurityState(Enum):
    UNINITIALIZED = "Uninitialized"
    INITIALIZING = "Initializing"
    OPERATIONAL = "Operational"
    DEGRADED = "Degraded"
    FAILED = "Failed"
    STOPPED = "Stopped"


class RecordStatus(Enum):
    REGISTERED = "Registered"
    ASSIGNED = "Assigned"


class AuthorizationDecision(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True, slots=True)
class IdentityRecord:
    organization_id: str
    identity_id: str
    status: str = RecordStatus.REGISTERED.value

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RoleAssignmentRecord:
    organization_id: str
    identity_id: str
    roles: tuple[str, ...]
    status: str = RecordStatus.ASSIGNED.value

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PolicyAssignmentRecord:
    organization_id: str
    policy_id: str
    status: str = RecordStatus.ASSIGNED.value

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class SecurityReceipt:
    """Hash-linked evidence for one bounded security operation."""

    receipt_id: str
    sequence: int
    operation: str
    organization_id: str
    identity_id: str | None
    assignment_type: str | None
    requested_value: Any
    outcome: str
    status: str
    reason_code: str
    input_hash: str
    previous_hash: str
    prior_state: dict[str, Any]
    prior_state_hash: str
    resulting_state: dict[str, Any]
    resulting_state_hash: str
    result: dict[str, Any]
    receipt_hash: str

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        operation: str,
        organization_id: str,
        identity_id: str | None,
        assignment_type: str | None,
        requested_value: Any,
        outcome: str,
        status: str,
        reason_code: str,
        normalized_input: dict[str, Any],
        previous_hash: str,
        prior_state: dict[str, Any],
        resulting_state: dict[str, Any],
        result: dict[str, Any],
    ) -> SecurityReceipt:
        input_hash = canonical_hash(normalized_input)
        prior_state_hash = canonical_hash(prior_state)
        resulting_state_hash = canonical_hash(resulting_state)
        content = {
            "receipt_id": f"SCR-{sequence:06d}",
            "sequence": sequence,
            "operation": operation,
            "organization_id": organization_id,
            "identity_id": identity_id,
            "assignment_type": assignment_type,
            "requested_value": requested_value,
            "outcome": outcome,
            "status": status,
            "reason_code": reason_code,
            "input_hash": input_hash,
            "previous_hash": previous_hash,
            "prior_state": prior_state,
            "prior_state_hash": prior_state_hash,
            "resulting_state": resulting_state,
            "resulting_state_hash": resulting_state_hash,
            "result": result,
        }
        return cls(**content, receipt_hash=canonical_hash(content))

    def content(self) -> dict[str, object]:
        return {
            "receipt_id": self.receipt_id,
            "sequence": self.sequence,
            "operation": self.operation,
            "organization_id": self.organization_id,
            "identity_id": self.identity_id,
            "assignment_type": self.assignment_type,
            "requested_value": self.requested_value,
            "outcome": self.outcome,
            "status": self.status,
            "reason_code": self.reason_code,
            "input_hash": self.input_hash,
            "previous_hash": self.previous_hash,
            "prior_state": self.prior_state,
            "prior_state_hash": self.prior_state_hash,
            "resulting_state": self.resulting_state,
            "resulting_state_hash": self.resulting_state_hash,
            "result": self.result,
        }

    def verify(self) -> bool:
        return (
            self.input_hash == canonical_hash(self.normalized_input())
            and self.prior_state_hash == canonical_hash(self.prior_state)
            and self.resulting_state_hash
            == canonical_hash(self.resulting_state)
            and self.receipt_hash == canonical_hash(self.content())
        )

    def normalized_input(self) -> dict[str, Any]:
        value = self.result.get("normalized_input")
        return value if isinstance(value, dict) else {}

    def to_dict(self) -> dict[str, object]:
        return {**self.content(), "receipt_hash": self.receipt_hash}


@dataclass(frozen=True, slots=True)
class ReplayResult:
    receipt_id: str
    verified: bool
    operation: str
    expected_hash: str
    actual_hash: str
    reason: str
    replay_receipt_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
