from core.module import Module


class Health(Module):
    """AnchorCore Health Monitor."""

    def __init__(self):
        super().__init__("Health Monitor", "1.0.0")


def create_module(context: dict) -> Health:
    """Create the Health Monitor service."""
    return Health()
