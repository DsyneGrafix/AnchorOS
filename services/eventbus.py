from collections.abc import Callable

from services.event import AnchorEvent
from core.module import Module


EventHandler = Callable[[AnchorEvent], None]


class EventBus(Module):
    """AnchorCore platform messaging service."""

    def __init__(self) -> None:
        super().__init__("Event Bus", "1.0.0")
        self.subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        handlers = self.subscribers.setdefault(event_type, [])

        if handler not in handlers:
            handlers.append(handler)

    def publish(self, event: AnchorEvent) -> None:
        print(
            f"✓ Event: {event.event_type} "
            f"[{event.event_id}]"
        )

        for handler in self.subscribers.get(event.event_type, []):
            handler(event)


def create_module(context: dict) -> EventBus:
    return EventBus()
