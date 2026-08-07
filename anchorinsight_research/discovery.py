"""
AIN-303.1 Deterministic Source Discovery.

Generates approved CandidateSource objects from a ResearchPlan using a
bounded source catalog.

This module SHALL NOT:
- access the web
- call AI models
- acquire source content
- create findings
- admit evidence
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import CandidateSource, ResearchPlan
from .storage import ResearchArtifactStore


class SourceDiscoveryError(Exception):
    """Base exception for source-discovery failures."""


class DiscoveryValidationError(SourceDiscoveryError):
    """Raised when discovery inputs are invalid."""


@dataclass(frozen=True)
class SourceCatalogEntry:
    """One approved source available to deterministic discovery."""

    title: str
    url: str
    organization: str
    source_type: str
    authority_score: float
    categories: tuple[str, ...]
    discovery_reason: str
    active: bool = True


class SourceDiscoveryService:
    """
    Discover approved candidate sources for a ResearchPlan.

    Discovery is deterministic:
    - source catalog order is stable
    - ranking rules are explicit
    - duplicate suppression uses source fingerprints
    """

    def __init__(
        self,
        *,
        store: ResearchArtifactStore,
        catalog: Iterable[SourceCatalogEntry] | None = None,
    ) -> None:
        self.store = store
        self.catalog = tuple(catalog or self.default_catalog())

    @staticmethod
    def default_catalog() -> tuple[SourceCatalogEntry, ...]:
        """Return the initial bounded CPS Energy proof catalog."""
        return (
            SourceCatalogEntry(
                title="CPS Energy Official Website",
                url="https://www.cpsenergy.com",
                organization="CPS Energy",
                source_type="Corporate",
                authority_score=1.00,
                categories=(
                    "Communications",
                    "Energy",
                    "Infrastructure",
                    "Technology",
                ),
                discovery_reason="Official organization source",
            ),
            SourceCatalogEntry(
                title="CPS Energy Newsroom",
                url="https://newsroom.cpsenergy.com",
                organization="CPS Energy",
                source_type="Corporate",
                authority_score=0.98,
                categories=(
                    "Energy",
                    "Infrastructure",
                    "Technology",
                ),
                discovery_reason="Official announcements and modernization news",
            ),
            SourceCatalogEntry(
                title="Public Utility Commission of Texas",
                url="https://www.puc.texas.gov",
                organization="CPS Energy",
                source_type="Regulatory",
                authority_score=0.96,
                categories=(
                    "Energy",
                    "Infrastructure",
                ),
                discovery_reason="Relevant regulatory authority",
            ),
            SourceCatalogEntry(
                title="City of San Antonio",
                url="https://www.sanantonio.gov",
                organization="CPS Energy",
                source_type="Government",
                authority_score=0.94,
                categories=(
                    "Infrastructure",
                    "Technology",
                ),
                discovery_reason="Municipal owner and government source",
            ),
            SourceCatalogEntry(
                title="ERCOT",
                url="https://www.ercot.com",
                organization="CPS Energy",
                source_type="Industry",
                authority_score=0.92,
                categories=(
                    "Energy",
                    "Grid",
                    "Infrastructure",
                ),
                discovery_reason="Texas grid operator source",
            ),
        )

    def discover(
        self,
        plan: ResearchPlan,
    ) -> tuple[CandidateSource, ...]:
        """
        Discover, rank, suppress duplicates, persist, and return candidates.
        """
        self._validate_plan(plan)

        matching_entries = [
            entry
            for entry in self.catalog
            if self._matches(plan, entry)
        ]

        ranked_entries = sorted(
            matching_entries,
            key=lambda entry: (
                -entry.authority_score,
                entry.source_type,
                entry.title,
                entry.url,
            ),
        )

        discovered: list[CandidateSource] = []

        for entry in ranked_entries[: plan.maximum_sources]:
            candidate = CandidateSource(
                plan_id=plan.plan_id,
                title=entry.title,
                url=entry.url,
                organization=entry.organization,
                source_type=entry.source_type,
                authority_score=entry.authority_score,
                discovery_reason=entry.discovery_reason,
            )

            existing = self.store.find_candidate_by_fingerprint(
                candidate.source_fingerprint
            )

            if existing is not None:
                continue

            self.store.save_candidate_source(candidate)
            discovered.append(candidate)

        return tuple(discovered)

    def rank(
        self,
        sources: Iterable[CandidateSource],
    ) -> tuple[CandidateSource, ...]:
        """Return candidate sources in deterministic priority order."""
        return tuple(
            sorted(
                sources,
                key=lambda source: (
                    -source.authority_score,
                    source.source_type,
                    source.title,
                    source.normalized_url,
                ),
            )
        )

    def _validate_plan(self, plan: ResearchPlan) -> None:
        if not plan.plan_id.strip():
            raise DiscoveryValidationError("plan_id is required")

        if not plan.organization.strip():
            raise DiscoveryValidationError("organization is required")

        if plan.maximum_sources < 1:
            raise DiscoveryValidationError(
                "maximum_sources must be at least 1"
            )

        if not plan.research_categories:
            raise DiscoveryValidationError(
                "at least one research category is required"
            )

    def _matches(
        self,
        plan: ResearchPlan,
        entry: SourceCatalogEntry,
    ) -> bool:
        if not entry.active:
            return False

        if (
            entry.organization.casefold()
            != plan.organization.casefold()
        ):
            return False

        allowed_source_types = {
            source_type.casefold()
            for source_type in plan.priority_sources
        }

        if entry.source_type.casefold() not in allowed_source_types:
            return False

        plan_categories = {
            category.casefold()
            for category in plan.research_categories
        }
        entry_categories = {
            category.casefold()
            for category in entry.categories
        }

        return bool(plan_categories & entry_categories)
