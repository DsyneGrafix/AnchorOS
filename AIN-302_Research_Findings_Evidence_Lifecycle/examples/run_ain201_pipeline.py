"""Run the AIN-201.1 CPS Energy orchestration proof against AnchorInsight."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anchorinsight_pipeline import (
    CommercialIntelligencePipeline,
    PipelineRequest,
    ProfileRefreshStage,
    ReportRequestStage,
    RequestValidationStage,
    TargetResolutionStage,
)
from anchorinsight_registry import (
    CommercialIntelligenceRegistryService,
    OrganizationIntelligenceProfileService,
    ScoringDecisionService,
)


def main() -> int:
    database = ROOT / "data" / "anchorinsight.db"
    if not database.exists():
        print("Missing data/anchorinsight.db")
        print("Run first: python -m examples.seed_and_run_web")
        return 1

    registry = CommercialIntelligenceRegistryService(database)
    scoring = ScoringDecisionService(registry)
    profiles = OrganizationIntelligenceProfileService(registry, scoring)

    pipeline = CommercialIntelligencePipeline(
        services={"registry": registry, "profiles": profiles},
        stages=[
            RequestValidationStage(),
            TargetResolutionStage(),
            ProfileRefreshStage(),
            ReportRequestStage(),
        ],
        receipt_directory=ROOT / "data" / "pipeline_receipts",
    )
    request = PipelineRequest(
        workspace_id="SLS-DEMO-001",
        organization_identifier="COF-ORG-2026-001",
        requested_by="Ricky Jarnagin",
        research_objective=(
            "Identify evidence of infrastructure modernization, communications "
            "investment, grid technology programs, or related commercial signals "
            "announced by CPS Energy within the past 24 months."
        ),
        requested_outputs=("Organization Profile",),
        priority="High",
    )
    receipt = pipeline.run(request)
    print(json.dumps(receipt.to_dict(), indent=2))
    return 0 if receipt.status.value == "Completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
