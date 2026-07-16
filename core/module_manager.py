import importlib
import pkgutil

from core.lifecycle_manager import LifecycleManager
from core.module import Module


class ModuleManager:
    """Discovers, registers, and manages AnchorOS modules."""

    def __init__(self) -> None:
        self.modules: dict[str, Module] = {}
        self.lifecycle = LifecycleManager()

    def register(self, module: Module) -> None:
        """Register a verified AnchorOS module."""

        if not isinstance(module, Module):
            raise TypeError(
                f"Cannot register object of type "
                f"{type(module).__name__}; expected Module."
            )

        if module.name in self.modules:
            raise ValueError(
                f"Module already registered: {module.name}"
            )

        self.lifecycle.discover(module)
        self.lifecycle.register(module)

        self.modules[module.name] = module

        print(f"✓ Registered: {module.name}")

    def discover(
        self,
        package_name: str,
        context: dict[str, Module] | None = None,
    ) -> list[Module]:
        """
        Discover modules inside a Python package.

        Each discoverable file must provide a create_module(context)
        factory function that returns a Module instance.
        """

        package = importlib.import_module(package_name)

        if not hasattr(package, "__path__"):
            raise ValueError(
                f"{package_name} is not a discoverable package."
            )

        discovered: list[Module] = []
        module_context = context or {}

        for module_info in pkgutil.iter_modules(package.__path__):
            if module_info.name.startswith("_"):
                continue

            full_name = f"{package_name}.{module_info.name}"
            imported_module = importlib.import_module(full_name)

            factory = getattr(
                imported_module,
                "create_module",
                None,
            )

            if factory is None:
                continue

            module = factory(module_context)

            if not isinstance(module, Module):
                raise TypeError(
                    f"{full_name}.create_module() did not "
                    f"return a Module instance."
                )

            self.register(module)
            discovered.append(module)

        return discovered

    def start_all(self) -> None:
        """Start every registered module."""

        for module in self.modules.values():
            self.lifecycle.start(module)
            print(f"✓ Started: {module.name}")

    def stop_all(self) -> None:
        """Stop every registered module."""

        for module in reversed(list(self.modules.values())):
            self.lifecycle.stop(module)
            print(f"✓ Stopped: {module.name}")

    def health_report(self) -> list[dict[str, str]]:
        """Return health information for all registered modules."""

        return [
            module.health()
            for module in self.modules.values()
        ]

    def lifecycle_report(self) -> dict[str, str]:
        """Return lifecycle state for all registered modules."""

        return {
            name: state.value
            for name, state in self.lifecycle.report().items()
        }

    def get(self, name: str) -> Module:
        """Retrieve a registered module by name."""

        try:
            return self.modules[name]
        except KeyError as error:
            raise KeyError(
                f"Module is not registered: {name}"
            ) from error
