from anchorcore.audit import Audit
from anchorcore.eventbus import EventBus
from core.module import Module
from core.module_manager import ModuleManager


def boot() -> None:
    """Boot the AnchorOS operational platform."""

    print("=" * 40)
    print("AnchorOS Starting...")
    print("=" * 40)

    manager = ModuleManager()

    print("\nDiscovering AnchorCore...\n")

    core_modules = manager.discover("anchorcore")

    context: dict[str, Module] = {
        module.name: module
        for module in core_modules
    }

    audit = context.get("Audit Engine")
    event_bus = context.get("Event Bus")

    if not isinstance(audit, Audit):
        raise RuntimeError(
            "AnchorOS requires the AnchorCore Audit Engine."
        )

    if not isinstance(event_bus, EventBus):
        raise RuntimeError(
            "AnchorOS requires the AnchorCore Event Bus."
        )

    event_bus.subscribe(
        event_name="framework.started",
        handler=audit.handle_event,
    )

    event_bus.subscribe(
        event_name="framework.stopping",
        handler=audit.handle_event,
    )

    print("\nDiscovering Frameworks...\n")

    manager.discover(
        package_name="frameworks",
        context=context,
    )

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
