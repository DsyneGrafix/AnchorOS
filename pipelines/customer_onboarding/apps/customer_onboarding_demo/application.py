"""Runnable demonstration of the Customer Onboarding Pipeline."""

from __future__ import annotations

from core.boot_pipeline import BootPipeline
from core.service_registry import ServiceRegistry
from pipelines.customer_onboarding import (
    CustomerPipelineEngine,
    OnboardingRequest,
)
from services.audit import Audit
from services.configuration import Configuration
from services.event import AnchorEvent
from services.eventbus import EventBus
from services.health import Health
from services.manifest import PlatformManifest

from .security_adapter import DemonstrationSecurityCore


class CustomerOnboardingDemo:
    """Wire the pipeline to real Platform Services and a security stub."""

    def __init__(self) -> None:
        self.audit = Audit()
        self.event_bus = EventBus()
        self.configuration = Configuration(
            {
                "customer_pipeline.allowed_licenses": (
                    "AOS-DEVELOPER",
                    "AOS-ENTERPRISE",
                ),
                "customer_pipeline.allowed_environments": (
                    "sandbox",
                    "production",
                ),
                "customer_pipeline.required_platform_services": (
                    "Audit Engine",
                    "Configuration",
                    "Event Bus",
                    "Health Monitor",
                    "Platform Manifest",
                ),
            }
        )
        self.manifest = PlatformManifest()
        self.health = Health()
        self.boot_pipeline = BootPipeline()
        self.security_core = DemonstrationSecurityCore()
        self.registry = ServiceRegistry()

        self.services = (
            self.audit,
            self.event_bus,
            self.configuration,
            self.manifest,
            self.health,
        )
        for service in self.services:
            service.start()
            self.registry.register(service)
            self.manifest.register_service(service.name)

        self.event_bus.subscribe(
            "framework.started",
            self.health.handle_framework_started,
        )
        for framework in ("AnchorFiber", "AnchorStack"):
            self.manifest.register_framework(framework)
            self.event_bus.publish(
                AnchorEvent(
                    source=framework,
                    event_type="framework.started",
                    message=f"{framework} is Running for demonstration.",
                )
            )

        self.boot_pipeline.execute()
        self.engine = CustomerPipelineEngine.from_registry(
            registry=self.registry,
            boot_pipeline=self.boot_pipeline,
            security_core=self.security_core,
        )
        self.engine.start()

    def run(self) -> tuple[dict[str, object], dict[str, object]]:
        request = OnboardingRequest(
            onboarding_id="CO-000001",
            organization_name="Northstar Infrastructure",
            organization_slug="northstar-infrastructure",
            primary_identity_id="identity:northstar-admin",
            requested_roles=("OrganizationAdmin",),
            license_id="AOS-DEVELOPER",
            frameworks=("AnchorFiber", "AnchorStack"),
            security_policy_id="AOS-POLICY-BASELINE",
            deployment_environment="sandbox",
        )
        record = self.engine.execute(request)
        replay = self.engine.replay(request.onboarding_id)
        return record.to_dict(), replay.to_dict()
