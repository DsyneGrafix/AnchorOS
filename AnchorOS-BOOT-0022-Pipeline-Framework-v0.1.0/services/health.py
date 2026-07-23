from services.event import AnchorEvent
from core.module import Module


class Health(Module):
    """AnchorCore Health Monitor."""

    def __init__(self) -> None:
        super().__init__("Health Monitor", "1.0.0")
        self.framework_states: dict[str, str] = {}

    def handle_framework_started(
        self,
        event: AnchorEvent,
    ) -> None:
        self.framework_states[event.source] = "Running"

        print(
            f"✓ Health: {event.source} reported Running"
        )

    def get_framework_states(self) -> dict[str, str]:
        return self.framework_states.copy()


def create_module(context: dict) -> Health:
    return Health()
