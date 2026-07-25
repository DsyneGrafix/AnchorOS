"""End-to-end BOOT-0021 demonstration using real AnchorOS services."""

from __future__ import annotations

from core.boot_pipeline import BootPipeline
from core.module_manager import ModuleManager
from core.service_registry import ServiceRegistry
from pipelines.customer_onboarding import CustomerPipelineEngine, OnboardingRequest
from services.audit import Audit
from services.configuration import Configuration
from services.eventbus import EventBus
from services.health import Health
from services.manifest import PlatformManifest
from services.security_core import SecurityCore


class SecurityCoreDemo:
    """Boot services, exercise Security Core, then complete CP-001."""

    def __init__(self) -> None:
        self.manager = ModuleManager()
        self.registry = ServiceRegistry()
        self.boot_pipeline = BootPipeline()

    def boot(self) -> None:
        services = self.manager.discover("services", context=self.registry)
        for service in services:
            self.registry.register(service)

        audit = self.registry.require("Audit Engine")
        event_bus = self.registry.require("Event Bus")
        configuration = self.registry.require("Configuration")
        health = self.registry.require("Health Monitor")
        manifest = self.registry.require("Platform Manifest")
        if not all(
            (
                isinstance(audit, Audit),
                isinstance(event_bus, EventBus),
                isinstance(configuration, Configuration),
                isinstance(health, Health),
                isinstance(manifest, PlatformManifest),
            )
        ):
            raise RuntimeError("Demonstration received invalid Platform Services.")

        for service_name in self.registry.list_services():
            manifest.register_service(service_name)
        event_bus.subscribe("framework.started", audit.handle_event)
        event_bus.subscribe("framework.started", health.handle_framework_started)
        event_bus.subscribe("framework.stopping", audit.handle_event)

        frameworks = self.manager.discover("frameworks", context=self.registry)
        for framework in frameworks:
            manifest.register_framework(framework.name)
        manifest.register_application("Security Core Demonstration")

        configuration.set("customer_pipeline.allowed_licenses", ("AOS-DEVELOPER",))
        configuration.set("customer_pipeline.allowed_environments", ("sandbox",))
        configuration.set(
            "customer_pipeline.required_platform_services",
            (
                "Audit Engine",
                "Configuration",
                "Event Bus",
                "Health Monitor",
                "Platform Manifest",
            ),
        )
        self.manager.start_all()
        results = self.boot_pipeline.execute()
        if len(results) != 8 or not self.boot_pipeline.summary():
            raise RuntimeError("AnchorOS Boot Pipeline did not verify.")

    def run(self) -> dict[str, object]:
        self.boot()
        core = self.registry.require("Security Core")
        if not isinstance(core, SecurityCore):
            raise RuntimeError("Security Core did not resolve through ServiceRegistry.")

        identity = core.register_identity(
            organization_id="ORG-DEMO001",
            identity_id="identity:demo-admin",
            idempotency_key="security-demo:identity",
        )
        roles = core.assign_identity_and_roles(
            organization_id="ORG-DEMO001",
            identity_id="identity:demo-admin",
            roles=("OrganizationAdmin",),
            idempotency_key="security-demo:roles",
        )
        policy = core.assign_policy(
            organization_id="ORG-DEMO001",
            policy_id="AOS-POLICY-BASELINE",
            idempotency_key="security-demo:policy",
        )
        allowed = core.authorize(
            organization_id="ORG-DEMO001",
            identity_id="identity:demo-admin",
            required_role="OrganizationAdmin",
        )
        denied = core.authorize(
            organization_id="ORG-DEMO001",
            identity_id="identity:demo-admin",
            required_role="SecurityReviewer",
        )
        replay = core.replay(roles["receipt_id"])

        customer_pipeline = CustomerPipelineEngine.from_registry(
            registry=self.registry,
            boot_pipeline=self.boot_pipeline,
            security_core=core,
        )
        customer_pipeline.start()
        customer = customer_pipeline.execute(
            OnboardingRequest(
                onboarding_id="CO-DEMO-0021",
                organization_name="Northstar Infrastructure",
                organization_slug="northstar-infrastructure",
                primary_identity_id="identity:northstar-admin",
                requested_roles=("OrganizationAdmin",),
                license_id="AOS-DEVELOPER",
                frameworks=("AnchorFiber", "AnchorStack"),
                security_policy_id="AOS-POLICY-BASELINE",
                deployment_environment="sandbox",
            )
        )
        customer_replay = customer_pipeline.replay(customer.onboarding_id)
        return {
            "platform_boot": self.registry.require("Platform Manifest").describe()["boot"],
            "security_health": core.health(),
            "identity_receipt": identity,
            "role_receipt": roles,
            "policy_receipt": policy,
            "allow_decision": allowed,
            "deny_decision": denied,
            "evidence_chain_verified": core.verify_evidence_chain(),
            "security_replay": replay.to_dict(),
            "customer_state": customer.state.value,
            "customer_final_hash": customer.final_hash,
            "customer_replay": customer_replay.to_dict(),
            "verified_operational": (
                core.health()["operational"] is True
                and customer.state.value == "Operational"
                and customer_replay.verified
            ),
        }
