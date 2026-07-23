"""Receipt construction and verification for Security Core v0.1."""

from __future__ import annotations

from typing import Any

from .models import SecurityReceipt
from .repositories import SecurityReceiptRepository


class ReceiptService:
    def __init__(self, repository: SecurityReceiptRepository) -> None:
        self.repository = repository

    def issue(
        self,
        *,
        operation: str,
        organization_id: str,
        identity_id: str | None,
        assignment_type: str | None,
        requested_value: Any,
        outcome: str,
        status: str,
        reason_code: str,
        normalized_input: dict[str, Any],
        prior_state: dict[str, Any],
        resulting_state: dict[str, Any],
        result: dict[str, Any],
    ) -> SecurityReceipt:
        receipts = self.repository.list_all()
        receipt = SecurityReceipt.create(
            sequence=len(receipts) + 1,
            operation=operation,
            organization_id=organization_id,
            identity_id=identity_id,
            assignment_type=assignment_type,
            requested_value=requested_value,
            outcome=outcome,
            status=status,
            reason_code=reason_code,
            normalized_input=normalized_input,
            previous_hash=receipts[-1].receipt_hash if receipts else "",
            prior_state=prior_state,
            resulting_state=resulting_state,
            result={**result, "normalized_input": normalized_input},
        )
        self.repository.append(receipt)
        return receipt

    @staticmethod
    def verify_receipt(receipt: SecurityReceipt) -> bool:
        return receipt.verify()

    def verify_chain(
        self,
        receipts: list[SecurityReceipt] | None = None,
    ) -> bool:
        evidence = receipts if receipts is not None else self.repository.list_all()
        previous_hash = ""
        for sequence, receipt in enumerate(evidence, start=1):
            if receipt.sequence != sequence:
                return False
            if receipt.receipt_id != f"SCR-{sequence:06d}":
                return False
            if receipt.previous_hash != previous_hash:
                return False
            if not receipt.verify():
                return False
            previous_hash = receipt.receipt_hash
        return True
