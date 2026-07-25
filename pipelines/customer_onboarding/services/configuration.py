from core.module import Module


class Configuration(Module):
    """AnchorOS Configuration Service."""

    def __init__(
        self,
        initial: dict[str, object] | None = None,
    ) -> None:
        super().__init__("Configuration", "1.0.0")
        self._settings = dict(initial or {})

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


def create_module(context: dict) -> Configuration:
    """Create the Configuration service."""
    return Configuration()
