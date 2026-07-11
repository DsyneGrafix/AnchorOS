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

    audit = manager.get("Audit Engine")

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
