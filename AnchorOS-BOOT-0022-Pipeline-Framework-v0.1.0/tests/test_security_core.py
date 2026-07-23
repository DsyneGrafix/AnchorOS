"""BOOT-0021 Security Core verification tests."""

import contextlib
from copy import deepcopy
import io
import unittest

from core.boot_pipeline import BootPipeline
from core.service_registry import ServiceRegistry
from pipelines.customer_onboarding import (
    CustomerPipelineEngine,
    CustomerState,
    OnboardingRequest,
)
from services.audit import Audit
from services.configuration import Configuration
from services.event import AnchorEvent
from services.eventbus import EventBus
from services.health import Health
from services.manifest import PlatformManifest
from services.security_core import SecurityCore, SecurityState


class SecurityCoreTestCase(unittest.TestCase):
    def setUp(self):
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()

    def tearDown(self):
        self.output.__exit__(None, None, None)

    def build_core(
        self,
        *,
        include_manifest=True,
        configuration_overrides=None,
        start=True,
    ):
        registry = ServiceRegistry()
        audit = Audit()
        event_bus = EventBus()
        configuration = Configuration(configuration_overrides)
        health = Health()
        manifest = PlatformManifest()
        services = [audit, event_bus, configuration, health]
        if include_manifest:
            services.append(manifest)
        for service in services:
            service.start()
            registry.register(service)
            manifest.register_service(service.name)
        core = SecurityCore.from_registry(registry)
        registry.register(core)
        if start:
            core.start()
        return core, registry, audit, configuration, manifest, health

    @staticmethod
    def roles(core, *, key="test:roles", roles=("OrganizationAdmin",)):
        return core.assign_identity_and_roles(
            organization_id="ORG-TEST001",
            identity_id="identity:test-admin",
            roles=roles,
            idempotency_key=key,
        )

    def test_refuses_start_without_required_platform_service(self):
        core, _, audit, _, _, _ = self.build_core(
            include_manifest=False,
            start=False,
        )
        with self.assertRaises(RuntimeError):
            core.start()
        self.assertIs(core.lifecycle.state, SecurityState.FAILED)
        self.assertFalse(core.health()["operational"])
        self.assertEqual(core.get_receipts()[-1]["outcome"], "FAIL")
        self.assertEqual(audit.get_records()[-1]["event_type"], core.EVENT_OPERATION_FAILED)

    def test_refuses_start_with_invalid_configuration(self):
        core, _, _, _, _, _ = self.build_core(
            configuration_overrides={"security_core.allowed_roles": ()},
            start=False,
        )
        with self.assertRaises(RuntimeError):
            core.start()
        self.assertEqual(core.get_receipts()[-1]["reason_code"], "INVALID_CONFIGURATION")

    def test_valid_identity_registration_and_duplicate_are_idempotent(self):
        core, _, _, _, _, _ = self.build_core()
        first = core.register_identity(
            organization_id="ORG-TEST001",
            identity_id="identity:test-admin",
            idempotency_key="test:identity",
        )
        second = core.register_identity(
            organization_id="ORG-TEST001",
            identity_id="identity:test-admin",
            idempotency_key="test:identity",
        )
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "Registered")
        self.assertEqual(len(core.get_receipts()), 1)

    def test_valid_role_assignment_is_scoped_and_audited(self):
        core, _, audit, _, _, _ = self.build_core()
        receipt = self.roles(core)
        self.assertEqual(receipt["status"], "Assigned")
        self.assertEqual(receipt["assignment_type"], "identity_roles")
        self.assertEqual(receipt["organization_id"], "ORG-TEST001")
        events = [record["event_type"] for record in audit.get_records()]
        self.assertIn(core.EVENT_IDENTITY_REGISTERED, events)
        self.assertIn(core.EVENT_ROLES_ASSIGNED, events)

    def test_unconfigured_role_fails_closed_and_is_audited(self):
        core, _, audit, _, _, _ = self.build_core()
        receipt = self.roles(core, roles=("RootSuperuser",))
        self.assertEqual(receipt["outcome"], "FAIL")
        self.assertEqual(receipt["status"], "Rejected")
        self.assertEqual(receipt["reason_code"], "VALUE_NOT_CONFIGURED")
        self.assertEqual(audit.get_records()[-1]["event_type"], core.EVENT_OPERATION_FAILED)

    def test_valid_and_unconfigured_policy_assignments(self):
        core, _, audit, _, _, _ = self.build_core()
        valid = core.assign_policy(
            organization_id="ORG-TEST001",
            policy_id="AOS-POLICY-BASELINE",
            idempotency_key="test:policy",
        )
        invalid = core.assign_policy(
            organization_id="ORG-TEST002",
            policy_id="CUSTOM-POLICY",
            idempotency_key="test:bad-policy",
        )
        self.assertEqual(valid["status"], "Assigned")
        self.assertEqual(valid["assignment_type"], "security_policy")
        self.assertEqual(invalid["outcome"], "FAIL")
        self.assertEqual(audit.get_records()[-1]["event_type"], core.EVENT_OPERATION_FAILED)

    def test_authorization_allows_assigned_role(self):
        core, _, _, _, _, _ = self.build_core()
        self.roles(core)
        decision = core.authorize(
            organization_id="ORG-TEST001",
            identity_id="identity:test-admin",
            required_role="OrganizationAdmin",
        )
        self.assertEqual(decision["status"], "ALLOW")
        self.assertEqual(decision["reason_code"], "REQUIRED_ROLE_ASSIGNED")

    def test_authorization_denies_missing_role(self):
        core, _, _, _, _, _ = self.build_core()
        self.roles(core)
        decision = core.authorize(
            organization_id="ORG-TEST001",
            identity_id="identity:test-admin",
            required_role="SecurityReviewer",
        )
        self.assertEqual(decision["status"], "DENY")
        self.assertEqual(decision["reason_code"], "REQUIRED_ROLE_NOT_ASSIGNED")

    def test_unknown_identity_authorization_defaults_to_deny(self):
        core, _, _, _, _, _ = self.build_core()
        decision = core.authorize(
            organization_id="ORG-TEST001",
            identity_id="identity:unknown",
            required_role="OrganizationAdmin",
        )
        self.assertEqual(decision["status"], "DENY")
        self.assertEqual(decision["reason_code"], "UNKNOWN_IDENTITY")

    def test_identical_idempotent_assignment_returns_same_receipt(self):
        core, _, _, _, _, _ = self.build_core()
        first = self.roles(core)
        second = self.roles(core)
        self.assertEqual(first["receipt_id"], second["receipt_id"])
        self.assertEqual(first["receipt_hash"], second["receipt_hash"])
        self.assertEqual(len(core.get_receipts()), 1)

    def test_fresh_engines_produce_identical_assignment_evidence(self):
        first, _, _, _, _, _ = self.build_core()
        second, _, _, _, _, _ = self.build_core()
        first_receipt = self.roles(first)
        second_receipt = self.roles(second)
        self.assertEqual(first_receipt, second_receipt)

    def test_conflicting_idempotency_key_reuse_fails_closed(self):
        core, _, audit, _, _, _ = self.build_core()
        first = self.roles(core)
        conflict = self.roles(
            core,
            roles=("SecurityReviewer",),
        )
        self.assertEqual(first["outcome"], "PASS")
        self.assertEqual(conflict["outcome"], "FAIL")
        self.assertEqual(conflict["reason_code"], "IDEMPOTENCY_CONFLICT")
        self.assertEqual(audit.get_records()[-1]["event_type"], core.EVENT_OPERATION_FAILED)

    def test_receipt_and_chain_verification_detect_tampering(self):
        core, _, _, _, _, _ = self.build_core()
        self.roles(core)
        core.assign_policy(
            organization_id="ORG-TEST001",
            policy_id="AOS-POLICY-BASELINE",
            idempotency_key="test:policy",
        )
        receipts = core.repositories.receipts.list_all()
        self.assertTrue(core.verify_evidence_chain(receipts))
        tampered = deepcopy(receipts)
        tampered[0].requested_value = ("SecurityReviewer",)
        self.assertFalse(core.verify_receipt(tampered[0]))
        self.assertFalse(core.verify_evidence_chain(tampered))

    def test_deterministic_replay_verifies(self):
        core, _, audit, _, _, _ = self.build_core()
        receipt = self.roles(core)
        replay = core.replay(receipt["receipt_id"])
        self.assertTrue(replay.verified)
        self.assertEqual(replay.expected_hash, replay.actual_hash)
        self.assertEqual(audit.get_records()[-1]["event_type"], core.EVENT_REPLAY_VERIFIED)
        self.assertTrue(core.verify_evidence_chain())

    def test_stopped_or_invalid_operations_fail_closed_with_receipts(self):
        core, _, audit, _, _, _ = self.build_core()
        core.stop()
        unavailable = self.roles(core)
        invalid = core.assign_policy(
            organization_id="not-an-organization",
            policy_id="AOS-POLICY-BASELINE",
            idempotency_key="test:invalid-org",
        )
        self.assertEqual(unavailable["outcome"], "FAIL")
        self.assertEqual(unavailable["reason_code"], "SERVICE_UNAVAILABLE")
        self.assertEqual(invalid["outcome"], "FAIL")
        failures = [
            record for record in audit.get_records()
            if record["event_type"] == core.EVENT_OPERATION_FAILED
        ]
        self.assertEqual(len(failures), 2)

    def test_unexpected_exception_becomes_safe_failure_receipt(self):
        core, _, audit, _, _, _ = self.build_core()

        def unexpected(*args, **kwargs):
            raise RuntimeError("internal-sensitive-detail")

        core._require_configured = unexpected
        receipt = self.roles(core)
        self.assertEqual(receipt["outcome"], "FAIL")
        self.assertEqual(receipt["reason_code"], "INTERNAL_ERROR")
        self.assertNotIn("internal-sensitive-detail", receipt["result"]["message"])
        self.assertNotIn(
            "internal-sensitive-detail",
            str(audit.get_records()[-1]["payload"]),
        )

    def test_malformed_non_json_input_still_generates_failure_receipt(self):
        core, _, audit, _, _, _ = self.build_core()
        receipt = core.assign_identity_and_roles(
            organization_id="ORG-TEST001",
            identity_id="identity:test-admin",
            roles=("OrganizationAdmin", object()),
            idempotency_key="test:malformed",
        )
        self.assertEqual(receipt["outcome"], "FAIL")
        self.assertEqual(receipt["requested_value"], "<invalid>")
        self.assertEqual(audit.get_records()[-1]["event_type"], core.EVENT_OPERATION_FAILED)

    def test_customer_pipeline_completes_with_real_security_core(self):
        core, registry, _, configuration, manifest, health = self.build_core()
        configuration.set(
            "customer_pipeline.allowed_licenses",
            ("AOS-DEVELOPER",),
        )
        configuration.set(
            "customer_pipeline.allowed_environments",
            ("sandbox",),
        )
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
        event_bus = registry.require("Event Bus")
        for framework in ("AnchorFiber", "AnchorStack"):
            manifest.register_framework(framework)
            health.handle_framework_started(
                AnchorEvent(
                    source=framework,
                    event_type="framework.started",
                    message="Test framework is Running.",
                )
            )
        boot_pipeline = BootPipeline()
        boot_pipeline.execute()
        engine = CustomerPipelineEngine.from_registry(
            registry=registry,
            boot_pipeline=boot_pipeline,
            security_core=core,
        )
        engine.start()
        record = engine.execute(
            OnboardingRequest(
                onboarding_id="CO-SC-001",
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
        replay = engine.replay(record.onboarding_id)
        self.assertIs(record.state, CustomerState.OPERATIONAL)
        self.assertEqual(record.artifacts["CP-003"]["assignment_type"], "identity_roles")
        self.assertEqual(record.artifacts["CP-006"]["assignment_type"], "security_policy")
        self.assertTrue(replay.verified)
        self.assertTrue(core.verify_evidence_chain())
        self.assertIs(event_bus, core.event_bus)

    def test_existing_boot_pipeline_remains_eight_stage_pass(self):
        pipeline = BootPipeline()
        results = pipeline.execute()
        self.assertEqual(len(results), 8)
        self.assertTrue(pipeline.summary())
        self.assertTrue(all(result.success for result in results))


if __name__ == "__main__":
    unittest.main()
