from anchorcore.audit import Audit
from core.module import Module


class AnchorStack(Module):
    """AnchorStack governance framework."""

    def __init__(self, audit: Audit) -> None:
        super().__init__("AnchorStack", "1.0.0")
        self.audit = audit

    def start(self) -> None:
        super().start()

        self.audit.log(
            source=self.name,
            event="framework.started",
            message="AnchorStack entered the Running state.",
        )

    def stop(self) -> None:
        self.audit.log(
            source=self.name,
            event="framework.stopping",
            message="AnchorStack is leaving the Running state.",
        )

        super().stop()
