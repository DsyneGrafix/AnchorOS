import contextlib
from copy import deepcopy
import io
import unittest

from core.boot_pipeline import BootPipeline
from core.service_registry import ServiceRegistry
from pipelines.customer_onboarding import (
    CUSTOMER_PIPELINE_STAGES,
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
from services.security_core import SecurityCore


class CustomerPipelineTestCase(unittest.TestCase):
    def build_engine(
        self,
        *,
        security_operational=True,
        healthy_frameworks=True,
        boot_verified=True,
    ):
        audit = Audit()
        event_bus = EventBus()
        configuration = Configuration(
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
        manifest = PlatformManifest()
        health = Health()
        services = (
            audit,
            event_bus,
            configuration,
            manifest,
            health,
        )
        registry = ServiceRegistry()
        for service in services:
            service.start()
            registry.register(service)
            manifest.register_service(service.name)
        for framework in ("AnchorFiber", "AnchorStack"):
            manifest.register_framework(framework)
            if healthy_frameworks:
                health.handle_framework_started(
                    AnchorEvent(
                        source=framework,
                        event_type="framework.started",
                        message="Test framework is Running.",
                    )
                )

        boot_pipeline = BootPipeline()
        with contextlib.redirect_stdout(io.StringIO()):
            boot_pipeline.execute()
        if not boot_verified:
            boot_pipeline.results[4].success = False

        security_core = SecurityCore.from_registry(registry)
        registry.register(security_core)
        manifest.register_service(security_core.name)
        security_core.start()
        if not security_operational:
            security_core.stop()
        engine = CustomerPipelineEngine.from_registry(
            registry=registry,
            boot_pipeline=boot_pipeline,
            security_core=security_core,
        )
        engine.start()
        return engine, audit, configuration

    @staticmethod
    def request(**overrides):
        values = {
            "onboarding_id": "CO-TEST-001",
            "organization_name": "Northstar Infrastructure",
            "organization_slug": "northstar-infrastructure",
            "primary_identity_id": "identity:northstar-admin",
            "requested_roles": ("OrganizationAdmin",),
            "license_id": "AOS-DEVELOPER",
            "frameworks": ("AnchorFiber", "AnchorStack"),
            "security_policy_id": "AOS-POLICY-BASELINE",
            "deployment_environment": "sandbox",
        }
        values.update(overrides)
        return OnboardingRequest(**values)

    def test_stage_definitions_form_one_complete_chain(self):
        self.assertEqual(len(CUSTOMER_PIPELINE_STAGES), 9)
        self.assertEqual(
            [stage.code for stage in CUSTOMER_PIPELINE_STAGES],
            [f"CP-{number:03d}" for number in range(1, 10)],
        )
        for current, following in zip(
            CUSTOMER_PIPELINE_STAGES,
            CUSTOMER_PIPELINE_STAGES[1:],
        ):
            self.assertIs(current.exit_state, following.entry_state)
            self.assertTrue(current.purpose)
            self.assertTrue(current.entry_criteria)
            self.assertTrue(current.exit_criteria)

    def test_successful_pipeline_is_operational_and_replayable(self):
        engine, audit, _ = self.build_engine()
        record = engine.execute(self.request())

        self.assertIs(record.state, CustomerState.OPERATIONAL)
        self.assertEqual(len(record.transitions), 9)
        self.assertTrue(engine.verify_record(record))
        self.assertEqual(record.transitions[-1].stage_code, "CP-009")
        self.assertEqual(record.artifacts["CP-008"]["status"], "PASS")
        self.assertEqual(
            record.artifacts["CP-007"]["action"],
            "PrepareOnly",
        )
        self.assertFalse(
            record.artifacts["CP-004"]["commercial_transaction"]
        )

        stage_audits = [
            item
            for item in audit.get_records()
            if item["event_type"]
            == engine.EVENT_STAGE_COMPLETED
        ]
        self.assertEqual(len(stage_audits), 9)
        self.assertEqual(
            [item["payload"]["stage_code"] for item in stage_audits],
            [f"CP-{number:03d}" for number in range(1, 10)],
        )

        replay = engine.replay(record.onboarding_id)
        self.assertTrue(replay.verified)
        self.assertEqual(replay.expected_hash, replay.actual_hash)
        self.assertEqual(replay.actual_transitions, 9)
        self.assertEqual(
            audit.get_records()[-1]["event_type"],
            engine.EVENT_REPLAY_VERIFIED,
        )

    def test_unconfigured_license_fails_closed_at_cp_004(self):
        engine, audit, _ = self.build_engine()
        record = engine.execute(
            self.request(license_id="AOS-UNKNOWN")
        )

        self.assertIs(record.state, CustomerState.FAILED)
        self.assertIs(
            record.last_successful_state,
            CustomerState.IDENTITY_ASSIGNED,
        )
        self.assertEqual(record.failed_stage, "CP-004")
        self.assertEqual(len(record.transitions), 4)
        self.assertNotIn("CP-005", record.artifacts)
        self.assertTrue(engine.verify_record(record))
        self.assertEqual(
            audit.get_records()[-1]["event_type"],
            engine.EVENT_STAGE_FAILED,
        )

    def test_security_core_unavailability_fails_closed_at_cp_003(self):
        engine, _, _ = self.build_engine(
            security_operational=False
        )
        record = engine.execute(self.request())

        self.assertIs(record.state, CustomerState.FAILED)
        self.assertEqual(record.failed_stage, "CP-003")
        self.assertIs(
            record.last_successful_state,
            CustomerState.PROVISIONED,
        )
        self.assertIn("not operational", record.failure_reason)

    def test_unhealthy_framework_fails_closed_at_cp_005(self):
        engine, _, _ = self.build_engine(
            healthy_frameworks=False
        )
        record = engine.execute(self.request())

        self.assertIs(record.state, CustomerState.FAILED)
        self.assertEqual(record.failed_stage, "CP-005")
        self.assertIn("not Running", record.failure_reason)
        self.assertNotIn("CP-006", record.artifacts)

    def test_boot_pipeline_failure_prevents_validation(self):
        engine, _, _ = self.build_engine(boot_verified=False)
        record = engine.execute(self.request())

        self.assertIs(record.state, CustomerState.FAILED)
        self.assertEqual(record.failed_stage, "CP-008")
        self.assertIs(
            record.last_successful_state,
            CustomerState.DEPLOYMENT_PREPARED,
        )
        self.assertNotIn("CP-009", record.artifacts)

    def test_transition_evidence_detects_tampering(self):
        engine, _, _ = self.build_engine()
        record = engine.execute(self.request())
        tampered = deepcopy(record)
        tampered.transitions[0].details["organization_name"] = (
            "Changed Organization"
        )

        self.assertFalse(engine.verify_record(tampered))
        self.assertTrue(engine.verify_record(record))

        artifact_tampered = deepcopy(record)
        artifact_tampered.artifacts["CP-004"]["license_id"] = (
            "AOS-ENTERPRISE"
        )
        self.assertFalse(engine.verify_record(artifact_tampered))

    def test_invalid_security_receipt_fails_closed_at_cp_006(self):
        engine, _, _ = self.build_engine()

        def invalid_policy_receipt(**kwargs):
            return {
                "organization_id": kwargs["organization_id"],
                "assignment_type": "security_policy",
                "status": "Assigned",
            }

        engine.security_core.assign_policy = invalid_policy_receipt
        record = engine.execute(self.request())

        self.assertIs(record.state, CustomerState.FAILED)
        self.assertEqual(record.failed_stage, "CP-006")
        self.assertIn("receipt failed", record.failure_reason)
        self.assertNotIn("CP-007", record.artifacts)

    def test_duplicate_registration_does_not_replace_valid_record(self):
        engine, _, _ = self.build_engine()
        first = engine.execute(self.request())
        duplicate = engine.execute(self.request())
        stored = engine.get_record(first.onboarding_id)

        self.assertIs(first.state, CustomerState.OPERATIONAL)
        self.assertIs(duplicate.state, CustomerState.FAILED)
        self.assertEqual(duplicate.failed_stage, "CP-001")
        self.assertIs(stored.state, CustomerState.OPERATIONAL)
        self.assertEqual(stored.final_hash, first.final_hash)

    def test_configuration_service_fails_closed_for_missing_values(self):
        configuration = Configuration({"present": "value"})
        self.assertEqual(configuration.get("present"), "value")
        self.assertEqual(configuration.get("missing", "fallback"), "fallback")
        with self.assertRaises(RuntimeError):
            configuration.require("missing")


if __name__ == "__main__":
    unittest.main()
