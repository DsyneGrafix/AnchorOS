from core.module import Module


class ModuleManager:
    """Registers and manages AnchorOS modules."""

    def __init__(self) -> None:
        self.modules: dict[str, Module] = {}

    def register(self, module: Module) -> None:
        if module.name in self.modules:
            raise ValueError(f"Module already registered: {module.name}")

        self.modules[module.name] = module
        print(f"✓ Registered: {module.name}")

    def start_all(self) -> None:
        for module in self.modules.values():
            module.start()
            print(f"✓ Started: {module.name}")

    def stop_all(self) -> None:
        for module in self.modules.values():
            module.stop()
            print(f"✓ Stopped: {module.name}")

    def health_report(self) -> list[dict[str, str]]:
        return [module.health() for module in self.modules.values()]
