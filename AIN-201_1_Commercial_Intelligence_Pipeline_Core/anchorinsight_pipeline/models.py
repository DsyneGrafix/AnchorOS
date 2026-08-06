"""AIN-201 immutable request, manifest, stage-result, and receipt models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PipelineStatus(StrEnum):
    QUEUED = "Queued"
    RUNNING = "Running"
    WAITING_FOR_REVIEW = "Waiting for Evidence Review"
    CONSTRAINED = "Constrained"
    REVALIDATION_REQUIRED = "Revalidation Required"
    COMPLETED = "Completed"
    PARTIALLY_COMPLETED = "Partially Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    ARCHIVED = "Archived"


class StageStatus(StrEnum):
    PENDING = "Pending"
    RUNNING = "Running"
    PASSED = "Passed"
    SKIPPED = "Skipped"
    CONSTRAINED = "Constrained"
    REVALIDATION_REQUIRED = "Revalidation Required"
    FAILED = "Failed"


@dataclass(frozen=True)
class PipelineRequest:
    workspace_id: str
    organization_identifier: str
    requested_by: str
    research_objective: str
    requested_outputs: tuple[str, ...] = ("Organization Profile",)
    market_scope: str | None = None
    source_policy: str = "approved_sources_only"
    priority: str = "Normal"
    review_policy: str = "human_required"
    request_version: str = "1.0"
    pipeline_request_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)

    def validate(self) -> None:
        required = {
            "workspace_id": self.workspace_id,
            "organization_identifier": self.organization_identifier,
            "requested_by": self.requested_by,
            "research_objective": self.research_objective,
        }
        blank = [name for name, value in required.items() if not value or not value.strip()]
        if blank:
            raise ValueError(f"Blank required request fields: {', '.join(blank)}")
        if len(self.research_objective.strip()) < 20:
            raise ValueError("Research objective must be bounded and at least 20 characters.")

    @property
    def request_fingerprint(self) -> str:
        payload = {
            "workspace_id": self.workspace_id,
            "organization_identifier": self.organization_identifier.casefold(),
            "research_objective": " ".join(self.research_objective.split()).casefold(),
            "source_policy": self.source_policy,
            "requested_outputs": sorted(self.requested_outputs),
            "request_version": self.request_version,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def idempotency_key(self) -> str:
        return f"AIN201-{self.request_fingerprint[:24]}"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["requested_outputs"] = list(self.requested_outputs)
        result["request_fingerprint"] = self.request_fingerprint
        result["idempotency_key"] = self.idempotency_key
        return result


@dataclass(frozen=True)
class StageDefinition:
    name: str
    version: str
    required: bool
    requested_output: str | None = None


@dataclass
class StageResult:
    stage_id: str
    pipeline_request_id: str
    stage_name: str
    stage_version: str
    required: bool
    status: StageStatus
    started_at: str
    completed_at: str
    input_references: list[str] = field(default_factory=list)
    output_references: list[str] = field(default_factory=list)
    decision: str = "CONTINUE"
    reason_code: str = "STAGE_COMPLETE"
    warnings: list[str] = field(default_factory=list)
    evidence_references: list[str] = field(default_factory=list)
    audit_reference: str | None = None
    retry_count: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result


@dataclass
class PipelineManifest:
    pipeline_id: str
    pipeline_version: str
    request: PipelineRequest
    stage_definitions: list[StageDefinition]
    service_versions: dict[str, str]
    execution_policy: str = "fail_visible"
    evidence_policy: str = "human_review_before_authority"
    replay_policy: str = "original_immutable"
    created_at: str = field(default_factory=utc_now)
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "pipeline_version": self.pipeline_version,
            "request": self.request.to_dict(),
            "stage_definitions": [asdict(item) for item in self.stage_definitions],
            "service_versions": self.service_versions,
            "execution_policy": self.execution_policy,
            "evidence_policy": self.evidence_policy,
            "replay_policy": self.replay_policy,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "integrity_hash": self.integrity_hash,
        }

    @property
    def integrity_hash(self) -> str:
        payload = {
            "pipeline_id": self.pipeline_id,
            "pipeline_version": self.pipeline_version,
            "request": self.request.to_dict(),
            "stage_definitions": [asdict(item) for item in self.stage_definitions],
            "service_versions": self.service_versions,
            "execution_policy": self.execution_policy,
            "evidence_policy": self.evidence_policy,
            "replay_policy": self.replay_policy,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class PipelineReceipt:
    pipeline_id: str
    request: PipelineRequest
    status: PipelineStatus
    stage_results: list[StageResult]
    started_at: str
    completed_at: str
    manifest_hash: str
    warnings: list[str] = field(default_factory=list)

    @property
    def required_stage_count(self) -> int:
        return sum(1 for item in self.stage_results if item.required)

    @property
    def required_stages_passed(self) -> int:
        valid = {StageStatus.PASSED, StageStatus.SKIPPED, StageStatus.CONSTRAINED}
        return sum(1 for item in self.stage_results if item.required and item.status in valid)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "pipeline_id": self.pipeline_id,
            "workspace_id": self.request.workspace_id,
            "organization_identifier": self.request.organization_identifier,
            "research_objective": self.request.research_objective,
            "requested_outputs": list(self.request.requested_outputs),
            "status": self.status.value,
            "stages_attempted": len(self.stage_results),
            "required_stages_passed": self.required_stages_passed,
            "required_stage_count": self.required_stage_count,
            "stage_results": [item.to_dict() for item in self.stage_results],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "manifest_hash": self.manifest_hash,
            "warnings": self.warnings,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload["integrity_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return payload
