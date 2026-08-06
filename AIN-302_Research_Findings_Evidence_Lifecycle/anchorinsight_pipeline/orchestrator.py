"""AIN-201.1 deterministic pipeline orchestrator."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from .context import PipelineContext
from .models import (
    PipelineManifest,
    PipelineReceipt,
    PipelineRequest,
    PipelineStatus,
    StageStatus,
    utc_now,
)
from .stage import PipelineStage
from .store import JsonPipelineStore


class CommercialIntelligencePipeline:
    VERSION = "201.1"

    def __init__(
        self,
        *,
        services: dict,
        stages: Iterable[PipelineStage],
        receipt_directory: str | Path = "data/pipeline_receipts",
    ) -> None:
        self.services = dict(services)
        self.stages = list(stages)
        self.store = JsonPipelineStore(receipt_directory)
        self._completed_by_idempotency_key: dict[str, PipelineReceipt] = {}

    def _manifest(self, request: PipelineRequest) -> PipelineManifest:
        definitions = [
            stage.definition(request.requested_outputs)
            for stage in self.stages
        ]
        versions = {
            "AIN-201": self.VERSION,
            "AIN-101": "1.0",
            "AIN-103": "1.0",
            **{
                name: str(getattr(service, "VERSION", "unknown"))
                for name, service in self.services.items()
            },
        }
        return PipelineManifest(
            pipeline_id=str(uuid4()),
            pipeline_version=self.VERSION,
            request=request,
            stage_definitions=definitions,
            service_versions=versions,
        )

    def run(self, request: PipelineRequest) -> PipelineReceipt:
        existing = self._completed_by_idempotency_key.get(request.idempotency_key)
        if existing is not None:
            return existing

        manifest = self._manifest(request)
        self.store.save_manifest(manifest.pipeline_id, manifest.to_dict())
        context = PipelineContext(
            request=request,
            manifest=manifest,
            services=self.services,
        )
        started = utc_now()
        terminal_status = PipelineStatus.RUNNING

        for stage in self.stages:
            definition = stage.definition(request.requested_outputs)
            result = stage.run(context)

            if result.status == StageStatus.REVALIDATION_REQUIRED:
                terminal_status = PipelineStatus.REVALIDATION_REQUIRED
                break
            if result.status == StageStatus.FAILED:
                terminal_status = (
                    PipelineStatus.PARTIALLY_COMPLETED
                    if context.stage_results[:-1]
                    else PipelineStatus.FAILED
                )
                break
            if result.status == StageStatus.CONSTRAINED:
                terminal_status = PipelineStatus.CONSTRAINED
                break

        if terminal_status == PipelineStatus.RUNNING:
            required = [item for item in context.stage_results if item.required]
            valid = {StageStatus.PASSED, StageStatus.SKIPPED, StageStatus.CONSTRAINED}
            terminal_status = (
                PipelineStatus.COMPLETED
                if required and all(item.status in valid for item in required)
                else PipelineStatus.PARTIALLY_COMPLETED
            )

        manifest.completed_at = utc_now()
        self.store.save_manifest(manifest.pipeline_id, manifest.to_dict())
        receipt = PipelineReceipt(
            pipeline_id=manifest.pipeline_id,
            request=request,
            status=terminal_status,
            stage_results=context.stage_results,
            started_at=started,
            completed_at=manifest.completed_at,
            manifest_hash=manifest.integrity_hash,
            warnings=context.warnings,
        )
        self.store.save_receipt(receipt.pipeline_id, receipt.to_dict())

        if terminal_status == PipelineStatus.COMPLETED:
            self._completed_by_idempotency_key[request.idempotency_key] = receipt
        return receipt
