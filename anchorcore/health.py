from typing import Any

from core.module import Module


class Health(Module):
    """AnchorCore Health Monitor."""

    def __init__(self) -> None:
        super().__init__("Health Monitor", "1.0.0")
        self.framework_states: dict[str, str] = {}

    def handle_framework_started(
        self,
        payload: dict[str, Any],
    ) -> None:
        """Record that a framework entered the Running state."""

        source = str(payload["source"])
        self.framework_states[source] = "Running"

        print(f"✓ Health: {source} reported Running")

    def get_framework_states(self) -> dict[str, str]:
        """Return known framework states."""

        return self.framework_states.copy()


def create_module(context: dict) -> Health:
    """Create the AnchorCore Health Monitor."""

    return Health()
