"""AIN-304 -> AIN-303.2 Collection Requirement adapter.

Transforms one bounded AIN-304 CollectionRequirement into the existing
AIN-303.1 ResearchRequest model consumed by LiveEvidenceBridgeService.

The adapter does not discover sources, select URLs, acquire content, create
findings, approve evidence, score Strategic Fit, or infer capability matches.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from anchorinsight_research.models import ResearchRequest

from .service import CollectionRequirement


class CollectionRequirementAdapterError(ValueError):
    """Raised when a collection requirement cannot cross into AIN-303.2."""


@dataclass(frozen=True, slots=True)
class ResearchRequestHandoff:
    """Traceable handoff from one CR-* requirement to one ResearchRequest."""

    collection_requirement_id: str
    contract_id: str
    obligation_id: str
    capability_registry_id: str | None
    allowed_capability_ids: tuple[str, ...]
    research_request: ResearchRequest

    def to_dict(self) -> dict:
        return {
            "collection_requirement_id": self.collection_requirement_id,
            "contract_id": self.contract_id,
            "obligation_id": self.obligation_id,
            "capability_registry_id": self.capability_registry_id,
            "allowed_capability_ids": list(self.allowed_capability_ids),
            "research_request": self.research_request.to_dict(),
        }


class CollectionRequirementResearchAdapter:
    """Build bounded AIN-303.2 ResearchRequests from AIN-304 requirements."""

    VERSION = "304.4"
    SUPPORTED_HANDOFF = "AIN-303.2"

    def adapt(
        self,
        *,
        requirement: CollectionRequirement,
        workspace_id: str,
        organization_identifier: str,
        organization_name: str,
    ) -> ResearchRequestHandoff:
        self._validate(requirement)

        allowed = tuple(requirement.allowed_capability_ids)
        capability_clause = (
            f" Candidate problem/capability intersections are limited to "
            f"{requirement.capability_registry_id}: {', '.join(allowed)}."
            if allowed
            else ""
        )

        objective = (
            f"Resolve {requirement.contract_id} {requirement.obligation_id} for "
            f"{organization_name}. {requirement.objective}{capability_clause}"
        )

        constraints = [
            f"Collection Requirement: {requirement.requirement_id}",
            f"Evidence Contract: {requirement.contract_id}",
            f"Contract Obligation: {requirement.obligation_id}",
            "Do not infer a customer problem or need.",
            "Do not assert Strategic Fit or assign an evidence state.",
            "Do not create findings, approve evidence, or commit authoritative evidence.",
            "Preserve evidence that contradicts or weakens the proposed alignment.",
            "No qualifying evidence found is an acceptable acquisition outcome.",
            f"Preferred source class: {requirement.preferred_source_class}",
            f"Completion condition: {requirement.completion_condition}",
        ]

        if requirement.capability_registry_id:
            constraints.extend([
                f"Capability Registry: {requirement.capability_registry_id}",
                f"Allowed Capability IDs: {', '.join(allowed)}",
                "Do not use potential, future, backlog, hypothetical, or generic platform capabilities.",
                "Do not assert that any allowed capability matches the organization without governed evidence.",
            ])

        request = ResearchRequest(
            workspace_id=workspace_id,
            organization_identifier=organization_identifier,
            objective=objective,
            requested_outputs=(
                "Candidate public-source evidence bearing on the bounded contract obligation",
                "Source provenance sufficient for AIN-302 admission",
                "Contrary or disconfirming evidence when present",
            ),
            constraints=tuple(constraints),
        )

        return ResearchRequestHandoff(
            collection_requirement_id=requirement.requirement_id,
            contract_id=requirement.contract_id or "",
            obligation_id=requirement.obligation_id or "",
            capability_registry_id=requirement.capability_registry_id,
            allowed_capability_ids=allowed,
            research_request=request,
        )

    def _validate(self, requirement: CollectionRequirement) -> None:
        if requirement.handoff_target != self.SUPPORTED_HANDOFF:
            raise CollectionRequirementAdapterError(
                f"Unsupported handoff target: {requirement.handoff_target}"
            )
        if not requirement.requirement_id.startswith("CR-"):
            raise CollectionRequirementAdapterError("Collection requirement must have a CR-* identifier")
        if not requirement.contract_id or not requirement.obligation_id:
            raise CollectionRequirementAdapterError(
                "Contract-driven acquisition requires contract_id and obligation_id"
            )
        if requirement.obligation_id in {"OSF-01", "OSF-02"}:
            if requirement.contract_id != "OSF-EC-001":
                raise CollectionRequirementAdapterError(
                    "OSF-01/OSF-02 must be governed by OSF-EC-001"
                )
            if requirement.capability_registry_id != "SLS-CAP-001":
                raise CollectionRequirementAdapterError(
                    "OSF-01/OSF-02 require the SLS-CAP-001 capability boundary"
                )
            if not requirement.allowed_capability_ids:
                raise CollectionRequirementAdapterError(
                    "Capability-bounded obligations require an explicit capability whitelist"
                )
            expected = tuple(f"CAP-{index:03d}" for index in range(1, 11))
            if tuple(requirement.allowed_capability_ids) != expected:
                raise CollectionRequirementAdapterError(
                    "OSF-01/OSF-02 capability whitelist must be exactly CAP-001 through CAP-010"
                )
