from anchorcore.audit import Audit
from anchorcore.configuration import Configuration
from anchorcore.eventbus import EventBus
from anchorcore.health import Health
from core.module_manager import ModuleManager
from frameworks.anchorstack import AnchorStack


def boot() -> None:
    """Boot the AnchorOS operational platform."""

    print("=" * 40)
    print("AnchorOS Starting...")
    print("=" * 40)

    manager = ModuleManager()

    # Create AnchorCore services.
    configuration = Configuration()
    audit = Audit()
    event_bus = EventBus()
    health = Health()

    # Create frameworks and provide their platform dependencies.
    anchorstack = AnchorStack(audit=audit)

    print("\nRegistering AnchorCore...\n")

    manager.register(configuration)
    manager.register(audit)
    manager.register(event_bus)
    manager.register(health)

    print("\nRegistering Frameworks...\n")

    manager.register(anchorstack)

    print("\nLoading Platform...\n")

    manager.start_all()

    print("\nHealth Report")
    print("-" * 40)

    for module in manager.health_report():
        print(
            f"{module['name']}: "
            f"{module['status']} "
            f"(v{module['version']})"
        )

    print("\nAudit Records")
    print("-" * 40)

    for record in audit.get_records():
        print(
            f"{record['timestamp']} | "
            f"{record['source']} | "
            f"{record['event']} | "
            f"{record['message']}"
        )

    print("\n" + "=" * 40)
    print("Platform Operational")
    print("=" * 40)
