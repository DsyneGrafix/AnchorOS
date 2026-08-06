"""Append-preserving JSON store for AIN-302 proof artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence_models import (
    AdmittedSource,
    EvidenceCommitRecord,
    FindingReceipt,
    ResearchFinding,
    ReviewRecord,
)


class EvidenceLifecycleStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        for name in ("sources", "findings", "finding_receipts", "reviews", "commits"):
            (self.root / name).mkdir(exist_ok=True)

    def _write_once(self, category: str, object_id: str, payload: dict[str, Any]) -> Path:
        path = self.root / category / f"{object_id}.json"
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing != payload:
                raise ValueError(f"Immutable object already exists with different content: {path}")
            return path
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def save_source(self, source: AdmittedSource) -> Path:
        return self._write_once("sources", source.source_id, source.to_dict())

    def save_finding(self, finding: ResearchFinding) -> Path:
        # A finding version is immutable. Status transitions are represented by review records.
        object_id = f"{finding.finding_id}.v{finding.finding_version}"
        return self._write_once("findings", object_id, finding.to_dict())

    def save_finding_receipt(self, receipt: FindingReceipt) -> Path:
        payload = receipt.__dict__.copy()
        object_id = f"{receipt.finding_id}.v{receipt.finding_version}"
        return self._write_once("finding_receipts", object_id, payload)

    def save_review(self, review: ReviewRecord) -> Path:
        return self._write_once("reviews", review.review_id, review.to_dict())

    def save_commit(self, commit: EvidenceCommitRecord) -> Path:
        return self._write_once("commits", commit.evidence_id, commit.__dict__.copy())

    def find_commit_for_finding(self, finding_id: str, finding_version: int) -> dict[str, Any] | None:
        for path in (self.root / "commits").glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if (
                payload["finding_id"] == finding_id
                and payload["finding_version"] == finding_version
            ):
                return payload
        return None

    def reconstruct_chain(self, evidence_id: str) -> dict[str, Any]:
        commit_path = self.root / "commits" / f"{evidence_id}.json"
        commit = json.loads(commit_path.read_text(encoding="utf-8"))
        source = json.loads(
            (self.root / "sources" / f"{commit['source_id']}.json").read_text(encoding="utf-8")
        )
        finding = json.loads(
            (
                self.root
                / "findings"
                / f"{commit['finding_id']}.v{commit['finding_version']}.json"
            ).read_text(encoding="utf-8")
        )
        review = json.loads(
            (self.root / "reviews" / f"{commit['review_id']}.json").read_text(encoding="utf-8")
        )
        return {
            "source": source,
            "finding": finding,
            "review": review,
            "evidence_commit": commit,
        }
