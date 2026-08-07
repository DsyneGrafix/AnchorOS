"""
AIN-303.1 Research Planning Service.

Converts a bounded ResearchRequest into a deterministic ResearchPlan.

This module SHALL NOT perform source discovery, acquisition, AI reasoning,
finding extraction, evidence admission, scoring, or reporting.
"""

from __future__ import annotations

from hashlib import sha256
import json
from uuid import uuid4

from .models import (
    ResearchPlan,
    ResearchPlanStatus,
    ResearchRequest,
    normalize_text,
)


class ResearchPlanningError(Exception):
    """Base exception for research-planning failures."""


class ValidationError(ResearchPlanningError):
    """Raised when a research request is invalid."""


class ResearchPlanningService:
    """Create deterministic research plans from bounded requests."""

    DEFAULT_PRIORITY_SOURCES = (
        "Corporate",
        "Government",
        "Regulatory",
        "Industry",
    )

    DEFAULT_MAXIMUM_SOURCES = 25
    DEFAULT_TIME_WINDOW = "24 months"
    DEFAULT_STRATEGY = "STANDARD"

    def create_plan(
        self,
        request: ResearchRequest,
        *,
        pipeline_id: str | None = None,
    ) -> ResearchPlan:
        """Validate a request and return its deterministic research plan."""
        self._validate(request)

        return ResearchPlan(
            plan_id=self._deterministic_plan_id(request),
            request_id=request.request_id,
            organization=request.organization_identifier,
            research_categories=self._categorize(request),
            priority_sources=self.DEFAULT_PRIORITY_SOURCES,
            maximum_sources=self.DEFAULT_MAXIMUM_SOURCES,
            time_window=self.DEFAULT_TIME_WINDOW,
            acquisition_strategy=self.DEFAULT_STRATEGY,
            expected_outputs=request.requested_outputs,
            workspace=request.workspace_id,
            pipeline_id=pipeline_id or str(uuid4()),
            status=ResearchPlanStatus.PLANNED,
        )

    def _validate(self, request: ResearchRequest) -> None:
        """Reject requests that cannot produce a bounded research plan."""
        if not request.request_id.strip():
            raise ValidationError("request_id is required")

        if not request.workspace_id.strip():
            raise ValidationError("workspace_id is required")

        if not request.organization_identifier.strip():
            raise ValidationError("organization_identifier is required")

        if len(request.objective.strip()) < 20:
            raise ValidationError(
                "research objective must contain at least 20 characters"
            )

        if not request.requested_outputs:
            raise ValidationError(
                "at least one requested output is required"
            )

    def _deterministic_plan_id(
        self,
        request: ResearchRequest,
    ) -> str:
        """
        Generate the same plan ID for the same logical research request.

        The request UUID and pipeline UUID are intentionally excluded.
        """
        payload = {
            "workspace_id": normalize_text(request.workspace_id),
            "organization_identifier": normalize_text(
                request.organization_identifier
            ),
            "objective": normalize_text(request.objective),
            "requested_outputs": sorted(request.requested_outputs),
            "constraints": sorted(request.constraints),
        }

        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = sha256(canonical.encode("utf-8")).hexdigest()[:16]

        return f"PLAN-{digest}"

    def _categorize(
        self,
        request: ResearchRequest,
    ) -> tuple[str, ...]:
        """Derive deterministic initial categories from the objective."""
        text = normalize_text(request.objective)
        categories: set[str] = set()

        if "infrastructure" in text:
            categories.add("Infrastructure")

        if "communications" in text:
            categories.add("Communications")

        if "grid" in text or "energy" in text:
            categories.add("Energy")

        if "technology" in text:
            categories.add("Technology")

        if not categories:
            categories.add("General")

        return tuple(sorted(categories))
