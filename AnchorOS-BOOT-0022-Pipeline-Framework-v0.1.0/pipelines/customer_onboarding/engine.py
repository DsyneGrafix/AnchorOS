"""Deterministic Customer Onboarding Pipeline engine."""

from __future__ import annotations

from copy import deepcopy
import re

from core.boot_pipeline import BootPipeline
from core.module import Module
from core.pipeline import PipelineRunner
from core.service_registry import ServiceRegistry
from services.audit import Audit
from services.configuration import Configuration
from services.event import AnchorEvent
from services.eventbus import EventBus
from services.health import Health
from services.manifest import PlatformManifest

from .errors import CustomerPipelineError, StageRequirementError
from .lifecycle import CustomerLifecycleManager
from .models import (
    CustomerRecord,
    CustomerState,
    OnboardingRequest,
    ReplayResult,
    canonical_hash,
)
from .security import SecurityCoreGateway
from .stages import CUSTOMER_PIPELINE_STAGES, StageDefinition


class CustomerPipelineEngine(Module):
    """
    Provision organizations through CP-001 to CP-009.

    This engine deliberately excludes CRM, billing, payments, invoicing,
    forecasting, marketing automation, authentication, and authorization.
    """

    EVENT_STAGE_COMPLETED = "customer_onboarding.stage.completed"
    EVENT_STAGE_FAILED = "customer_onboarding.stage.failed"
    EVENT_REPLAY_VERIFIED = "customer_onboarding.replay.verified"
    EVENT_REPLAY_FAILED = "customer_onboarding.replay.failed"

    def __init__(
        self,
        *,
        audit: Audit,
        event_bus: EventBus,
        configuration: Configuration,
        manifest: PlatformManifest,
        health: Health,
        boot_pipeline: BootPipeline,
        security_core: SecurityCoreGateway,
    ) -> None:
        super().__init__("Customer Onboarding Pipeline", "0.1.0")
        self.audit = audit
        self.event_bus = event_bus
        self.configuration = configuration
        self.manifest = manifest
        self.health_monitor = health
        self.boot_pipeline = boot_pipeline
        self.security_core = security_core
        self.lifecycle = CustomerLifecycleManager()
        self.pipeline_runner = PipelineRunner()
        self._records: dict[str, CustomerRecord] = {}

        for event_type in (
            self.EVENT_STAGE_COMPLETED,
            self.EVENT_STAGE_FAILED,
            self.EVENT_REPLAY_VERIFIED,
            self.EVENT_REPLAY_FAILED,
        ):
            self.event_bus.subscribe(
                event_type=event_type,
                handler=self.audit.handle_event,
            )

        self._handlers = {
            "CP-001": self._customer_registration,
            "CP-002": self._organization_provisioning,
            "CP-003": self._identity_role_assignment,
            "CP-004": self._license_assignment,
            "CP-005": self._framework_enablement,
            "CP-006": self._security_policy_assignment,
            "CP-007": self._deployment_preparation,
            "CP-008": self._validation,
            "CP-009": self._operational,
        }

    @classmethod
    def from_registry(
        cls,
        *,
        registry: ServiceRegistry,
        boot_pipeline: BootPipeline,
        security_core: SecurityCoreGateway,
    ) -> CustomerPipelineEngine:
        """Create the pipeline from authoritative Platform Services."""

        audit = registry.require("Audit Engine")
        event_bus = registry.require("Event Bus")
        configuration = registry.require("Configuration")
        manifest = registry.require("Platform Manifest")
        health = registry.require("Health Monitor")

        required_types = (
            (audit, Audit),
            (event_bus, EventBus),
            (configuration, Configuration),
            (manifest, PlatformManifest),
            (health, Health),
        )
        invalid = [
            expected.__name__
            for service, expected in required_types
            if not isinstance(service, expected)
        ]
        if invalid:
            raise RuntimeError(
                "Customer Onboarding Pipeline received invalid "
                "Platform Service types: " + ", ".join(invalid)
            )

        return cls(
            audit=audit,
            event_bus=event_bus,
            configuration=configuration,
            manifest=manifest,
            health=health,
            boot_pipeline=boot_pipeline,
            security_core=security_core,
        )

    def start(self) -> None:
        """Start only when the consumed Platform Services are running."""

        consumed_services = (
            self.audit,
            self.event_bus,
            self.configuration,
            self.manifest,
            self.health_monitor,
        )
        unavailable = sorted(
            service.name
            for service in consumed_services
            if service.status != "Running"
        )
        if unavailable:
            raise RuntimeError(
                "Customer Onboarding Pipeline requires running "
                "Platform Services: " + ", ".join(unavailable)
            )
        super().start()

    def execute(
        self,
        request: OnboardingRequest,
    ) -> CustomerRecord:
        """Execute once, persist the record, and stop at first failure."""

        record = self._run(
            request,
            persist=True,
            emit_events=True,
        )
        return deepcopy(record)

    def replay(self, onboarding_id: str) -> ReplayResult:
        """Re-execute deterministically and compare transition evidence."""

        if onboarding_id not in self._records:
            raise KeyError(
                f"Onboarding record not found: {onboarding_id}"
            )

        expected = self._records[onboarding_id]
        actual = self._run(
            expected.request,
            persist=False,
            emit_events=False,
        )

        expected_chain_valid = self.lifecycle.verify(expected)
        actual_chain_valid = self.lifecycle.verify(actual)
        verified = (
            expected_chain_valid
            and actual_chain_valid
            and expected.state is actual.state
            and expected.final_hash == actual.final_hash
            and len(expected.transitions) == len(actual.transitions)
        )
        message = (
            "Deterministic replay matched the stored transition chain."
            if verified
            else "Deterministic replay did not match stored evidence."
        )
        result = ReplayResult(
            onboarding_id=onboarding_id,
            verified=verified,
            expected_hash=expected.final_hash,
            actual_hash=actual.final_hash,
            expected_transitions=len(expected.transitions),
            actual_transitions=len(actual.transitions),
            message=message,
        )

        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type=(
                    self.EVENT_REPLAY_VERIFIED
                    if verified
                    else self.EVENT_REPLAY_FAILED
                ),
                message=message,
                severity="INFO" if verified else "ERROR",
                payload=result.to_dict(),
            )
        )
        return result

    def get_record(self, onboarding_id: str) -> CustomerRecord:
        """Return an isolated copy of a stored onboarding record."""

        if onboarding_id not in self._records:
            raise KeyError(
                f"Onboarding record not found: {onboarding_id}"
            )
        return deepcopy(self._records[onboarding_id])

    def list_records(self) -> list[dict[str, object]]:
        """Return deterministic onboarding summaries."""

        return [
            {
                "onboarding_id": record.onboarding_id,
                "state": record.state.value,
                "failed_stage": record.failed_stage,
                "final_hash": record.final_hash,
            }
            for _, record in sorted(self._records.items())
        ]

    def verify_record(self, record: CustomerRecord) -> bool:
        """Verify a supplied record's hash-linked transition evidence."""

        return self.lifecycle.verify(record)

    def _run(
        self,
        request: OnboardingRequest,
        *,
        persist: bool,
        emit_events: bool,
    ) -> CustomerRecord:
        if self.status != "Running":
            raise RuntimeError(
                "Customer Onboarding Pipeline is not running."
            )

        record = CustomerRecord(request=request)

        def execute_stage(stage):
            input_hash = canonical_hash(record.input_snapshot())

            try:
                if record.state is not stage.entry_state:
                    raise StageRequirementError(
                        f"Expected {stage.entry_state.value}; "
                        f"found {record.state.value}."
                    )

                handler = self._handlers[stage.code]
                details = handler(
                    record,
                    enforce_unique=persist,
                )
                record.artifacts[stage.code] = deepcopy(details)
                transition = self.lifecycle.advance(
                    record,
                    stage,
                    input_hash=input_hash,
                    details=details,
                )
                if emit_events:
                    self._publish_transition(
                        stage,
                        transition.to_dict(),
                        success=True,
                    )
            except Exception as error:
                reason = self._safe_failure_reason(error)
                transition = self.lifecycle.fail(
                    record,
                    stage,
                    input_hash=input_hash,
                    reason=reason,
                )
                if emit_events:
                    self._publish_transition(
                        stage,
                        transition.to_dict(),
                        success=False,
                    )
                return False
            return True

        self.pipeline_runner.execute_ordered(
            CUSTOMER_PIPELINE_STAGES,
            execute_stage,
        )

        if (
            persist
            and request.onboarding_id not in self._records
        ):
            self._records[request.onboarding_id] = deepcopy(record)
        return record

    def _customer_registration(
        self,
        record: CustomerRecord,
        *,
        enforce_unique: bool,
    ) -> dict[str, object]:
        request = record.request
        if not request.onboarding_id.strip():
            raise StageRequirementError(
                "Onboarding identifier is required."
            )
        if enforce_unique and request.onboarding_id in self._records:
            raise StageRequirementError(
                "Onboarding identifier is already registered."
            )
        if not request.organization_name.strip():
            raise StageRequirementError(
                "Organization name is required."
            )
        if not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?",
            request.organization_slug,
        ):
            raise StageRequirementError(
                "Organization slug must be lowercase alphanumeric "
                "with internal hyphens and at most 63 characters."
            )
        return {
            "onboarding_id": request.onboarding_id,
            "organization_name": request.organization_name.strip(),
            "organization_slug": request.organization_slug,
            "status": "Registered",
        }

    def _organization_provisioning(
        self,
        record: CustomerRecord,
        *,
        enforce_unique: bool,
    ) -> dict[str, object]:
        del enforce_unique
        slug = record.request.organization_slug
        identifier_hash = canonical_hash({"organization_slug": slug})
        return {
            "organization_id": (
                f"ORG-{identifier_hash[:12].upper()}"
            ),
            "organization_slug": slug,
            "status": "Provisioned",
        }

    def _identity_role_assignment(
        self,
        record: CustomerRecord,
        *,
        enforce_unique: bool,
    ) -> dict[str, object]:
        del enforce_unique
        self._require_security_core()
        request = record.request
        identity_id = request.primary_identity_id.strip()
        roles = tuple(sorted(request.requested_roles))
        if not identity_id:
            raise StageRequirementError(
                "Primary identity identifier is required."
            )
        if not roles or any(not role.strip() for role in roles):
            raise StageRequirementError(
                "At least one non-empty role is required."
            )
        if len(set(roles)) != len(roles):
            raise StageRequirementError(
                "Requested roles must be unique."
            )
        organization_id = self._organization_id(record)
        receipt = self.security_core.assign_identity_and_roles(
            organization_id=organization_id,
            identity_id=identity_id,
            roles=roles,
            idempotency_key=(
                f"{request.onboarding_id}:CP-003"
            ),
        )
        self._require_security_receipt(
            receipt,
            organization_id=organization_id,
            assignment_type="identity_roles",
        )
        return deepcopy(receipt)

    def _license_assignment(
        self,
        record: CustomerRecord,
        *,
        enforce_unique: bool,
    ) -> dict[str, object]:
        del enforce_unique
        allowed = self._configured_values(
            "customer_pipeline.allowed_licenses"
        )
        license_id = record.request.license_id
        if license_id not in allowed:
            raise StageRequirementError(
                f"License is not configured: {license_id}"
            )
        organization_id = self._organization_id(record)
        assignment_hash = canonical_hash(
            {
                "organization_id": organization_id,
                "license_id": license_id,
            }
        )
        return {
            "assignment_id": (
                f"LIC-{assignment_hash[:16].upper()}"
            ),
            "organization_id": organization_id,
            "license_id": license_id,
            "status": "Assigned",
            "commercial_transaction": False,
        }

    def _framework_enablement(
        self,
        record: CustomerRecord,
        *,
        enforce_unique: bool,
    ) -> dict[str, object]:
        del enforce_unique
        requested = tuple(sorted(record.request.frameworks))
        if not requested:
            raise StageRequirementError(
                "At least one framework must be requested."
            )
        if len(set(requested)) != len(requested):
            raise StageRequirementError(
                "Requested frameworks must be unique."
            )

        manifest_frameworks = set(
            self.manifest.describe()["frameworks"]
        )
        framework_states = (
            self.health_monitor.get_framework_states()
        )
        missing = sorted(set(requested) - manifest_frameworks)
        unhealthy = sorted(
            framework
            for framework in requested
            if framework_states.get(framework) != "Running"
        )
        if missing:
            raise StageRequirementError(
                "Frameworks are not registered in Manifest: "
                + ", ".join(missing)
            )
        if unhealthy:
            raise StageRequirementError(
                "Frameworks are not Running in Health: "
                + ", ".join(unhealthy)
            )
        return {
            "organization_id": self._organization_id(record),
            "frameworks": requested,
            "status": "Enabled",
        }

    def _security_policy_assignment(
        self,
        record: CustomerRecord,
        *,
        enforce_unique: bool,
    ) -> dict[str, object]:
        del enforce_unique
        self._require_security_core()
        policy_id = record.request.security_policy_id.strip()
        if not policy_id:
            raise StageRequirementError(
                "Security policy identifier is required."
            )
        organization_id = self._organization_id(record)
        receipt = self.security_core.assign_policy(
            organization_id=organization_id,
            policy_id=policy_id,
            idempotency_key=(
                f"{record.request.onboarding_id}:CP-006"
            ),
        )
        self._require_security_receipt(
            receipt,
            organization_id=organization_id,
            assignment_type="security_policy",
        )
        return deepcopy(receipt)

    def _deployment_preparation(
        self,
        record: CustomerRecord,
        *,
        enforce_unique: bool,
    ) -> dict[str, object]:
        del enforce_unique
        allowed = self._configured_values(
            "customer_pipeline.allowed_environments"
        )
        environment = record.request.deployment_environment
        if environment not in allowed:
            raise StageRequirementError(
                "Deployment environment is not configured: "
                f"{environment}"
            )

        manifest = self.manifest.describe()
        plan = {
            "organization_id": self._organization_id(record),
            "environment": environment,
            "platform_product": manifest["product"],
            "platform_version": manifest["version"],
            "platform_boot": manifest["boot"],
            "action": "PrepareOnly",
        }
        plan_hash = canonical_hash(plan)
        return {
            **plan,
            "deployment_plan_id": (
                f"DEP-{plan_hash[:16].upper()}"
            ),
            "plan_hash": plan_hash,
            "status": "Ready",
        }

    def _validation(
        self,
        record: CustomerRecord,
        *,
        enforce_unique: bool,
    ) -> dict[str, object]:
        del enforce_unique
        required_artifacts = {
            f"CP-{number:03d}"
            for number in range(1, 8)
        }
        missing_artifacts = sorted(
            required_artifacts - set(record.artifacts)
        )
        if missing_artifacts:
            raise StageRequirementError(
                "Prior-stage evidence is missing: "
                + ", ".join(missing_artifacts)
            )
        if not self.lifecycle.verify(record):
            raise StageRequirementError(
                "Transition evidence chain failed verification."
            )

        boot_results = self.boot_pipeline.results
        boot_verified = (
            len(boot_results) == len(self.boot_pipeline.stages)
            and self.boot_pipeline.summary()
            and all(result.success for result in boot_results)
        )
        if not boot_verified:
            raise StageRequirementError(
                "Boot Pipeline has not passed every stage."
            )

        required_services = self._configured_values(
            "customer_pipeline.required_platform_services"
        )
        manifest_services = set(
            self.manifest.describe()["services"]
        )
        missing_services = sorted(
            set(required_services) - manifest_services
        )
        if missing_services:
            raise StageRequirementError(
                "Required Platform Services are absent from Manifest: "
                + ", ".join(missing_services)
            )

        service_status = {
            self.audit.name: self.audit.status,
            self.event_bus.name: self.event_bus.status,
            self.configuration.name: self.configuration.status,
            self.manifest.name: self.manifest.status,
            self.health_monitor.name: self.health_monitor.status,
        }
        not_running = sorted(
            name
            for name in required_services
            if service_status.get(name) != "Running"
        )
        if not_running:
            raise StageRequirementError(
                "Required Platform Services are not Running: "
                + ", ".join(not_running)
            )
        self._require_security_core()

        evidence = {
            "organization_id": self._organization_id(record),
            "boot_stages_passed": len(boot_results),
            "platform_services": required_services,
            "prior_transition_hash": record.final_hash,
            "status": "PASS",
        }
        receipt_hash = canonical_hash(evidence)
        return {
            **evidence,
            "validation_id": (
                f"VAL-{receipt_hash[:16].upper()}"
            ),
            "validation_hash": receipt_hash,
        }

    def _operational(
        self,
        record: CustomerRecord,
        *,
        enforce_unique: bool,
    ) -> dict[str, object]:
        del enforce_unique
        validation = record.artifacts.get("CP-008", {})
        if validation.get("status") != "PASS":
            raise StageRequirementError(
                "A passing validation receipt is required."
            )
        return {
            "organization_id": self._organization_id(record),
            "validation_id": validation["validation_id"],
            "status": "Operational",
        }

    def _organization_id(self, record: CustomerRecord) -> str:
        value = record.artifacts.get("CP-002", {}).get(
            "organization_id"
        )
        if not isinstance(value, str) or not value:
            raise StageRequirementError(
                "Provisioned organization identifier is unavailable."
            )
        return value

    def _configured_values(self, key: str) -> tuple[str, ...]:
        try:
            configured = self.configuration.require(key)
        except RuntimeError as error:
            raise StageRequirementError(str(error)) from error

        if not isinstance(configured, (list, tuple)):
            raise StageRequirementError(
                f"Configuration must be a list or tuple: {key}"
            )
        values = tuple(sorted(configured))
        if not values or any(
            not isinstance(value, str) or not value
            for value in values
        ):
            raise StageRequirementError(
                f"Configuration contains invalid values: {key}"
            )
        return values

    def _require_security_core(self) -> None:
        health = self.security_core.health()
        if health.get("operational") is not True:
            raise StageRequirementError(
                "Security Core public interface is not operational."
            )

    def _require_security_receipt(
        self,
        receipt: dict[str, object],
        *,
        organization_id: str,
        assignment_type: str,
    ) -> None:
        if not isinstance(receipt, dict):
            raise StageRequirementError(
                "Security Core returned an invalid receipt."
            )
        if (
            receipt.get("status") != "Assigned"
            or receipt.get("organization_id") != organization_id
            or receipt.get("assignment_type") != assignment_type
            or not isinstance(receipt.get("receipt_id"), str)
        ):
            raise StageRequirementError(
                "Security Core receipt failed validation."
            )

    def _publish_transition(
        self,
        stage: StageDefinition,
        transition: dict[str, object],
        *,
        success: bool,
    ) -> None:
        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type=(
                    self.EVENT_STAGE_COMPLETED
                    if success
                    else self.EVENT_STAGE_FAILED
                ),
                message=(
                    f"{stage.code} {stage.name} "
                    f"{'completed' if success else 'failed'}."
                ),
                severity="INFO" if success else "ERROR",
                payload=transition,
            )
        )

    @staticmethod
    def _safe_failure_reason(error: Exception) -> str:
        if isinstance(error, CustomerPipelineError):
            return str(error)
        return (
            "Stage execution failed closed: "
            f"{type(error).__name__}: {error}"
        )
