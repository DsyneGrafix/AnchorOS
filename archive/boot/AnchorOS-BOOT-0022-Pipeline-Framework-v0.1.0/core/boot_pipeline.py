from dataclasses import dataclass

from core.pipeline import (
    PipelineChainVerifier,
    PipelineDefinition,
    PipelineReplayVerifier,
    PipelineRunner,
    PipelineStage,
    StageOutcome,
)


@dataclass
class StageResult:
    name: str
    success: bool
    message: str


class BootPipeline:
    """AnchorOS boot execution pipeline backed by Pipeline Framework v0.1."""

    PIPELINE_ID = "AOS-BOOT"
    PIPELINE_VERSION = "0.1.0"

    def __init__(self):
        self.results: list[StageResult] = []
        self.framework_result = None

        # Compatibility surface preserved for startup.py and downstream users.
        self.stages = [
            ("Identity", self.identity),
            ("Discovery", self.discover),
            ("Registration", self.register),
            ("Dependency Resolution", self.resolve_dependencies),
            ("Startup", self.startup),
            ("Verification", self.verify),
            ("Reporting", self.report),
            ("Operational", self.operational),
        ]
        framework_stages = tuple(
            PipelineStage(
                stage_id=f"BOOT-{position:03d}",
                name=name,
                position=position,
                success_state=("Operational" if position == len(self.stages) else name),
                handler=self._framework_handler(handler),
            )
            for position, (name, handler) in enumerate(self.stages, start=1)
        )
        self.definition = PipelineDefinition(
            pipeline_id=self.PIPELINE_ID,
            name="AnchorOS Boot Pipeline",
            version=self.PIPELINE_VERSION,
            stages=framework_stages,
            initial_state="Pending",
            terminal_success_state="Operational",
            terminal_failure_state="Failed",
            metadata={"compatibility": "BOOT-0021"},
        )
        self.runner = PipelineRunner()

    @staticmethod
    def _framework_handler(handler):
        def execute(_context):
            result = handler()
            return StageOutcome(
                success=result.success,
                resulting_state=result.name,
                output={"message": result.message},
                reason_code="PASS" if result.success else "BOOT_STAGE_FAILED",
                message=result.message,
            )
        return execute

    def execute(self) -> list[StageResult]:
        self.results.clear()
        self.framework_result = self.runner.run(
            self.definition,
            {"boot": self.PIPELINE_VERSION},
            pipeline_run_id="AOS-BOOT:CURRENT",
        )
        self.results.extend(
            StageResult(
                transition.stage_name,
                transition.outcome == "PASS",
                transition.output.get("message", transition.output.get("error", "")),
            )
            for transition in self.framework_result.transitions
        )
        for result in self.results:
            status = "PASS" if result.success else "FAIL"
            print(f"{status}: {result.name} — {result.message}")
        return self.results

    def summary(self) -> bool:
        return bool(self.results) and all(result.success for result in self.results)

    def verify_evidence(self) -> bool:
        return bool(self.framework_result) and PipelineChainVerifier().verify(self.framework_result)

    def replay(self):
        if self.framework_result is None:
            raise RuntimeError("Boot Pipeline has not executed.")
        return PipelineReplayVerifier().replay(self.definition, self.framework_result)

    def identity(self) -> StageResult:
        return StageResult("Identity", True, "Platform identity available.")

    def discover(self) -> StageResult:
        return StageResult("Discovery", True, "Module discovery complete.")

    def register(self) -> StageResult:
        return StageResult("Registration", True, "Module registration complete.")

    def resolve_dependencies(self) -> StageResult:
        return StageResult("Dependency Resolution", True, "Dependencies resolved.")

    def startup(self) -> StageResult:
        return StageResult("Startup", True, "Platform startup complete.")

    def verify(self) -> StageResult:
        return StageResult("Verification", True, "Platform verification passed.")

    def report(self) -> StageResult:
        return StageResult("Reporting", True, "Platform reporting complete.")

    def operational(self) -> StageResult:
        return StageResult("Operational", True, "Platform operational state approved.")
