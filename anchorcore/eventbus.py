from core.module import Module


class EventBus(Module):
    """AnchorCore Event Bus."""

    def __init__(self):
        super().__init__("Event Bus", "1.0.0")


def create_module(context: dict) -> EventBus:
    """Create the Event Bus service."""
    return EventBus()
