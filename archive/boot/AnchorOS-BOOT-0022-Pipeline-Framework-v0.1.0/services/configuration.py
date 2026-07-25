"""Authoritative AnchorOS Configuration Platform Service."""

from core.module import Module


DEFAULT_SETTINGS: dict[str, object] = {
    "security_core.enabled": True,
    "security_core.required_platform_services": (
        "Audit Engine",
        "Configuration",
        "Event Bus",
        "Health Monitor",
        "Platform Manifest",
    ),
    "security_core.allowed_roles": (
        "OrganizationAdmin",
        "OrganizationOperator",
        "SecurityReviewer",
    ),
    "security_core.allowed_policy_ids": (
        "AOS-POLICY-BASELINE",
        "AOS-POLICY-RESTRICTED",
    ),
}


class Configuration(Module):
    """AnchorOS Configuration Service with bounded runtime overrides."""

    def __init__(
        self,
        initial: dict[str, object] | None = None,
    ) -> None:
        super().__init__("Configuration", "1.0.0")
        self._settings = {
            **DEFAULT_SETTINGS,
            **dict(initial or {}),
        }

    def get(
        self,
        key: str,
        default: object = None,
    ) -> object:
        """Return a configuration value without exposing storage."""

        return self._settings.get(key, default)

    def require(self, key: str) -> object:
        """Return a required value or fail closed."""

        if key not in self._settings:
            raise RuntimeError(
                f"Required configuration not found: {key}"
            )
        return self._settings[key]

    def set(self, key: str, value: object) -> None:
        """Set a configuration value through the service API."""

        if not key:
            raise ValueError("Configuration key cannot be empty.")
        self._settings[key] = value


def create_module(context: object) -> Configuration:
    """Create the Configuration service."""

    return Configuration()
