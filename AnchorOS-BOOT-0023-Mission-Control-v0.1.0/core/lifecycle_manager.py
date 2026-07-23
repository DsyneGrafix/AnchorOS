from core.lifecycle import LifecycleState
from core.module import Module


class LifecycleManager:
    """Manages the operational lifecycle of AnchorOS modules."""

    def __init__(self) -> None:
        self._states: dict[str, LifecycleState] = {}

    def discover(self, module: Module) -> None:
        """Record that AnchorOS discovered a module."""

        self._states[module.name] = LifecycleState.DISCOVERED

    def register(self, module: Module) -> None:
        """Record that a discovered module was registered."""

        self._require_state(
            module,
            allowed={
                LifecycleState.DISCOVERED,
                LifecycleState.STOPPED,
            },
        )

        self._states[module.name] = LifecycleState.REGISTERED

    def start(self, module: Module) -> None:
        """Start a registered module and track its lifecycle."""

        self._require_state(
            module,
            allowed={
                LifecycleState.REGISTERED,
                LifecycleState.STOPPED,
            },
        )

        self._states[module.name] = LifecycleState.STARTING

        try:
            module.start()
        except Exception:
            self._states[module.name] = LifecycleState.FAILED
            raise

        self._states[module.name] = LifecycleState.RUNNING

    def stop(self, module: Module) -> None:
        """Stop a running module and track its lifecycle."""

        self._require_state(
            module,
            allowed={LifecycleState.RUNNING},
        )

        self._states[module.name] = LifecycleState.STOPPING

        try:
            module.stop()
        except Exception:
            self._states[module.name] = LifecycleState.FAILED
            raise

        self._states[module.name] = LifecycleState.STOPPED

    def restart(self, module: Module) -> None:
        """Stop and restart a running module."""

        self.stop(module)
        self.start(module)

    def fail(self, module: Module) -> None:
        """Explicitly place a module into the Failed state."""

        self._states[module.name] = LifecycleState.FAILED

    def get_state(self, module_name: str) -> LifecycleState | None:
        """Return the current lifecycle state for a module."""

        return self._states.get(module_name)

    def report(self) -> dict[str, LifecycleState]:
        """Return a copy of all tracked lifecycle states."""

        return dict(self._states)

    def _require_state(
        self,
        module: Module,
        allowed: set[LifecycleState],
    ) -> None:
        """Confirm that a requested transition is permitted."""

        current_state = self._states.get(
            module.name,
            LifecycleState.CREATED,
        )

        if current_state not in allowed:
            allowed_names = ", ".join(
                state.value for state in allowed
            )

            raise RuntimeError(
                f"{module.name} cannot transition from "
                f"{current_state.value}. "
                f"Allowed states: {allowed_names}."
            )
