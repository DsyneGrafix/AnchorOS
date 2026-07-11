from collections.abc import Callable
from typing import Any

from core.module import Module


EventHandler = Callable[[dict[str, Any]], None]


class EventBus(Module):
    """AnchorCore platform messaging service."""

    def __init__(self) -> None:
        super().__init__("Event Bus", "1.0.0")
        self.subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(
        self,
        event_name: str,
        handler: EventHandler,
    ) -> None:
        """Subscribe a handler to a named event."""

        handlers = self.subscribers.setdefault(event_name, [])

        if handler not in handlers:
            handlers.append(handler)

    def publish(
        self,
        event_name: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish an event to all subscribers."""

        print(f"✓ Event: {event_name}")

        for handler in self.subscribers.get(event_name, []):
            handler(payload)


def create_module(context: dict) -> EventBus:
    """Create the AnchorCore Event Bus."""

    return EventBus()
