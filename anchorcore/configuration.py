from core.module import Module


class Configuration(Module):
    """AnchorCore Configuration Service."""

    def __init__(self):
        super().__init__("Configuration", "1.0.0")


def create_module(context: dict) -> Configuration:
    """Create the Configuration service."""
    return Configuration()
