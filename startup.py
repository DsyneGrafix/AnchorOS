from services.audit import Audit
from services.eventbus import EventBus
from services.health import Health
from services.manifest import PlatformManifest
from banner import print_banner
from core.boot_pipeline import BootPipeline
from core.module_manager import ModuleManager
from core.service_registry import ServiceRegistry


def boot() -> None:
    """Initialize, verify, and report the AnchorOS platform."""

    print_banner()
    print("\nPlatform Initialization Sequence\n")

    manager = ModuleManager()
    registry = ServiceRegistry()
    pipeline = BootPipeline()

    # --------------------------------------------------
    # Discover Platform Services
    # --------------------------------------------------

    print("\nDiscovering Platform Services...\n")

    core_modules = manager.discover("services")

    for module in core_modules:
        registry.register(module)

    # --------------------------------------------------
    # Resolve required AnchorCore services
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
    # Populate AnchorCore manifest inventory
    # --------------------------------------------------

    for service_name in registry.list_services():
        manifest.register_service(service_name)

    # --------------------------------------------------
    # Configure event subscriptions
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

    event_bus.subscribe(
        event_type="anchorstack.continuation_validity.determined",
        handler=audit.handle_event,
    )

    event_bus.subscribe(
        event_type="anchorgrid.equipment_evidence.snapshot_prepared",
        handler=audit.handle_event,
    )

    event_bus.subscribe(
        event_type="anchorgrid.equipment_evidence.determination_received",
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
    # Display registered services
    # --------------------------------------------------

    print("\nRegistered Services")
    print("-" * 40)

    for service_name in registry.list_services():
        print(f"✓ {service_name}")

    # --------------------------------------------------
    # Start platform
    # --------------------------------------------------

    print("\nLoading Platform...\n")

    manager.start_all()

    # --------------------------------------------------
    # Health report
    # --------------------------------------------------

    health_data = manager.health_report()

    print("\nHealth Report")
    print("-" * 40)

    for module in health_data:
        print(
            f"{module['name']}: "
            f"{module['status']} "
            f"(v{module['version']})"
        )

    # --------------------------------------------------
    # Framework states
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
    # Platform manifest
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

    print("\nPlatform Services")
    print("-" * 40)

    for service in manifest_data["services"]:
        print(f"✓ {service}")

    print("\nFrameworks")
    print("-" * 40)

    if manifest_data["frameworks"]:
        for framework in manifest_data["frameworks"]:
            print(f"✓ {framework}")
    else:
        print("No frameworks registered.")

    print("\nApplications")
    print("-" * 40)

    if manifest_data["applications"]:
        for application in manifest_data["applications"]:
            print(f"✓ {application}")
    else:
        print("No applications registered.")

    # --------------------------------------------------
    # Operational summary
    # --------------------------------------------------

    audit_records = audit.get_records()

    service_count = len(manifest_data["services"])
    framework_count = len(manifest_data["frameworks"])
    application_count = len(manifest_data["applications"])
    audit_count = len(audit_records)

    all_modules_running = all(
        module["status"] == "Running"
        for module in health_data
    )

    platform_status = (
        "HEALTHY"
        if all_modules_running
        else "DEGRADED"
    )

    print("\nOperational Summary")
    print("-" * 40)

    print(f"Services      : {service_count}")
    print(f"Frameworks    : {framework_count}")
    print(f"Applications  : {application_count}")
    print(f"Audit Records : {audit_count}")
    print()
    print(f"Platform Status: {platform_status}")

    # --------------------------------------------------
    # Audit records
    # --------------------------------------------------

    print("\nAudit Records")
    print("-" * 40)

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
    # Verify Boot Pipeline
    # --------------------------------------------------

    print("\nBoot Pipeline Verification")
    print("-" * 40)

    pipeline_results = pipeline.execute()

    passed_stages = sum(
        result.success
        for result in pipeline_results
    )

    total_stages = len(pipeline.stages)

    pipeline_passed = (
        pipeline.summary()
        and passed_stages == total_stages
    )

    print("-" * 40)
    print(
        "Pipeline Result : "
        f"{'PASS' if pipeline_passed else 'FAIL'}"
    )
    print(
        f"Stages Passed   : "
        f"{passed_stages} / {total_stages}"
    )
    print(
        "Overall Status  : "
        f"{'VERIFIED' if pipeline_passed else 'FAILED'}"
    )

    if not pipeline_passed:
        raise RuntimeError(
            "AnchorOS Boot Pipeline verification failed."
        )

    if not all_modules_running:
        raise RuntimeError(
            "AnchorOS cannot declare operational status "
            "while one or more modules are not running."
        )

    # --------------------------------------------------
    # Lifecycle report
    # --------------------------------------------------

    lifecycle_states = manager.lifecycle_report()

    print("\nLifecycle Report")
    print("-" * 40)

    if lifecycle_states:
        for name, state in lifecycle_states.items():
            print(f"{name}: {state}")
    else:
        print("No lifecycle states reported.")

    lifecycle_verified = (
        bool(lifecycle_states)
        and all(
            state == "Running"
            for state in lifecycle_states.values()
        )
    )

    print()
    print(
        "Lifecycle Manager: "
        f"{'VERIFIED' if lifecycle_verified else 'FAILED'}"
    )

    if not lifecycle_verified:
        raise RuntimeError(
            "AnchorOS lifecycle verification failed."
        )

    # --------------------------------------------------
    # Declare operational state
    # --------------------------------------------------

    print("\n" + "=" * 58)
    print("Platform Initialization Complete")
    print("AnchorOS is Operational.")
    print("=" * 58)
