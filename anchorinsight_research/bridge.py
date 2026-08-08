"""AIN-303.2 live acquisition -> AIN-302 source-admission orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .handoff import EvidenceHandoffResult, EvidenceHandoffService
from .models import CandidateSource, ResearchRequest
from .service import ResearchAcquisitionResult, ResearchPlanningAcquisitionService


@dataclass(frozen=True)
class LiveEvidenceBridgeResult:
    """Outcome of one bounded live acquisition and AIN-302 handoff run."""

    acquisition: ResearchAcquisitionResult
    handoffs: tuple[EvidenceHandoffResult, ...]

    @property
    def sources_admitted_to_ain302(self) -> int:
        return len(self.handoffs)

    @property
    def complete(self) -> bool:
        return (
            self.acquisition.documents_acquired > 0
            and self.sources_admitted_to_ain302 == self.acquisition.documents_acquired
        )

    def to_dict(self) -> dict:
        return {
            "acquisition": self.acquisition.to_dict(),
            "handoffs": [
                {
                    "source": result.source.to_dict(),
                    "receipt": result.receipt.to_dict(),
                }
                for result in self.handoffs
            ],
            "summary": {
                "documents_acquired": self.acquisition.documents_acquired,
                "sources_admitted_to_ain302": self.sources_admitted_to_ain302,
                "complete": self.complete,
            },
        }


class LiveEvidenceBridgeService:
    """Run AIN-303 live acquisition and hand retrieved sources to AIN-302.

    This orchestrator stops at AIN-302 source admission. It deliberately does
    not create findings, approve findings, or commit authoritative evidence.
    """

    VERSION = "303.2"

    def __init__(
        self,
        *,
        research_service: ResearchPlanningAcquisitionService,
        handoff_service: EvidenceHandoffService,
    ) -> None:
        self.research_service = research_service
        self.handoff_service = handoff_service

    def execute(
        self,
        *,
        request: ResearchRequest,
        workspace_id: str,
        organization_id: str,
        provider: Callable[[CandidateSource], tuple[bytes, str]],
        acquisition_method: str = "AIN-303.2 Live Provider",
        pipeline_id: str | None = None,
    ) -> LiveEvidenceBridgeResult:
        plan = self.research_service.create_plan(request, pipeline_id=pipeline_id)
        candidates = self.research_service.discover_sources(plan)
        providers = {source.source_id: provider for source in candidates}

        acquisition = self.research_service.execute_with_providers(
            request=request,
            providers=providers,
            acquisition_method=acquisition_method,
            pipeline_id=pipeline_id,
        )

        sources_by_id = {source.source_id: source for source in acquisition.candidate_sources}
        receipts_by_document = {
            receipt.document_id: receipt
            for receipt in acquisition.acquisition_receipts
            if receipt.document_id is not None
        }

        handoffs: list[EvidenceHandoffResult] = []
        for document in acquisition.acquired_documents:
            source = sources_by_id[document.source_id]
            receipt = receipts_by_document.get(document.document_id)
            if receipt is None:
                continue
            handoffs.append(
                self.handoff_service.handoff(
                    source=source,
                    document=document,
                    acquisition_receipt=receipt,
                    workspace_id=workspace_id,
                    organization_id=organization_id,
                )
            )

        return LiveEvidenceBridgeResult(
            acquisition=acquisition,
            handoffs=tuple(handoffs),
        )
