"""AIN-107 — AnchorInsight Executive Intelligence Report Service.

Builds a deterministic executive brief from the AIN-103 Organization
Intelligence Profile. The service consumes governed registry/profile state; it
does not acquire sources, create findings, approve evidence, or rescore a
subject.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any


@dataclass(frozen=True)
class ExecutiveBrief:
    """Display-ready executive intelligence report."""

    report_id: str
    report_version: str
    generated_at: str
    organization: dict[str, Any]
    executive_summary: dict[str, Any]
    commercial_confidence: dict[str, Any]
    scorecard_summary: tuple[dict[str, Any], ...]
    evidence_summary: dict[str, Any]
    opportunities: dict[str, Any]
    risks: dict[str, Any]
    actions: dict[str, Any]
    data_quality: dict[str, Any]
    evidence_basis: tuple[str, ...]

    @property
    def integrity_hash(self) -> str:
        payload = self.to_dict(include_integrity=False)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self, *, include_integrity: bool = True) -> dict[str, Any]:
        payload = {
            "report_id": self.report_id,
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "organization": self.organization,
            "executive_summary": self.executive_summary,
            "commercial_confidence": self.commercial_confidence,
            "scorecard_summary": list(self.scorecard_summary),
            "evidence_summary": self.evidence_summary,
            "opportunities": self.opportunities,
            "risks": self.risks,
            "actions": self.actions,
            "data_quality": self.data_quality,
            "evidence_basis": list(self.evidence_basis),
        }
        if include_integrity:
            payload["integrity_hash"] = self.integrity_hash
        return payload


class ExecutiveReportService:
    """Generate an executive brief from governed AIN-103 profile state."""

    VERSION = "107.1"
    REPORT_VERSION = "1.0"

    def __init__(self, profiles: Any) -> None:
        self.profiles = profiles

    def generate_executive_brief(self, organization_identifier: str) -> ExecutiveBrief:
        profile = self.profiles.export_payload(organization_identifier)
        organization = profile["organization"]
        evidence = profile["evidence"]
        decision = profile["decision"]

        evidence_basis = tuple(
            item["cof_evidence_id"]
            for item in evidence["items"]
            if item.get("cof_evidence_id")
        )

        report_id = self._report_id(
            organization_identifier=organization["cof_organization_id"],
            evidence_basis=evidence_basis,
            decision=decision["decision"],
            cci=profile["commercial_confidence"].get("score"),
        )

        summary = {
            "headline": profile["headline"],
            "decision": decision["decision"],
            "confidence": decision.get("confidence"),
            "next_justified_action": decision["next_action"],
            "basis": decision.get("basis"),
            "readiness": profile["readiness"],
        }

        evidence_summary = {
            "count": evidence["count"],
            "classification_counts": evidence["classification_counts"],
            "verified_count": evidence["classification_counts"].get("Verified", 0),
            "items": tuple(evidence["items"]),
        }

        return ExecutiveBrief(
            report_id=report_id,
            report_version=self.REPORT_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
            organization=organization,
            executive_summary=summary,
            commercial_confidence=profile["commercial_confidence"],
            scorecard_summary=tuple(profile["score_tiles"]),
            evidence_summary=evidence_summary,
            opportunities=profile["opportunities"],
            risks=profile["risks"],
            actions=profile["actions"],
            data_quality=profile["data_quality"],
            evidence_basis=evidence_basis,
        )

    @staticmethod
    def _report_id(
        *,
        organization_identifier: str,
        evidence_basis: tuple[str, ...],
        decision: str,
        cci: float | None,
    ) -> str:
        payload = {
            "organization": organization_identifier,
            "evidence_basis": sorted(evidence_basis),
            "decision": decision,
            "cci": cci,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return f"EXR-{digest}"
