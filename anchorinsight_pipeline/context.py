"""Mutable execution context shared by AIN-201 stages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import PipelineManifest, PipelineRequest, StageResult


@dataclass
class PipelineContext:
    request: PipelineRequest
    manifest: PipelineManifest
    services: dict[str, Any]
    data: dict[str, Any] = field(default_factory=dict)
    stage_results: list[StageResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def service(self, name: str) -> Any:
        try:
            return self.services[name]
        except KeyError as exc:
            raise KeyError(f"Required pipeline service is unavailable: {name}") from exc
