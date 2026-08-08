"""AIN-302 -> Commercial Intelligence Registry adapter.

Translates an approved AIN-302 evidence commit into the existing
CommercialIntelligenceRegistryService API.

Boundary:
    AIN-302 owns source admission, finding review, and evidence authority.
    The Commercial Intelligence Registry owns durable commercial records.

The registry currently exposes ``create_source`` and ``add_evidence`` while
AIN-302 consumes a single ``create_evidence`` port. This adapter owns that
translation so neither subsystem has to absorb the other's implementation.
"""
from __future__ import annotations

from urllib.parse import urlparse
from typing import Any


class RegistryAdapterError(Exception):
    """Raised when an AIN-302 commit cannot be translated to the registry."""


class CommercialRegistryEvidenceAdapter:
    """Compatibility boundary consumed by EvidenceLifecycleService."""

    VERSION = "302.2"

    def __init__(self, registry: Any) -> None:
        self.registry = registry

    def create_evidence(
        self,
        *,
        evidence_id: str,
        organization_id: str,
        source_id: str,
        finding_id: str,
        finding_version: int,
        assertion: str,
        classification: str,
        confidence: float,
        review_id: str,
        reviewer_id: str,
        authority_reference: str,
        source_url: str,
        source_title: str,
        source_hash: str,
    ) -> str:
        """Create one governed commercial-registry evidence record.

        ``classification`` is the AIN-302 finding classification and is
        preserved as the registry ``evidence_type``. Because this path is
        reachable only after AIN-302 human approval, the registry evidence
        classification is ``Verified``.
        """
        self._validate(
            evidence_id=evidence_id,
            organization_id=organization_id,
            source_id=source_id,
            finding_id=finding_id,
            finding_version=finding_version,
            assertion=assertion,
            classification=classification,
            confidence=confidence,
            review_id=review_id,
            reviewer_id=reviewer_id,
            authority_reference=authority_reference,
            source_url=source_url,
            source_title=source_title,
            source_hash=source_hash,
        )

        normalized_hash = source_hash.strip().casefold()
        registry_source = self._find_source_by_provenance(
            url=source_url,
            checksum_sha256=normalized_hash,
        )

        if registry_source is None:
            registry_source = self._create_source_with_hash(
                source_title=source_title,
                source_url=source_url,
                source_hash=normalized_hash,
                reviewer_id=reviewer_id,
            )

        evidence = self.registry.add_evidence(
            source_identifier=registry_source["source_id"],
            assertion=assertion,
            evidence_type=classification,
            classification="Verified",
            actor=reviewer_id,
            subject_type="Organization",
            subject_identifier=organization_id,
            confidence=confidence,
            reviewer=reviewer_id,
            relevance="High",
            link_type="Supports",
            assertion_supported=assertion,
        )

        registry_identifier = evidence.get("cof_evidence_id")
        if not registry_identifier:
            raise RegistryAdapterError(
                "Commercial registry did not return a COF evidence identifier."
            )
        return str(registry_identifier)

    def _find_source_by_provenance(
        self,
        *,
        url: str,
        checksum_sha256: str,
    ) -> dict[str, Any] | None:
        """Reuse an existing registry source with identical URL and hash."""
        connection = self.registry.db.connect()
        try:
            row = connection.execute(
                """
                SELECT * FROM sources
                WHERE url = ? AND checksum_sha256 = ? AND status = 'Active'
                ORDER BY created_at
                LIMIT 1
                """,
                (url, checksum_sha256),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            connection.close()

    def _create_source_with_hash(
        self,
        *,
        source_title: str,
        source_url: str,
        source_hash: str,
        reviewer_id: str,
    ) -> dict[str, Any]:
        """Create a registry source and preserve AIN-303's verified hash.

        The current registry ``create_source`` API computes a checksum only
        when raw content is supplied. AIN-302 receives the already-verified
        source hash from AIN-303, so this compatibility adapter records that
        exact digest immediately after source creation.
        """
        registry_source = self.registry.create_source(
            source_type="AIN-302 Governed Source",
            title=source_title,
            actor=reviewer_id,
            publisher=self._publisher_from_url(source_url),
            url=source_url,
            confidentiality="Public",
        )

        with self.registry.db.transaction() as connection:
            connection.execute(
                """
                UPDATE sources
                SET checksum_sha256 = ?
                WHERE source_id = ?
                """,
                (source_hash, registry_source["source_id"]),
            )

        refreshed = self._find_source_by_provenance(
            url=source_url,
            checksum_sha256=source_hash,
        )
        if refreshed is None:
            raise RegistryAdapterError(
                "Registry source provenance could not be verified after creation."
            )
        return refreshed

    @staticmethod
    def _publisher_from_url(url: str) -> str:
        host = urlparse(url).hostname
        if not host:
            raise RegistryAdapterError(
                f"Unable to derive source publisher from URL: {url}"
            )
        return host.removeprefix("www.")

    @staticmethod
    def _validate(**payload: Any) -> None:
        required_text = (
            "evidence_id",
            "organization_id",
            "source_id",
            "finding_id",
            "assertion",
            "classification",
            "review_id",
            "reviewer_id",
            "authority_reference",
            "source_url",
            "source_title",
            "source_hash",
        )
        for name in required_text:
            value = payload[name]
            if not isinstance(value, str) or not value.strip():
                raise RegistryAdapterError(f"{name} is required")

        if int(payload["finding_version"]) < 1:
            raise RegistryAdapterError("finding_version must be at least 1")

        confidence = float(payload["confidence"])
        if not 0 <= confidence <= 1:
            raise RegistryAdapterError("confidence must be between 0 and 1")

        source_hash = str(payload["source_hash"]).strip().casefold()
        if len(source_hash) != 64:
            raise RegistryAdapterError("source_hash must be a SHA-256 hex digest")
        try:
            int(source_hash, 16)
        except ValueError as exc:
            raise RegistryAdapterError(
                "source_hash must be a SHA-256 hex digest"
            ) from exc
