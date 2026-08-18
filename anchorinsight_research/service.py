"""
AIN-303.1 Research Planning & Acquisition Application Service.

Coordinates:

ResearchRequest
    -> ResearchPlan
    -> CandidateSource discovery
    -> deterministic acquisition
    -> AcquisitionReceipt
    -> AIN-302-ready source artifacts

This service SHALL NOT perform AI reasoning, create findings, admit evidence,
calculate CCI, authorize commercial action, or generate executive reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from .acquisition import AcquisitionService
from .discovery import (
    SourceCatalogEntry,
    SourceDiscoveryService,
)
from .models import (
    AcquisitionReceipt,
    AcquiredDocument,
    CandidateSource,
    ResearchPlan,
    ResearchRequest,
)
from .planning import ResearchPlanningService
from .storage import ResearchArtifactStore


class ResearchAcquisitionServiceError(Exception):
    """Base exception for application-service failures."""


class SourceContentUnavailable(
    ResearchAcquisitionServiceError
):
    """Raised when no provider content exists for a candidate source."""


@dataclass(frozen=True)
class ResearchAcquisitionResult:
    """Outcome of one bounded AIN-303.1 execution."""

    request: ResearchRequest
    plan: ResearchPlan
    candidate_sources: tuple[CandidateSource, ...]
    acquired_documents: tuple[AcquiredDocument, ...]
    acquisition_receipts: tuple[AcquisitionReceipt, ...]

    @property
    def sources_discovered(self) -> int:
        return len(self.candidate_sources)

    @property
    def documents_acquired(self) -> int:
        return len(self.acquired_documents)

    @property
    def receipts_generated(self) -> int:
        return len(self.acquisition_receipts)

    @property
    def ready_for_ain302(self) -> bool:
        return (
            self.documents_acquired > 0
            and self.receipts_generated
            == self.sources_discovered
        )

    def to_dict(self) -> dict:
        return {
            "request": self.request.to_dict(),
            "plan": self.plan.to_dict(),
            "candidate_sources": [
                source.to_dict()
                for source in self.candidate_sources
            ],
            "acquired_documents": [
                document.metadata_dict()
                for document in self.acquired_documents
            ],
            "acquisition_receipts": [
                receipt.to_dict()
                for receipt in self.acquisition_receipts
            ],
            "summary": {
                "sources_discovered": (
                    self.sources_discovered
                ),
                "documents_acquired": (
                    self.documents_acquired
                ),
                "receipts_generated": (
                    self.receipts_generated
                ),
                "ready_for_ain302": (
                    self.ready_for_ain302
                ),
            },
        }


class ResearchPlanningAcquisitionService:
    """
    Execute the bounded AIN-303.1 research-acquisition workflow.

    Provider behavior is injected. This keeps network access and external
    systems outside the deterministic orchestration core.
    """

    VERSION = "303.1"

    def __init__(
        self,
        *,
        store: ResearchArtifactStore,
        catalog: tuple[SourceCatalogEntry, ...] | None = None,
    ) -> None:
        self.store = store

        self.planning = ResearchPlanningService()

        self.discovery = SourceDiscoveryService(
            store=store,
            catalog=catalog,
        )

        self.acquisition = AcquisitionService(
            store=store,
        )

    @classmethod
    def from_directory(
        cls,
        directory: str | Path,
        *,
        catalog: tuple[SourceCatalogEntry, ...] | None = None,
    ) -> "ResearchPlanningAcquisitionService":
        """Create the application service using filesystem storage."""
        return cls(
            store=ResearchArtifactStore(directory),
            catalog=catalog,
        )

    def create_plan(
        self,
        request: ResearchRequest,
        *,
        pipeline_id: str | None = None,
    ) -> ResearchPlan:
        """
        Create and persist a deterministic ResearchPlan.

        When the same logical request has already produced a plan, return
        the original immutable plan rather than attempting to overwrite it
        with new request, pipeline, or timestamp metadata.
        """
        proposed_plan = self.planning.create_plan(
            request,
            pipeline_id=pipeline_id,
        )

        existing_path = (
            self.store.research_plans
            / f"{proposed_plan.plan_id}.json"
        )

        if existing_path.exists():
            payload = self.store.load_plan(
                proposed_plan.plan_id
            )
            return self._plan_from_dict(payload)

        self.store.save_plan(proposed_plan)
        return proposed_plan

    def discover_sources(
        self,
        plan: ResearchPlan,
    ) -> tuple[CandidateSource, ...]:
        """Discover and persist approved candidate sources."""
        discovered = self.discovery.discover(plan)

        if discovered:
            return discovered

        return self._load_existing_candidates(
            plan.plan_id
        )

    def execute_with_providers(
        self,
        *,
        request: ResearchRequest,
        providers: Mapping[
            str,
            Callable[
                [CandidateSource],
                tuple[bytes, str],
            ],
        ],
        acquisition_method: str = "Bounded Provider",
        pipeline_id: str | None = None,
    ) -> ResearchAcquisitionResult:
        """
        Execute planning, discovery, and acquisition.

        Provider keys may be either:
        - CandidateSource.source_id
        - CandidateSource.normalized_url

        A missing provider produces a governed NOT_FOUND receipt.
        """
        plan = self.create_plan(
            request,
            pipeline_id=pipeline_id,
        )

        candidate_sources = self.discover_sources(
            plan
        )

        acquired_documents: list[
            AcquiredDocument
        ] = []

        receipts: list[AcquisitionReceipt] = []

        for source in candidate_sources:
            provider = self._resolve_provider(
                source=source,
                providers=providers,
            )

            if provider is None:
                receipt = self.acquisition.record_failure(
                    source=source,
                    parent_research_request_id=(
                        request.request_id
                    ),
                    acquisition_method=(
                        acquisition_method
                    ),
                    status=self._not_found_status(),
                    failure_reason=(
                        "No bounded content provider was "
                        "registered for this candidate source."
                    ),
                )

                receipts.append(receipt)
                continue

            document, receipt = (
                self.acquisition.acquire_with_provider(
                    source=source,
                    provider=provider,
                    acquisition_method=(
                        acquisition_method
                    ),
                    parent_research_request_id=(
                        request.request_id
                    ),
                )
            )

            if document is not None:
                acquired_documents.append(document)

            receipts.append(receipt)

        return ResearchAcquisitionResult(
            request=request,
            plan=plan,
            candidate_sources=candidate_sources,
            acquired_documents=tuple(
                acquired_documents
            ),
            acquisition_receipts=tuple(receipts),
        )

    def execute_with_content_map(
        self,
        *,
        request: ResearchRequest,
        content_by_url: Mapping[
            str,
            tuple[bytes, str],
        ],
        acquisition_method: str = "Static Content Map",
        pipeline_id: str | None = None,
    ) -> ResearchAcquisitionResult:
        """
        Execute using deterministic content indexed by normalized URL.

        This is the primary AIN-303.1 proof method. It performs no live
        web access and no AI processing.
        """
        providers: dict[
            str,
            Callable[
                [CandidateSource],
                tuple[bytes, str],
            ],
        ] = {}

        for url, content in content_by_url.items():
            normalized_url = (
                url.strip().casefold().rstrip("/")
            )

            def provider(
                source: CandidateSource,
                *,
                value: tuple[bytes, str] = content,
            ) -> tuple[bytes, str]:
                return value

            providers[normalized_url] = provider

        return self.execute_with_providers(
            request=request,
            providers=providers,
            acquisition_method=acquisition_method,
            pipeline_id=pipeline_id,
        )

    def _resolve_provider(
        self,
        *,
        source: CandidateSource,
        providers: Mapping[
            str,
            Callable[
                [CandidateSource],
                tuple[bytes, str],
            ],
        ],
    ) -> Callable[
        [CandidateSource],
        tuple[bytes, str],
    ] | None:
        return (
            providers.get(source.source_id)
            or providers.get(source.normalized_url)
        )

    def _plan_from_dict(
        self,
        payload: dict,
    ) -> ResearchPlan:
        """Reconstruct an immutable ResearchPlan from persisted JSON."""
        from datetime import datetime

        from .models import ResearchPlanStatus

        return ResearchPlan(
            plan_id=payload["plan_id"],
            request_id=payload["request_id"],
            organization_identifier=payload.get(
                "organization_identifier",
                payload["organization"],
            ),
            research_categories=tuple(
                payload["research_categories"]
            ),
            priority_sources=tuple(
                payload["priority_sources"]
            ),
            maximum_sources=int(
                payload["maximum_sources"]
            ),
            time_window=payload["time_window"],
            acquisition_strategy=payload[
                "acquisition_strategy"
            ],
            expected_outputs=tuple(
                payload["expected_outputs"]
            ),
            workspace=payload["workspace"],
            pipeline_id=payload["pipeline_id"],
            status=ResearchPlanStatus(
                payload["status"]
            ),
            created_at=datetime.fromisoformat(
                payload["created_at"]
            ),
        )

    def _load_existing_candidates(
        self,
        plan_id: str,
    ) -> tuple[CandidateSource, ...]:
        """
        Reconstruct existing candidates for idempotent service retries.

        This avoids interpreting duplicate suppression as an empty plan.
        """
        payloads = []

        for path in self.store.candidate_sources.glob(
            "*.json"
        ):
            payload = self.store._read_json(path)

            if payload.get("plan_id") == plan_id:
                payloads.append(payload)

        candidates = tuple(
            self._candidate_from_dict(payload)
            for payload in payloads
        )

        return self.discovery.rank(candidates)

    def _candidate_from_dict(
        self,
        payload: dict,
    ) -> CandidateSource:
        from datetime import datetime

        from .models import CandidateSourceStatus

        return CandidateSource(
            source_id=payload["source_id"],
            plan_id=payload["plan_id"],
            title=payload["title"],
            url=payload["url"],
            organization=payload[
                "organization"
            ],
            source_type=payload["source_type"],
            authority_score=float(
                payload["authority_score"]
            ),
            discovery_reason=payload[
                "discovery_reason"
            ],
            discovered_at=datetime.fromisoformat(
                payload["discovered_at"]
            ),
            status=CandidateSourceStatus(
                payload["status"]
            ),
        )

    @staticmethod
    def _not_found_status():
        from .models import AcquisitionStatus

        return AcquisitionStatus.NOT_FOUND
