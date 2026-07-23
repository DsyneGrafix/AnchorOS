from __future__ import annotations

import time
import webbrowser
from typing import Any

from applications.mission_control import MissionControl
from banner import print_banner
from core.boot_pipeline import BootPipeline
from core.module_manager import ModuleManager
from core.service_registry import ServiceRegistry
from services.audit import Audit
from services.event import AnchorEvent
from services.eventbus import EventBus
from services.health import Health
from services.manifest import PlatformManifest


def boot(*, verify_only: bool = False, open_browser: bool = True) -> None:
    """Initialize, verify, expose, and report the AnchorOS platform."""

    print_banner()
    print("\nPlatform Initialization Sequence\n")

    manager = ModuleManager()
    registry = ServiceRegistry()
    pipeline = BootPipeline()
    pipeline_state: dict[str, Any] = {
        "verified": False,
        "passed": 0,
        "total": len(pipeline.stages),
        "result": "PENDING",
    }

    print("\nDiscovering Platform Services...\n")
    core_modules = manager.discover("services", context=registry)
    for module in core_modules:
        registry.register(module)

    audit = registry.require("Audit Engine")
    event_bus = registry.require("Event Bus")
    health = registry.require("Health Monitor")
    manifest = registry.require("Platform Manifest")

    if not isinstance(audit, Audit):
        raise RuntimeError("AnchorOS requires a valid Audit Engine.")
    if not isinstance(event_bus, EventBus):
        raise RuntimeError("AnchorOS requires a valid Event Bus.")
    if not isinstance(health, Health):
        raise RuntimeError("AnchorOS requires a valid Health Monitor.")
    if not isinstance(manifest, PlatformManifest):
        raise RuntimeError("AnchorOS requires a valid Platform Manifest.")

    for service_name in registry.list_services():
        manifest.register_service(service_name)

    for event_type in ("framework.started", "framework.stopping", "application.started", "application.stopped", "pipeline.completed"):
        event_bus.subscribe(event_type=event_type, handler=audit.handle_event)
    event_bus.subscribe(event_type="framework.started", handler=health.handle_framework_started)

    print("\nDiscovering Frameworks...\n")
    framework_modules = manager.discover(package_name="frameworks", context=registry)
    for framework in framework_modules:
        manifest.register_framework(framework.name)

    print("\nDiscovering Applications...\n")
    application_modules = manager.discover(package_name="applications", context=registry)
    for application in application_modules:
        manifest.register_application(application.name)

    mission_control = manager.get("Mission Control")
    if not isinstance(mission_control, MissionControl):
        raise RuntimeError("AnchorOS requires a valid Mission Control application.")

    def snapshot() -> dict[str, Any]:
        module_health = manager.health_report()
        all_running = bool(module_health) and all(item["status"] == "Running" for item in module_health)
        manifest_data = manifest.describe()
        return {
            "platform_status": "HEALTHY" if all_running and pipeline_state["verified"] else "INITIALIZING",
            "manifest": manifest_data,
            "services": manifest_data["services"],
            "frameworks": manifest_data["frameworks"],
            "applications": manifest_data["applications"],
            "health": {"status": "HEALTHY" if all_running else "DEGRADED", "modules": module_health},
            "audit": audit.get_records(),
            "pipeline": pipeline_state.copy(),
            "lifecycle": manager.lifecycle_report(),
        }

    mission_control.set_snapshot_provider(snapshot)

    print("\nRegistered Services")
    print("-" * 40)
    for service_name in registry.list_services():
        print(f"✓ {service_name}")

    print("\nLoading Platform...\n")
    manager.start_all()

    try:
        health_data = manager.health_report()
        print("\nHealth Report")
        print("-" * 40)
        for module in health_data:
            print(f"{module['name']}: {module['status']} (v{module['version']})")

        print("\nFramework States")
        print("-" * 40)
        framework_states = health.get_framework_states()
        if framework_states:
            for name, status in framework_states.items():
                print(f"{name}: {status}")
        else:
            print("No framework states reported.")

        manifest_data = manifest.describe()
        print("\nPlatform Manifest")
        print("-" * 40)
        print(f"Product   : {manifest_data['product']}")
        print(f"Version   : {manifest_data['version']}")
        print(f"Codename  : {manifest_data['codename']}")
        print(f"Stage     : {manifest_data['stage']}")
        print(f"Boot      : {manifest_data['boot']}")
        print(f"Build     : {manifest_data['build']}")

        for title, key in (("Kernel", "kernel"), ("Platform Services", "services"), ("Frameworks", "frameworks"), ("Applications", "applications")):
            print(f"\n{title}")
            print("-" * 40)
            items = manifest_data[key]
            if items:
                for item in items:
                    print(f"✓ {item}")
            else:
                print(f"No {title.lower()} registered.")

        audit_records = audit.get_records()
        service_count = len(manifest_data["services"])
        framework_count = len(manifest_data["frameworks"])
        application_count = len(manifest_data["applications"])
        all_modules_running = all(module["status"] == "Running" for module in health_data)

        print("\nOperational Summary")
        print("-" * 40)
        print(f"Services      : {service_count}")
        print(f"Frameworks    : {framework_count}")
        print(f"Applications  : {application_count}")
        print(f"Audit Records : {len(audit_records)}")
        print("\nPlatform Status: " + ("HEALTHY" if all_modules_running else "DEGRADED"))

        print("\nAudit Records")
        print("-" * 40)
        for record in audit_records:
            print(f"{record['timestamp']} | {record['event_id']} | {record['source']} | {record['event_type']} | {record['severity']} | {record['message']}")
        if not audit_records:
            print("No audit records.")

        print("\nBoot Pipeline Verification")
        print("-" * 40)
        pipeline_results = pipeline.execute()
        passed_stages = sum(result.success for result in pipeline_results)
        total_stages = len(pipeline.stages)
        pipeline_passed = pipeline.summary() and passed_stages == total_stages
        pipeline_state.update({
            "verified": pipeline_passed,
            "passed": passed_stages,
            "total": total_stages,
            "result": "PASS" if pipeline_passed else "FAIL",
        })
        event_bus.publish(AnchorEvent(
            source="Boot Pipeline",
            event_type="pipeline.completed",
            message=f"Boot Pipeline {'verified' if pipeline_passed else 'failed'}: {passed_stages}/{total_stages} stages passed.",
            severity="INFO" if pipeline_passed else "ERROR",
            payload=pipeline_state.copy(),
        ))

        print("-" * 40)
        print("Pipeline Result : " + ("PASS" if pipeline_passed else "FAIL"))
        print(f"Stages Passed   : {passed_stages} / {total_stages}")
        print("Overall Status  : " + ("VERIFIED" if pipeline_passed else "FAILED"))
        if not pipeline_passed:
            raise RuntimeError("AnchorOS Boot Pipeline verification failed.")
        if not all_modules_running:
            raise RuntimeError("AnchorOS cannot declare operational status while one or more modules are not running.")

        lifecycle_states = manager.lifecycle_report()
        print("\nLifecycle Report")
        print("-" * 40)
        for name, state in lifecycle_states.items():
            print(f"{name}: {state}")
        lifecycle_verified = bool(lifecycle_states) and all(state == "Running" for state in lifecycle_states.values())
        print("\nLifecycle Manager: " + ("VERIFIED" if lifecycle_verified else "FAILED"))
        if not lifecycle_verified:
            raise RuntimeError("AnchorOS lifecycle verification failed.")

        print("\nMission Control")
        print("-" * 40)
        print("✓ Registered: Mission Control")
        print("✓ Running: Mission Control")
        print(f"URL: {mission_control.url}")

        print("\n" + "=" * 58)
        print("Platform Initialization Complete")
        print("AnchorOS is Operational.")
        print("=" * 58)

        if open_browser and not verify_only:
            print(f"\nOpening Mission Control: {mission_control.url}")
            webbrowser.open(mission_control.url)

        if verify_only:
            return

        print("\nPress Ctrl+C to shut down AnchorOS.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutdown requested.")
    finally:
        manager.stop_all()
        print("AnchorOS shutdown complete.")
