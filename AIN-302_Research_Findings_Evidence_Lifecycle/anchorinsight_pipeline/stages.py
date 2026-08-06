"""Initial AIN-201.1 stages."""
from __future__ import annotations

from .context import PipelineContext
from .errors import PipelineValidationError
from .models import StageStatus
from .stage import PipelineStage, StageExecution


class RequestValidationStage(PipelineStage):
    name = "Research Request"
    version = "1.0"

    def execute(self, context: PipelineContext) -> StageExecution:
        try:
            context.request.validate()
        except ValueError as exc:
            raise PipelineValidationError(str(exc)) from exc
        context.data["request_validated"] = True
        return StageExecution(
            output_references=[context.request.pipeline_request_id],
            details={
                "idempotency_key": context.request.idempotency_key,
                "request_fingerprint": context.request.request_fingerprint,
            },
        )


class TargetResolutionStage(PipelineStage):
    name = "Target Resolution"
    version = "1.0"

    def validate(self, context: PipelineContext) -> None:
        if not context.data.get("request_validated"):
            raise PipelineValidationError("Research Request stage must pass first.")

    def execute(self, context: PipelineContext) -> StageExecution:
        registry = context.service("registry")
        identifier = context.request.organization_identifier
        try:
            organization = registry.get_organization(identifier)
        except Exception as exc:
            return StageExecution(
                status=StageStatus.REVALIDATION_REQUIRED,
                decision="REVALIDATE",
                reason_code="ORGANIZATION_NOT_RESOLVED",
                input_references=[identifier],
                warnings=[str(exc)],
                details={"organization_identifier": identifier},
            )

        context.data["organization"] = organization
        canonical = organization.get("cof_organization_id") or organization.get("organization_id")
        return StageExecution(
            input_references=[identifier],
            output_references=[canonical],
            details={
                "organization_id": organization.get("organization_id"),
                "cof_organization_id": organization.get("cof_organization_id"),
                "legal_name": organization.get("legal_name"),
                "common_name": organization.get("common_name"),
                "website": organization.get("website"),
                "headquarters": organization.get("headquarters"),
            },
        )


class ProfileRefreshStage(PipelineStage):
    """Initial read-only proof that orchestration reaches AIN-103."""

    name = "Organization Profile Refresh"
    version = "1.0"

    def validate(self, context: PipelineContext) -> None:
        if "organization" not in context.data:
            raise PipelineValidationError("A canonical organization is required.")

    def execute(self, context: PipelineContext) -> StageExecution:
        profiles = context.service("profiles")
        identifier = context.data["organization"]["cof_organization_id"]
        profile = profiles.build_profile(identifier)
        context.data["profile"] = profile
        return StageExecution(
            input_references=[identifier],
            output_references=[f"profile:{identifier}"],
            details={
                "display_name": profile["organization"]["display_name"],
                "decision": profile["decision"]["decision"],
                "readiness": profile["readiness"]["status"],
                "cci": profile["commercial_confidence"]["score"],
            },
        )


class ReportRequestStage(PipelineStage):
    """Optional placeholder proving requested-output stage semantics."""

    name = "Report Generation"
    version = "1.0"
    always_required = False
    requested_output = "Executive Brief"

    def execute(self, context: PipelineContext) -> StageExecution:
        if self.requested_output not in context.request.requested_outputs:
            return StageExecution(
                status=StageStatus.SKIPPED,
                decision="CONTINUE",
                reason_code="OPTIONAL_OUTPUT_NOT_REQUESTED",
            )
        return StageExecution(
            status=StageStatus.FAILED,
            decision="CONSTRAIN",
            reason_code="REPORT_SERVICE_NOT_IMPLEMENTED",
            warnings=["Executive Brief was requested, but AIN-107 is not implemented in AIN-201.1."],
        )
