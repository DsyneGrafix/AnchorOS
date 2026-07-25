"""Repository ports and in-memory adapters for Security Core v0.1."""

from __future__ import annotations

from copy import deepcopy
from typing import Protocol

from .models import (
    IdentityRecord,
    PolicyAssignmentRecord,
    RoleAssignmentRecord,
    SecurityReceipt,
)


class IdentityRepository(Protocol):
    def get(self, organization_id: str, identity_id: str) -> IdentityRecord | None: ...
    def save(self, record: IdentityRecord) -> None: ...


class RoleAssignmentRepository(Protocol):
    def get(self, organization_id: str, identity_id: str) -> RoleAssignmentRecord | None: ...
    def save(self, record: RoleAssignmentRecord) -> None: ...


class PolicyAssignmentRepository(Protocol):
    def get(self, organization_id: str) -> PolicyAssignmentRecord | None: ...
    def save(self, record: PolicyAssignmentRecord) -> None: ...


class SecurityReceiptRepository(Protocol):
    def append(self, receipt: SecurityReceipt) -> None: ...
    def get(self, receipt_id: str) -> SecurityReceipt | None: ...
    def list_all(self) -> list[SecurityReceipt]: ...


class IdempotencyRepository(Protocol):
    def get(self, key: str) -> tuple[str, str] | None: ...
    def save(self, key: str, input_hash: str, receipt_id: str) -> None: ...


class InMemoryIdentityRepository:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], IdentityRecord] = {}

    def get(self, organization_id: str, identity_id: str) -> IdentityRecord | None:
        return self._records.get((organization_id, identity_id))

    def save(self, record: IdentityRecord) -> None:
        self._records[(record.organization_id, record.identity_id)] = record


class InMemoryRoleAssignmentRepository:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], RoleAssignmentRecord] = {}

    def get(self, organization_id: str, identity_id: str) -> RoleAssignmentRecord | None:
        return self._records.get((organization_id, identity_id))

    def save(self, record: RoleAssignmentRecord) -> None:
        self._records[(record.organization_id, record.identity_id)] = record


class InMemoryPolicyAssignmentRepository:
    def __init__(self) -> None:
        self._records: dict[str, PolicyAssignmentRecord] = {}

    def get(self, organization_id: str) -> PolicyAssignmentRecord | None:
        return self._records.get(organization_id)

    def save(self, record: PolicyAssignmentRecord) -> None:
        self._records[record.organization_id] = record


class InMemorySecurityReceiptRepository:
    def __init__(self) -> None:
        self._records: list[SecurityReceipt] = []

    def append(self, receipt: SecurityReceipt) -> None:
        self._records.append(deepcopy(receipt))

    def get(self, receipt_id: str) -> SecurityReceipt | None:
        for receipt in self._records:
            if receipt.receipt_id == receipt_id:
                return deepcopy(receipt)
        return None

    def list_all(self) -> list[SecurityReceipt]:
        return deepcopy(self._records)


class InMemoryIdempotencyRepository:
    def __init__(self) -> None:
        self._records: dict[str, tuple[str, str]] = {}

    def get(self, key: str) -> tuple[str, str] | None:
        return self._records.get(key)

    def save(self, key: str, input_hash: str, receipt_id: str) -> None:
        self._records[key] = (input_hash, receipt_id)


class SecurityRepositories:
    """Dependency bundle; adapters can be replaced without engine changes."""

    def __init__(
        self,
        *,
        identities: IdentityRepository | None = None,
        roles: RoleAssignmentRepository | None = None,
        policies: PolicyAssignmentRepository | None = None,
        receipts: SecurityReceiptRepository | None = None,
        idempotency: IdempotencyRepository | None = None,
    ) -> None:
        self.identities = identities or InMemoryIdentityRepository()
        self.roles = roles or InMemoryRoleAssignmentRepository()
        self.policies = policies or InMemoryPolicyAssignmentRepository()
        self.receipts = receipts or InMemorySecurityReceiptRepository()
        self.idempotency = idempotency or InMemoryIdempotencyRepository()
