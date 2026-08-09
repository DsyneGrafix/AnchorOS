"""Machine-readable evidence contracts consumed by AIN-304."""
from __future__ import annotations

from dataclasses import dataclass
import json
from importlib.resources import files
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenceContractDimension:
    dimension_id: str
    name: str
    weight: int
    required_determination: str
    collection_objective: str
    completion_condition: str
    preferred_source_class: str
    priority: int


@dataclass(frozen=True, slots=True)
class EvidenceContract:
    contract_id: str
    name: str
    version: str
    evidence_states: tuple[str, ...]
    unknown_rule: str
    contrary_evidence_required: bool
    dimensions: tuple[EvidenceContractDimension, ...]
    approval_conditions: tuple[str, ...]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "EvidenceContract":
        dimensions = tuple(EvidenceContractDimension(**item) for item in payload["dimensions"])
        contract = cls(
            contract_id=payload["contract_id"],
            name=payload["name"],
            version=payload["version"],
            evidence_states=tuple(payload["evidence_states"]),
            unknown_rule=payload["unknown_rule"],
            contrary_evidence_required=bool(payload["contrary_evidence_required"]),
            dimensions=dimensions,
            approval_conditions=tuple(payload["approval_conditions"]),
        )
        contract.validate()
        return contract

    def validate(self) -> None:
        if sum(item.weight for item in self.dimensions) != 100:
            raise ValueError(f"{self.contract_id} dimension weights must total 100")
        if len(self.dimensions) != 5:
            raise ValueError(f"{self.contract_id} must define five dimensions")
        if "UNKNOWN" not in self.evidence_states or "NOT_SUPPORTED" not in self.evidence_states:
            raise ValueError(f"{self.contract_id} must preserve UNKNOWN and NOT_SUPPORTED separately")
        if not self.contrary_evidence_required:
            raise ValueError(f"{self.contract_id} must require consideration of contrary evidence")
        if len(set(item.dimension_id for item in self.dimensions)) != len(self.dimensions):
            raise ValueError(f"{self.contract_id} dimension identifiers must be unique")


def load_osf_ec_001() -> EvidenceContract:
    resource = files("anchorinsight_gap_resolution").joinpath("contracts/osf_ec_001.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return EvidenceContract.from_payload(payload)
