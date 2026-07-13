from anchorcore.audit import Audit
from anchorcore.eventbus import EventBus
from anchorcore.health import Health
from anchorcore.manifest import PlatformManifest
from banner import print_banner
from core.module_manager import ModuleManager
from core.service_registry import ServiceRegistry


def boot() -> None:
    """Boot the AnchorOS operational platform."""

    print_banner()
    print("\nPlatform Initialization Sequence\n")

    manager = ModuleManager()
    registry = ServiceRegistry()

    # --------------------------------------------------
    # Discover and register AnchorCore services
    # --------------------------------------------------

    print("\nDiscovering AnchorCore...\n")

    core_modules = manager.discover("anchorcore")

    for module in core_modules:
        registry.register(module)

    # --------------------------------------------------
    # Resolve required platform services
    # --------------------------------------------------

    audit = registry.require("Audit Engine")
    event_bus = registry.require("Event Bus")
    health = registry.require("Health Monitor")
    manifest = registry.require("Platform Manifest")

    if not isinstance(audit, Audit):
        raise RuntimeError(
            "AnchorOS requires a valid Audit Engine."
        )

    if not isinstance(event_bus, EventBus):
        raise RuntimeError(
            "AnchorOS requires a valid Event Bus."
        )

    if not isinstance(health, Health):
        raise RuntimeError(
            "AnchorOS requires a valid Health Monitor."
        )

    if not isinstance(manifest, PlatformManifest):
        raise RuntimeError(
            "AnchorOS requires a valid Platform Manifest."
        )

    # --------------------------------------------------
    # Populate the AnchorCore portion of the manifest
    # --------------------------------------------------

    for service_name in registry.list_services():
        manifest.register_service(service_name)

    # --------------------------------------------------
    # Configure platform event subscriptions
    # --------------------------------------------------

    event_bus.subscribe(
        event_type="framework.started",
        handler=audit.handle_event,
    )

    event_bus.subscribe(
        event_type="framework.started",
        handler=health.handle_framework_started,
    )

    event_bus.subscribe(
        event_type="framework.stopping",
        handler=audit.handle_event,
    )

    # --------------------------------------------------
    # Discover frameworks
    # --------------------------------------------------

    print("\nDiscovering Frameworks...\n")

    framework_modules = manager.discover(
        package_name="frameworks",
        context=registry,
    )

    for framework in framework_modules:
        manifest.register_framework(framework.name)

    # --------------------------------------------------
    # Display registered platform services
    # --------------------------------------------------

    print("\nRegistered Services")
    print("-" * 40)

    for service_name in registry.list_services():
        print(f"✓ {service_name}")

    # --------------------------------------------------
    # Start the platform
    # --------------------------------------------------

    print("\nLoading Platform...\n")

    manager.start_all()

    # --------------------------------------------------
    # Display module health
    # --------------------------------------------------

    print("\nHealth Report")
    print("-" * 40)

    for module in manager.health_report():
        print(
            f"{module['name']}: "
            f"{module['status']} "
            f"(v{module['version']})"
        )

    # --------------------------------------------------
    # Display framework states
    # --------------------------------------------------

    print("\nFramework States")
    print("-" * 40)

    framework_states = health.get_framework_states()

    if framework_states:
        for name, status in framework_states.items():
            print(f"{name}: {status}")
    else:
        print("No framework states reported.")

    # --------------------------------------------------
    # Display the platform manifest
    # --------------------------------------------------

    manifest_data = manifest.describe()

    print("\nPlatform Manifest")
    print("-" * 40)

    print(f"Product   : {manifest_data['product']}")
    print(f"Version   : {manifest_data['version']}")
    print(f"Codename  : {manifest_data['codename']}")
    print(f"Stage     : {manifest_data['stage']}")
    print(f"Boot      : {manifest_data['boot']}")
    print(f"Build     : {manifest_data['build']}")

    print("\nKernel")
    print("-" * 40)

    for component in manifest_data["kernel"]:
        print(f"✓ {component}")

    print("\nAnchorCore Services")
    print("-" * 40)

    for service in manifest_data["services"]:
        print(f"✓ {service}")

    print("\nFrameworks")
    print("-" * 40)

    if manifest_data["frameworks"]:
        for framework in manifest_data["frameworks"]:
            print(f"✓ {framework}")
    else:
        print("None")

    print("\nApplications")
    print("-" * 40)

    if manifest_data["applications"]:
        for application in manifest_data["applications"]:
            print(f"✓ {application}")
    else:
        print("None")

    # --------------------------------------------------
    # Display audit records
    # --------------------------------------------------

    print("\nAudit Records")
    print("-" * 40)

    audit_records = audit.get_records()

    if audit_records:
        for record in audit_records:
            print(
                f"{record['timestamp']} | "
                f"{record['event_id']} | "
                f"{record['source']} | "
                f"{record['event_type']} | "
                f"{record['severity']} | "
                f"{record['message']}"
            )
    else:
        print("No audit records.")

    # --------------------------------------------------
    # Complete initialization
    # --------------------------------------------------

    print("\n" + "=" * 58)
    print("Platform Initialization Complete")
    print("AnchorOS is Operational.")
    print("=" * 58)
