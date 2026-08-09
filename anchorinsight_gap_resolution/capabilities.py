"""Machine-readable current capability registries consumed by AIN-304."""
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
from typing import Any


@dataclass(frozen=True, slots=True)
class CurrentCapability:
    capability_id: str
    name: str
    product_surface: str
    claim: str
    status: str
    admissible_for_osf: bool
    proof_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityRegistry:
    registry_id: str
    name: str
    version: str
    admissibility_rule: str
    governing_rule: str
    platform_rule: str
    inadmissible_categories: tuple[str, ...]
    capabilities: tuple[CurrentCapability, ...]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "CapabilityRegistry":
        capabilities = tuple(
            CurrentCapability(
                capability_id=item["capability_id"],
                name=item["name"],
                product_surface=item["product_surface"],
                claim=item["claim"],
                status=item["status"],
                admissible_for_osf=bool(item["admissible_for_osf"]),
                proof_refs=tuple(item.get("proof_refs", ())),
            )
            for item in payload["capabilities"]
        )
        registry = cls(
            registry_id=payload["registry_id"],
            name=payload["name"],
            version=payload["version"],
            admissibility_rule=payload["admissibility_rule"],
            governing_rule=payload["governing_rule"],
            platform_rule=payload["platform_rule"],
            inadmissible_categories=tuple(payload["inadmissible_categories"]),
            capabilities=capabilities,
        )
        registry.validate()
        return registry

    def validate(self) -> None:
        ids = [item.capability_id for item in self.capabilities]
        expected = [f"CAP-{number:03d}" for number in range(1, 11)]
        if ids != expected:
            raise ValueError(f"{self.registry_id} must define CAP-001 through CAP-010 in order")
        if len(set(ids)) != len(ids):
            raise ValueError(f"{self.registry_id} capability identifiers must be unique")
        if not all(item.admissible_for_osf for item in self.capabilities):
            raise ValueError(f"{self.registry_id} V1 capabilities must all be OSF-admissible")
        if any(not item.claim.strip() for item in self.capabilities):
            raise ValueError(f"{self.registry_id} capabilities must define bounded claims")
        if any(not item.proof_refs for item in self.capabilities):
            raise ValueError(f"{self.registry_id} capabilities must carry proof references")

    @property
    def admissible_capabilities(self) -> tuple[CurrentCapability, ...]:
        return tuple(item for item in self.capabilities if item.admissible_for_osf)

    @property
    def admissible_capability_ids(self) -> tuple[str, ...]:
        return tuple(item.capability_id for item in self.admissible_capabilities)


def load_sls_cap_001() -> CapabilityRegistry:
    resource = files("anchorinsight_gap_resolution").joinpath("capabilities/sls_cap_001.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return CapabilityRegistry.from_payload(payload)
