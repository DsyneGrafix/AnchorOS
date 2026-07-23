class Module:
    """Base class for every AnchorOS-managed module."""

    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version
        self.status = "Offline"

    def start(self) -> None:
        self.status = "Running"

    def stop(self) -> None:
        self.status = "Stopped"

    def health(self) -> dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status,
        }
