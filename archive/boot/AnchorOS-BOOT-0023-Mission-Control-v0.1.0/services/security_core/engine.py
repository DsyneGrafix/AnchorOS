"""Authoritative, bounded Security Core Platform Service for BOOT-0021."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from core.module import Module
from core.service_registry import ServiceRegistry
from services.audit import Audit
from services.configuration import Configuration
from services.event import AnchorEvent
from services.eventbus import EventBus
from services.health import Health
from services.manifest import PlatformManifest

from .errors import (
    EvidenceVerificationError,
    IdempotencyConflictError,
    SecurityConfigurationError,
    SecurityCoreError,
    SecurityUnavailableError,
    SecurityValidationError,
)
from .lifecycle import SecurityLifecycle
from .models import (
    AuthorizationDecision,
    IdentityRecord,
    PolicyAssignmentRecord,
    RecordStatus,
    ReplayResult,
    RoleAssignmentRecord,
    SecurityReceipt,
    SecurityState,
    canonical_hash,
)
from .policy import decide_role_authorization
from .receipts import ReceiptService
from .repositories import SecurityRepositories


class SecurityCore(Module):
    """
    Narrow security assignment and decision service.

    This service stores only organization-scoped identity metadata, roles,
    policies, idempotency evidence, and receipts. It does not authenticate
    credentials, issue tokens, manage secrets, or contact identity providers.
    """

    VERSION = "0.1.0"
    REQUIRED_SERVICES = (
        "Audit Engine",
        "Event Bus",
        "Configuration",
        "Health Monitor",
        "Platform Manifest",
    )

    EVENT_STARTED = "security_core.started"
    EVENT_IDENTITY_REGISTERED = "security_core.identity.registered"
    EVENT_ROLES_ASSIGNED = "security_core.roles.assigned"
    EVENT_POLICY_ASSIGNED = "security_core.policy.assigned"
    EVENT_AUTHORIZATION_ALLOWED = "security_core.authorization.allowed"
    EVENT_AUTHORIZATION_DENIED = "security_core.authorization.denied"
    EVENT_OPERATION_FAILED = "security_core.operation.failed"
    EVENT_REPLAY_VERIFIED = "security_core.replay.verified"
    EVENT_REPLAY_FAILED = "security_core.replay.failed"

    _ORGANIZATION_PATTERN = re.compile(r"ORG-[A-Z0-9][A-Z0-9-]{2,63}")
    _IDENTITY_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9:._@/+-]{2,127}")
    _CONFIGURED_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9:._-]{1,127}")

    def __init__(
        self,
        *,
        registry: ServiceRegistry,
        repositories: SecurityRepositories | None = None,
    ) -> None:
        super().__init__("Security Core", self.VERSION)
        self.registry = registry
        self.repositories = repositories or SecurityRepositories()
        self.receipts = ReceiptService(self.repositories.receipts)
        self.lifecycle = SecurityLifecycle()
        self.audit: Audit | None = None
        self.event_bus: EventBus | None = None
        self.configuration: Configuration | None = None
        self.health_monitor: Health | None = None
        self.manifest: PlatformManifest | None = None
        self._subscribed = False

    @classmethod
    def from_registry(
        cls,
        registry: ServiceRegistry,
        *,
        repositories: SecurityRepositories | None = None,
    ) -> SecurityCore:
        return cls(registry=registry, repositories=repositories)

    def start(self) -> None:
        """Resolve authoritative dependencies and fail closed on any gap."""

        if self.lifecycle.state is SecurityState.OPERATIONAL:
            return
        try:
            self.lifecycle.transition(SecurityState.INITIALIZING)
            configuration = self.registry.require("Configuration")
            if not isinstance(configuration, Configuration):
                raise SecurityConfigurationError(
                    "Security Core requires the Configuration service."
                )
            configured = self._validated_configured_values(
                configuration,
                "security_core.required_platform_services",
            )
            available_audit = self.registry.get("Audit Engine")
            available_event_bus = self.registry.get("Event Bus")
            if (
                isinstance(available_audit, Audit)
                and isinstance(available_event_bus, EventBus)
                and available_audit.status == "Running"
                and available_event_bus.status == "Running"
            ):
                self.audit = available_audit
                self.event_bus = available_event_bus
                self._subscribe_audit()
            missing_mandatory = sorted(set(self.REQUIRED_SERVICES) - set(configured))
            if missing_mandatory:
                raise SecurityConfigurationError(
                    "Security Core required-service configuration omits: "
                    + ", ".join(missing_mandatory)
                )

            resolved = {name: self.registry.require(name) for name in configured}
            expected_types = {
                "Audit Engine": Audit,
                "Event Bus": EventBus,
                "Configuration": Configuration,
                "Health Monitor": Health,
                "Platform Manifest": PlatformManifest,
            }
            invalid = sorted(
                name
                for name, expected in expected_types.items()
                if not isinstance(resolved.get(name), expected)
            )
            if invalid:
                raise SecurityUnavailableError(
                    "Security Core received invalid Platform Services: "
                    + ", ".join(invalid)
                )
            unavailable = sorted(
                name
                for name, service in resolved.items()
                if service.status != "Running"
            )
            if unavailable:
                raise SecurityUnavailableError(
                    "Security Core requires running Platform Services: "
                    + ", ".join(unavailable)
                )

            self.audit = resolved["Audit Engine"]
            self.event_bus = resolved["Event Bus"]
            self.configuration = resolved["Configuration"]
            self.health_monitor = resolved["Health Monitor"]
            self.manifest = resolved["Platform Manifest"]
            self._validate_operating_configuration()
            self._subscribe_audit()
            self.manifest.register_service(self.name)
            super().start()
            self.lifecycle.transition(SecurityState.OPERATIONAL)
            self._publish(
                self.EVENT_STARTED,
                "Security Core entered the Operational state.",
                payload={"service": self.name, "version": self.version},
            )
        except Exception as error:
            self.lifecycle.force_failed()
            self.status = "Offline"
            self._issue_failure(
                operation="start",
                raw_input={"service": self.name},
                error=error,
            )
            raise RuntimeError(
                "Security Core initialization failed closed: "
                + self._safe_error_message(error)
            ) from error

    def stop(self) -> None:
        if self.lifecycle.state is not SecurityState.STOPPED:
            if self.lifecycle.state in {
                SecurityState.UNINITIALIZED,
                SecurityState.OPERATIONAL,
                SecurityState.DEGRADED,
                SecurityState.FAILED,
            }:
                self.lifecycle.transition(SecurityState.STOPPED)
        super().stop()

    def health(self) -> dict[str, object]:
        dependency_status = self._dependency_status()
        dependencies_running = bool(dependency_status) and all(
            value == "Running" for value in dependency_status.values()
        )
        if (
            self.lifecycle.state is SecurityState.OPERATIONAL
            and not dependencies_running
        ):
            self.lifecycle.transition(SecurityState.DEGRADED)
        elif (
            self.lifecycle.state is SecurityState.DEGRADED
            and dependencies_running
            and self.status == "Running"
        ):
            self.lifecycle.transition(SecurityState.OPERATIONAL)
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "state": self.lifecycle.state.value,
            "operational": (
                self.status == "Running"
                and self.lifecycle.state is SecurityState.OPERATIONAL
                and dependencies_running
            ),
            "dependencies": dependency_status,
            "receipt_count": len(self.repositories.receipts.list_all()),
            "storage": "in-memory",
        }

    def register_identity(
        self,
        *,
        organization_id: str,
        identity_id: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        raw = {
            "operation": "register_identity",
            "organization_id": organization_id,
            "identity_id": identity_id,
            "idempotency_key": idempotency_key,
        }
        try:
            normalized = self._normalize_identity_input(raw)
            self._ensure_operational()
            existing = self._idempotent_result(normalized)
            if existing is not None:
                return existing
            prior = self._identity_role_state(organization_id, identity_id)
            self.repositories.identities.save(
                IdentityRecord(organization_id, identity_id)
            )
            resulting = self._identity_role_state(organization_id, identity_id)
            result = {
                "organization_id": organization_id,
                "identity_id": identity_id,
                "status": RecordStatus.REGISTERED.value,
            }
            receipt = self._issue_success(
                operation="register_identity",
                normalized=normalized,
                prior=prior,
                resulting=resulting,
                result=result,
                requested_value=identity_id,
                organization_id=organization_id,
                identity_id=identity_id,
                assignment_type="identity_registration",
                status=RecordStatus.REGISTERED.value,
                reason_code="IDENTITY_REGISTERED",
            )
            self._store_idempotency(normalized, receipt)
            self._publish_receipt(
                self.EVENT_IDENTITY_REGISTERED,
                "Identity metadata registered for an organization.",
                receipt,
            )
            return receipt.to_dict()
        except Exception as error:
            return self._issue_failure(
                operation="register_identity",
                raw_input=raw,
                error=error,
                assignment_type="identity_registration",
            ).to_dict()

    def assign_identity_and_roles(
        self,
        *,
        organization_id: str,
        identity_id: str,
        roles: tuple[str, ...],
        idempotency_key: str,
    ) -> dict[str, object]:
        raw = {
            "operation": "assign_identity_and_roles",
            "organization_id": organization_id,
            "identity_id": identity_id,
            "roles": roles,
            "idempotency_key": idempotency_key,
        }
        try:
            normalized = self._normalize_role_input(raw)
            self._ensure_operational()
            self._require_configured("security_core.allowed_roles", normalized["roles"])
            existing = self._idempotent_result(normalized)
            if existing is not None:
                return existing
            prior = self._identity_role_state(organization_id, identity_id)
            identity_created = prior["identity"] is None
            if identity_created:
                self.repositories.identities.save(
                    IdentityRecord(organization_id, identity_id)
                )
            current_roles = tuple(prior.get("roles") or ())
            assigned_roles = tuple(sorted(set(current_roles) | set(normalized["roles"])))
            self.repositories.roles.save(
                RoleAssignmentRecord(
                    organization_id=organization_id,
                    identity_id=identity_id,
                    roles=assigned_roles,
                )
            )
            resulting = self._identity_role_state(organization_id, identity_id)
            result = {
                "organization_id": organization_id,
                "identity_id": identity_id,
                "assignment_type": "identity_roles",
                "roles": assigned_roles,
                "identity_registered": True,
                "status": RecordStatus.ASSIGNED.value,
            }
            receipt = self._issue_success(
                operation="assign_identity_and_roles",
                normalized=normalized,
                prior=prior,
                resulting=resulting,
                result=result,
                requested_value=normalized["roles"],
                organization_id=organization_id,
                identity_id=identity_id,
                assignment_type="identity_roles",
                status=RecordStatus.ASSIGNED.value,
                reason_code="ROLES_ASSIGNED",
            )
            self._store_idempotency(normalized, receipt)
            if identity_created:
                self._publish_receipt(
                    self.EVENT_IDENTITY_REGISTERED,
                    "Identity metadata registered during role assignment.",
                    receipt,
                )
            self._publish_receipt(
                self.EVENT_ROLES_ASSIGNED,
                "Configured roles assigned within an organization.",
                receipt,
            )
            return receipt.to_dict()
        except Exception as error:
            return self._issue_failure(
                operation="assign_identity_and_roles",
                raw_input=raw,
                error=error,
                assignment_type="identity_roles",
            ).to_dict()

    def assign_policy(
        self,
        *,
        organization_id: str,
        policy_id: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        raw = {
            "operation": "assign_policy",
            "organization_id": organization_id,
            "policy_id": policy_id,
            "idempotency_key": idempotency_key,
        }
        try:
            normalized = self._normalize_policy_input(raw)
            self._ensure_operational()
            self._require_configured(
                "security_core.allowed_policy_ids", (normalized["policy_id"],)
            )
            existing = self._idempotent_result(normalized)
            if existing is not None:
                return existing
            prior = self._policy_state(organization_id)
            self.repositories.policies.save(
                PolicyAssignmentRecord(organization_id, policy_id)
            )
            resulting = self._policy_state(organization_id)
            result = {
                "organization_id": organization_id,
                "assignment_type": "security_policy",
                "policy_id": policy_id,
                "status": RecordStatus.ASSIGNED.value,
            }
            receipt = self._issue_success(
                operation="assign_policy",
                normalized=normalized,
                prior=prior,
                resulting=resulting,
                result=result,
                requested_value=policy_id,
                organization_id=organization_id,
                identity_id=None,
                assignment_type="security_policy",
                status=RecordStatus.ASSIGNED.value,
                reason_code="POLICY_ASSIGNED",
            )
            self._store_idempotency(normalized, receipt)
            self._publish_receipt(
                self.EVENT_POLICY_ASSIGNED,
                "Configured security policy assigned to an organization.",
                receipt,
            )
            return receipt.to_dict()
        except Exception as error:
            return self._issue_failure(
                operation="assign_policy",
                raw_input=raw,
                error=error,
                assignment_type="security_policy",
            ).to_dict()

    def authorize(
        self,
        *,
        organization_id: str,
        identity_id: str,
        required_role: str,
    ) -> dict[str, object]:
        raw = {
            "operation": "authorize",
            "organization_id": organization_id,
            "identity_id": identity_id,
            "required_role": required_role,
        }
        try:
            normalized = self._normalize_authorization_input(raw)
            self._ensure_operational()
            configured = self._configured_values("security_core.allowed_roles")
            prior = self._identity_role_state(organization_id, identity_id)
            if required_role not in configured:
                decision = AuthorizationDecision.DENY
                reason_code = "ROLE_NOT_CONFIGURED"
            else:
                decision, reason_code = decide_role_authorization(
                    identity_registered=prior["identity"] is not None,
                    assigned_roles=tuple(prior.get("roles") or ()),
                    required_role=required_role,
                )
            result = {
                "organization_id": organization_id,
                "identity_id": identity_id,
                "required_role": required_role,
                "decision": decision.value,
                "reason_code": reason_code,
                "status": decision.value,
            }
            receipt = self._issue_success(
                operation="authorize",
                normalized=normalized,
                prior=prior,
                resulting=prior,
                result=result,
                requested_value=required_role,
                organization_id=organization_id,
                identity_id=identity_id,
                assignment_type=None,
                status=decision.value,
                reason_code=reason_code,
            )
            self._publish_receipt(
                self.EVENT_AUTHORIZATION_ALLOWED
                if decision is AuthorizationDecision.ALLOW
                else self.EVENT_AUTHORIZATION_DENIED,
                f"Authorization decision: {decision.value}.",
                receipt,
            )
            return receipt.to_dict()
        except Exception as error:
            receipt = self._issue_failure(
                operation="authorize",
                raw_input=raw,
                error=error,
                status=AuthorizationDecision.DENY.value,
            )
            self._publish_receipt(
                self.EVENT_AUTHORIZATION_DENIED,
                "Authorization failed closed with DENY.",
                receipt,
            )
            return receipt.to_dict()

    def verify_receipt(self, receipt: SecurityReceipt | dict[str, object]) -> bool:
        candidate = receipt
        if isinstance(receipt, dict):
            try:
                candidate = SecurityReceipt(**receipt)
            except (TypeError, ValueError):
                return False
        return isinstance(candidate, SecurityReceipt) and self.receipts.verify_receipt(candidate)

    def verify_evidence_chain(
        self,
        receipts: list[SecurityReceipt] | None = None,
    ) -> bool:
        return self.receipts.verify_chain(receipts)

    def replay(self, receipt_id: str) -> ReplayResult:
        target = self.repositories.receipts.get(receipt_id)
        if target is None:
            raise KeyError(f"Security receipt not found: {receipt_id}")

        actual_hash = canonical_hash(target.content())
        verified, reason = self._verify_replay_target(target)
        prior = {"target_receipt_hash": target.receipt_hash}
        normalized = {
            "operation": "replay",
            "receipt_id": receipt_id,
        }
        replay_receipt = self.receipts.issue(
            operation="replay",
            organization_id=target.organization_id,
            identity_id=target.identity_id,
            assignment_type=None,
            requested_value=receipt_id,
            outcome="PASS" if verified else "FAIL",
            status="Verified" if verified else "Failed",
            reason_code="REPLAY_VERIFIED" if verified else "REPLAY_FAILED",
            normalized_input=normalized,
            prior_state=prior,
            resulting_state=prior,
            result={"verified": verified, "reason": reason},
        )
        self._publish_receipt(
            self.EVENT_REPLAY_VERIFIED if verified else self.EVENT_REPLAY_FAILED,
            reason,
            replay_receipt,
        )
        return ReplayResult(
            receipt_id=receipt_id,
            verified=verified,
            operation=target.operation,
            expected_hash=target.receipt_hash,
            actual_hash=actual_hash,
            reason=reason,
            replay_receipt_id=replay_receipt.receipt_id,
        )

    def get_receipts(self) -> list[dict[str, object]]:
        return [receipt.to_dict() for receipt in self.repositories.receipts.list_all()]

    def _issue_success(
        self,
        *,
        operation: str,
        normalized: dict[str, Any],
        prior: dict[str, Any],
        resulting: dict[str, Any],
        result: dict[str, Any],
        requested_value: Any,
        organization_id: str,
        identity_id: str | None,
        assignment_type: str | None,
        status: str,
        reason_code: str,
    ) -> SecurityReceipt:
        if not self.receipts.verify_chain():
            raise EvidenceVerificationError("Security receipt chain is invalid.")
        receipt = self.receipts.issue(
            operation=operation,
            organization_id=organization_id,
            identity_id=identity_id,
            assignment_type=assignment_type,
            requested_value=requested_value,
            outcome="PASS",
            status=status,
            reason_code=reason_code,
            normalized_input=normalized,
            prior_state=prior,
            resulting_state=resulting,
            result=result,
        )
        if not self.receipts.verify_receipt(receipt) or not self.receipts.verify_chain():
            raise EvidenceVerificationError("Issued security receipt failed verification.")
        return receipt

    def _issue_failure(
        self,
        *,
        operation: str,
        raw_input: dict[str, Any],
        error: Exception,
        assignment_type: str | None = None,
        status: str = "Rejected",
    ) -> SecurityReceipt:
        reason_code = (
            error.reason_code
            if isinstance(error, SecurityCoreError)
            else "INTERNAL_ERROR"
        )
        organization_id = raw_input.get("organization_id")
        identity_id = raw_input.get("identity_id")
        safe_organization = organization_id if isinstance(organization_id, str) else ""
        safe_identity = identity_id if isinstance(identity_id, str) else None
        normalized = self._safe_normalized_input(operation, raw_input)
        prior = self._safe_operation_state(safe_organization, safe_identity, assignment_type)
        receipt = self.receipts.issue(
            operation=operation,
            organization_id=safe_organization,
            identity_id=safe_identity,
            assignment_type=assignment_type,
            requested_value=self._requested_value(raw_input),
            outcome="FAIL",
            status=status,
            reason_code=reason_code,
            normalized_input=normalized,
            prior_state=prior,
            resulting_state=prior,
            result={
                "status": status,
                "reason_code": reason_code,
                "message": self._safe_error_message(error),
            },
        )
        self._publish_receipt(
            self.EVENT_OPERATION_FAILED,
            "Security Core operation failed closed.",
            receipt,
            severity="ERROR",
        )
        return receipt

    def _idempotent_result(self, normalized: dict[str, Any]) -> dict[str, object] | None:
        key = normalized["idempotency_key"]
        input_hash = canonical_hash(normalized)
        stored = self.repositories.idempotency.get(key)
        if stored is None:
            return None
        stored_hash, receipt_id = stored
        if stored_hash != input_hash:
            raise IdempotencyConflictError(
                "Idempotency key was reused with different normalized input."
            )
        receipt = self.repositories.receipts.get(receipt_id)
        if receipt is None or not self.receipts.verify_receipt(receipt):
            raise EvidenceVerificationError(
                "Stored idempotent security receipt cannot be verified."
            )
        return receipt.to_dict()

    def _store_idempotency(self, normalized: dict[str, Any], receipt: SecurityReceipt) -> None:
        self.repositories.idempotency.save(
            normalized["idempotency_key"], canonical_hash(normalized), receipt.receipt_id
        )

    def _verify_replay_target(self, receipt: SecurityReceipt) -> tuple[bool, str]:
        if not self.receipts.verify_receipt(receipt):
            return False, "Receipt hash verification failed."
        if not self.receipts.verify_chain():
            return False, "Receipt-chain verification failed."
        if receipt.prior_state_hash != canonical_hash(receipt.prior_state):
            return False, "Prior security-state hash did not match."
        if receipt.resulting_state_hash != canonical_hash(receipt.resulting_state):
            return False, "Resulting security-state hash did not match."
        expected_state = self._replay_resulting_state(receipt)
        if expected_state != receipt.resulting_state:
            return False, "Deterministic operation result did not match."
        if receipt.operation == "authorize" and receipt.outcome == "PASS":
            decision, reason_code = decide_role_authorization(
                identity_registered=receipt.prior_state.get("identity") is not None,
                assigned_roles=tuple(receipt.prior_state.get("roles") or ()),
                required_role=str(receipt.requested_value),
            )
            configured = self._configured_values("security_core.allowed_roles")
            if receipt.requested_value not in configured:
                decision = AuthorizationDecision.DENY
                reason_code = "ROLE_NOT_CONFIGURED"
            if (
                receipt.status != decision.value
                or receipt.reason_code != reason_code
            ):
                return False, "Authorization decision did not replay."
        return True, "Deterministic replay matched the stored security evidence."

    @staticmethod
    def _replay_resulting_state(receipt: SecurityReceipt) -> dict[str, Any]:
        if receipt.outcome == "FAIL" or receipt.operation in {"authorize", "replay"}:
            return deepcopy(receipt.prior_state)
        resulting = deepcopy(receipt.prior_state)
        normalized = receipt.normalized_input()
        if receipt.operation == "register_identity":
            resulting["identity"] = {
                "organization_id": normalized["organization_id"],
                "identity_id": normalized["identity_id"],
                "status": RecordStatus.REGISTERED.value,
            }
            resulting.setdefault("roles", None)
        elif receipt.operation == "assign_identity_and_roles":
            resulting["identity"] = {
                "organization_id": normalized["organization_id"],
                "identity_id": normalized["identity_id"],
                "status": RecordStatus.REGISTERED.value,
            }
            resulting["roles"] = tuple(
                sorted(
                    set(receipt.prior_state.get("roles") or ())
                    | set(normalized["roles"])
                )
            )
        elif receipt.operation == "assign_policy":
            resulting["policy"] = {
                "organization_id": normalized["organization_id"],
                "policy_id": normalized["policy_id"],
                "status": RecordStatus.ASSIGNED.value,
            }
        return resulting

    def _identity_role_state(self, organization_id: str, identity_id: str) -> dict[str, Any]:
        identity = self.repositories.identities.get(organization_id, identity_id)
        roles = self.repositories.roles.get(organization_id, identity_id)
        return {
            "identity": identity.to_dict() if identity else None,
            "roles": roles.roles if roles else None,
        }

    def _policy_state(self, organization_id: str) -> dict[str, Any]:
        policy = self.repositories.policies.get(organization_id)
        return {"policy": policy.to_dict() if policy else None}

    def _safe_operation_state(
        self,
        organization_id: str,
        identity_id: str | None,
        assignment_type: str | None,
    ) -> dict[str, Any]:
        try:
            if assignment_type == "security_policy":
                return self._policy_state(organization_id)
            if identity_id:
                return self._identity_role_state(organization_id, identity_id)
        except Exception:
            pass
        return {}

    def _ensure_operational(self) -> None:
        if self.health().get("operational") is not True:
            raise SecurityUnavailableError("Security Core is not operational.")
        if not self.receipts.verify_chain():
            raise EvidenceVerificationError("Security receipt chain verification failed.")

    def _validate_operating_configuration(self) -> None:
        self._configured_values("security_core.allowed_roles")
        self._configured_values("security_core.allowed_policy_ids")
        if self.configuration is None:
            raise SecurityConfigurationError("Configuration service is unavailable.")
        enabled = self.configuration.require("security_core.enabled")
        if enabled is not True:
            raise SecurityConfigurationError("Security Core is not enabled by configuration.")

    def _configured_values(self, key: str) -> tuple[str, ...]:
        if self.configuration is None:
            raise SecurityConfigurationError("Configuration service is unavailable.")
        return self._validated_configured_values(self.configuration, key)

    @staticmethod
    def _validated_configured_values(
        configuration: Configuration,
        key: str,
    ) -> tuple[str, ...]:
        try:
            values = configuration.require(key)
        except RuntimeError as error:
            raise SecurityConfigurationError(str(error)) from error
        if not isinstance(values, (list, tuple)):
            raise SecurityConfigurationError(f"Configuration must be a list or tuple: {key}")
        normalized = tuple(sorted(values))
        if not normalized or any(not isinstance(value, str) or not value for value in normalized):
            raise SecurityConfigurationError(f"Configuration contains invalid values: {key}")
        return normalized

    def _require_configured(self, key: str, requested: tuple[str, ...]) -> None:
        allowed = set(self._configured_values(key))
        missing = sorted(set(requested) - allowed)
        if missing:
            raise SecurityConfigurationError(
                "Requested values are not configured: " + ", ".join(missing),
                reason_code="VALUE_NOT_CONFIGURED",
            )

    def _normalize_identity_input(self, raw: dict[str, Any]) -> dict[str, Any]:
        organization_id = self._validate_organization(raw.get("organization_id"))
        identity_id = self._validate_identity(raw.get("identity_id"))
        return {
            "operation": "register_identity",
            "organization_id": organization_id,
            "identity_id": identity_id,
            "idempotency_key": self._validate_idempotency(raw.get("idempotency_key")),
        }

    def _normalize_role_input(self, raw: dict[str, Any]) -> dict[str, Any]:
        roles = raw.get("roles")
        if not isinstance(roles, (list, tuple)) or not roles:
            raise SecurityValidationError("At least one role is required.")
        if any(not isinstance(role, str) or not self._CONFIGURED_ID_PATTERN.fullmatch(role) for role in roles):
            raise SecurityValidationError("Role identifiers are invalid.")
        normalized_roles = tuple(sorted(set(roles)))
        return {
            "operation": "assign_identity_and_roles",
            "organization_id": self._validate_organization(raw.get("organization_id")),
            "identity_id": self._validate_identity(raw.get("identity_id")),
            "roles": normalized_roles,
            "idempotency_key": self._validate_idempotency(raw.get("idempotency_key")),
        }

    def _normalize_policy_input(self, raw: dict[str, Any]) -> dict[str, Any]:
        policy_id = raw.get("policy_id")
        if not isinstance(policy_id, str) or not self._CONFIGURED_ID_PATTERN.fullmatch(policy_id):
            raise SecurityValidationError("Security policy identifier is invalid.")
        return {
            "operation": "assign_policy",
            "organization_id": self._validate_organization(raw.get("organization_id")),
            "policy_id": policy_id,
            "idempotency_key": self._validate_idempotency(raw.get("idempotency_key")),
        }

    def _normalize_authorization_input(self, raw: dict[str, Any]) -> dict[str, Any]:
        role = raw.get("required_role")
        if not isinstance(role, str) or not self._CONFIGURED_ID_PATTERN.fullmatch(role):
            raise SecurityValidationError("Authorization role requirement is invalid.")
        return {
            "operation": "authorize",
            "organization_id": self._validate_organization(raw.get("organization_id")),
            "identity_id": self._validate_identity(raw.get("identity_id")),
            "required_role": role,
        }

    def _validate_organization(self, value: object) -> str:
        if not isinstance(value, str) or not self._ORGANIZATION_PATTERN.fullmatch(value):
            raise SecurityValidationError("Organization identifier is invalid.")
        return value

    def _validate_identity(self, value: object) -> str:
        if not isinstance(value, str) or not self._IDENTITY_PATTERN.fullmatch(value):
            raise SecurityValidationError("Identity identifier is invalid.")
        return value

    @staticmethod
    def _validate_idempotency(value: object) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > 160:
            raise SecurityValidationError("Idempotency key is invalid.")
        return value.strip()

    @staticmethod
    def _safe_normalized_input(operation: str, raw: dict[str, Any]) -> dict[str, Any]:
        safe: dict[str, Any] = {"operation": operation}
        for key in (
            "organization_id",
            "identity_id",
            "roles",
            "policy_id",
            "required_role",
            "idempotency_key",
            "receipt_id",
            "service",
        ):
            value = raw.get(key)
            if key == "roles" and isinstance(value, (tuple, list)):
                safe[key] = (
                    tuple(sorted(value))
                    if all(isinstance(item, str) for item in value)
                    else "<invalid>"
                )
            elif isinstance(value, (str, bool, int, float)) or value is None:
                safe[key] = value
        return safe

    @staticmethod
    def _requested_value(raw: dict[str, Any]) -> Any:
        for key in ("roles", "policy_id", "required_role", "identity_id", "receipt_id", "service"):
            if key in raw:
                value = raw[key]
                if isinstance(value, (str, bool, int, float)) or value is None:
                    return value
                if isinstance(value, (tuple, list)) and all(
                    isinstance(item, str) for item in value
                ):
                    return tuple(value)
                return "<invalid>"
        return None

    def _dependency_status(self) -> dict[str, str]:
        statuses: dict[str, str] = {}
        for name in self.REQUIRED_SERVICES:
            service = self.registry.get(name)
            if service is not None:
                statuses[name] = service.status
        return statuses

    def _subscribe_audit(self) -> None:
        if self._subscribed or self.event_bus is None or self.audit is None:
            return
        for event_type in (
            self.EVENT_STARTED,
            self.EVENT_IDENTITY_REGISTERED,
            self.EVENT_ROLES_ASSIGNED,
            self.EVENT_POLICY_ASSIGNED,
            self.EVENT_AUTHORIZATION_ALLOWED,
            self.EVENT_AUTHORIZATION_DENIED,
            self.EVENT_OPERATION_FAILED,
            self.EVENT_REPLAY_VERIFIED,
            self.EVENT_REPLAY_FAILED,
        ):
            self.event_bus.subscribe(event_type, self.audit.handle_event)
        self._subscribed = True

    def _publish_receipt(
        self,
        event_type: str,
        message: str,
        receipt: SecurityReceipt,
        *,
        severity: str = "INFO",
    ) -> None:
        self._publish(
            event_type,
            message,
            severity=severity,
            payload={
                "receipt_id": receipt.receipt_id,
                "operation": receipt.operation,
                "organization_id": receipt.organization_id,
                "outcome": receipt.outcome,
                "reason_code": receipt.reason_code,
                "receipt_hash": receipt.receipt_hash,
            },
        )

    def _publish(
        self,
        event_type: str,
        message: str,
        *,
        severity: str = "INFO",
        payload: dict[str, object] | None = None,
    ) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(
            AnchorEvent(
                source=self.name,
                event_type=event_type,
                message=message,
                severity=severity,
                payload=payload or {},
            )
        )

    @staticmethod
    def _safe_error_message(error: Exception) -> str:
        if isinstance(error, SecurityCoreError):
            return str(error)
        return f"Internal operation failure: {type(error).__name__}."


def create_module(context: object) -> SecurityCore:
    """Discover Security Core while retaining the authoritative registry."""

    if not isinstance(context, ServiceRegistry):
        raise RuntimeError("Security Core discovery requires ServiceRegistry context.")
    return SecurityCore.from_registry(context)
