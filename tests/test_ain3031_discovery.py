from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from anchorinsight_research.discovery import (
    DiscoveryValidationError,
    SourceCatalogEntry,
    SourceDiscoveryService,
)
from anchorinsight_research.models import (
    CandidateSource,
    ResearchRequest,
)
from anchorinsight_research.planning import (
    ResearchPlanningService,
)
from anchorinsight_research.storage import (
    ResearchArtifactStore,
)


class SourceDiscoveryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.store = ResearchArtifactStore(
            Path(self.temporary_directory.name)
        )

        self.request = ResearchRequest(
            workspace_id="SLS-DEMO-001",
            organization_identifier="CPS Energy",
            objective=(
                "Identify evidence of infrastructure modernization, "
                "communications investment, and grid technology initiatives."
            ),
            requested_outputs=(
                "Candidate Sources",
                "Acquisition Receipts",
            ),
        )

        self.plan = ResearchPlanningService().create_plan(
            self.request,
            pipeline_id="PIPELINE-001",
        )

        self.store.save_plan(self.plan)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_candidate_sources_are_discovered(self) -> None:
        service = SourceDiscoveryService(
            store=self.store
        )

        sources = service.discover(self.plan)

        self.assertEqual(len(sources), 5)
        self.assertTrue(
            all(
                isinstance(source, CandidateSource)
                for source in sources
            )
        )

    def test_sources_are_ranked_by_authority(self) -> None:
        service = SourceDiscoveryService(
            store=self.store
        )

        sources = service.discover(self.plan)
        scores = [
            source.authority_score
            for source in sources
        ]

        self.assertEqual(
            scores,
            sorted(scores, reverse=True),
        )
        self.assertEqual(
            sources[0].title,
            "CPS Energy Official Website",
        )

    def test_discovered_sources_are_persisted(self) -> None:
        service = SourceDiscoveryService(
            store=self.store
        )

        sources = service.discover(self.plan)

        persisted = list(
            self.store.candidate_sources.glob("*.json")
        )

        self.assertEqual(len(persisted), len(sources))

        for source in sources:
            loaded = self.store.load_candidate_source(
                source.source_id
            )
            self.assertEqual(
                loaded["source_fingerprint"],
                source.source_fingerprint,
            )

    def test_duplicate_discovery_is_suppressed(self) -> None:
        service = SourceDiscoveryService(
            store=self.store
        )

        first = service.discover(self.plan)
        second = service.discover(self.plan)

        self.assertEqual(len(first), 5)
        self.assertEqual(second, ())
        self.assertEqual(
            len(
                list(
                    self.store.candidate_sources.glob(
                        "*.json"
                    )
                )
            ),
            5,
        )

    def test_maximum_sources_is_enforced(self) -> None:
        limited_plan = replace(
            self.plan,
            maximum_sources=2,
        )

        service = SourceDiscoveryService(
            store=self.store
        )

        sources = service.discover(limited_plan)

        self.assertEqual(len(sources), 2)
        self.assertEqual(
            sources[0].title,
            "CPS Energy Official Website",
        )
        self.assertEqual(
            sources[1].title,
            "CPS Energy Newsroom",
        )

    def test_inactive_source_is_excluded(self) -> None:
        catalog = (
            SourceCatalogEntry(
                title="Active Source",
                url="https://example.com/active",
                organization="CPS Energy",
                source_type="Corporate",
                authority_score=0.90,
                categories=("Energy",),
                discovery_reason="Approved test source",
                active=True,
            ),
            SourceCatalogEntry(
                title="Inactive Source",
                url="https://example.com/inactive",
                organization="CPS Energy",
                source_type="Corporate",
                authority_score=1.00,
                categories=("Energy",),
                discovery_reason="Disabled test source",
                active=False,
            ),
        )

        service = SourceDiscoveryService(
            store=self.store,
            catalog=catalog,
        )

        sources = service.discover(self.plan)

        self.assertEqual(len(sources), 1)
        self.assertEqual(
            sources[0].title,
            "Active Source",
        )

    def test_wrong_organization_is_excluded(self) -> None:
        catalog = (
            SourceCatalogEntry(
                title="Other Utility",
                url="https://example.com/other",
                organization="Austin Energy",
                source_type="Corporate",
                authority_score=1.00,
                categories=("Energy",),
                discovery_reason="Wrong organization",
            ),
        )

        service = SourceDiscoveryService(
            store=self.store,
            catalog=catalog,
        )

        sources = service.discover(self.plan)

        self.assertEqual(sources, ())

    def test_unapproved_source_type_is_excluded(self) -> None:
        catalog = (
            SourceCatalogEntry(
                title="Social Media Source",
                url="https://example.com/social",
                organization="CPS Energy",
                source_type="Social Media",
                authority_score=0.80,
                categories=("Energy",),
                discovery_reason="Unapproved source category",
            ),
        )

        service = SourceDiscoveryService(
            store=self.store,
            catalog=catalog,
        )

        sources = service.discover(self.plan)

        self.assertEqual(sources, ())

    def test_irrelevant_category_is_excluded(self) -> None:
        catalog = (
            SourceCatalogEntry(
                title="Healthcare Source",
                url="https://example.com/healthcare",
                organization="CPS Energy",
                source_type="Corporate",
                authority_score=1.00,
                categories=("Healthcare",),
                discovery_reason="Irrelevant category",
            ),
        )

        service = SourceDiscoveryService(
            store=self.store,
            catalog=catalog,
        )

        sources = service.discover(self.plan)

        self.assertEqual(sources, ())

    def test_rank_is_deterministic(self) -> None:
        service = SourceDiscoveryService(
            store=self.store
        )

        sources = service.discover(self.plan)

        first = service.rank(reversed(sources))
        second = service.rank(sources)

        self.assertEqual(
            tuple(
                source.source_fingerprint
                for source in first
            ),
            tuple(
                source.source_fingerprint
                for source in second
            ),
        )

    def test_invalid_maximum_sources_is_rejected(self) -> None:
        invalid_plan = replace(
            self.plan,
            maximum_sources=0,
        )

        service = SourceDiscoveryService(
            store=self.store
        )

        with self.assertRaises(
            DiscoveryValidationError
        ):
            service.discover(invalid_plan)

    def test_plan_without_categories_is_rejected(
        self,
    ) -> None:
        invalid_plan = replace(
            self.plan,
            research_categories=(),
        )

        service = SourceDiscoveryService(
            store=self.store
        )

        with self.assertRaises(
            DiscoveryValidationError
        ):
            service.discover(invalid_plan)


if __name__ == "__main__":
    unittest.main()
