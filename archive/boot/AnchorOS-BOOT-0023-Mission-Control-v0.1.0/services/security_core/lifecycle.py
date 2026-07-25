"""Security Core lifecycle state enforcement."""

from .models import SecurityState


class SecurityLifecycle:
    _allowed = {
        SecurityState.UNINITIALIZED: {SecurityState.INITIALIZING, SecurityState.STOPPED},
        SecurityState.INITIALIZING: {SecurityState.OPERATIONAL, SecurityState.FAILED},
        SecurityState.OPERATIONAL: {SecurityState.DEGRADED, SecurityState.STOPPED},
        SecurityState.DEGRADED: {SecurityState.OPERATIONAL, SecurityState.FAILED, SecurityState.STOPPED},
        SecurityState.FAILED: {SecurityState.INITIALIZING, SecurityState.STOPPED},
        SecurityState.STOPPED: {SecurityState.INITIALIZING},
    }

    def __init__(self) -> None:
        self.state = SecurityState.UNINITIALIZED

    def transition(self, target: SecurityState) -> None:
        if target not in self._allowed[self.state]:
            raise RuntimeError(
                f"Security Core cannot transition from {self.state.value} "
                f"to {target.value}."
            )
        self.state = target

    def force_failed(self) -> None:
        self.state = SecurityState.FAILED
