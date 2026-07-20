"""Business-capability services for the complete S.P.A.T.I.A.L. lifecycle."""

from __future__ import annotations

from datetime import date
from typing import Any

from spatial_engine.engine import InputError, SpatialEngine
from spatial_engine.report import render_markdown

from .errors import ApiError
from .repository import Repository


EVIDENCE_STATES = {"V", "S", "A", "U", "D"}
PROMOTION = {"A": "S", "S": "V"}
PROMOTION_RANK = {"U": 0, "D": 0, "A": 1, "S": 2, "V": 3}
OPPORTUNITY_REQUIRED = ("title", "geography", "infrastructure_class")
OPPORTUNITY_EDITABLE = (
    "title",
    "organization",
    "sector",
    "status",
    "description",
    "geography",
    "infrastructure_class",
)


def clean_system_fields(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.items()
        if key not in {"lifecycle_state", "archived", "revision", "created_at", "updated_at"}
    }


class AnchorIntelService:
    def __init__(self, repository: Repository, engine: SpatialEngine | None = None):
        self.repository = repository
        self.engine = engine or SpatialEngine()

    @staticmethod
    def _validate_opportunity(record: dict[str, Any]) -> None:
        if "evidence" in record:
            raise ApiError(400, "embedded_evidence", "Create evidence through /v1/evidence")
        missing = [key for key in OPPORTUNITY_REQUIRED if not str(record.get(key, "")).strip()]
        if missing:
            raise ApiError(400, "invalid_opportunity", "Missing required opportunity fields", {"fields": missing})

    def create_opportunity(self, record: dict[str, Any], actor: str) -> dict[str, Any]:
        self._validate_opportunity(record)
        record = dict(record)
        record.setdefault("problem_statement", "")
        record.setdefault("analyst", actor)
        record.setdefault("assessment_date", "")
        record.setdefault("dimensions", {})
        record.setdefault("gates", {})
        record.setdefault("fatal_constraints", [])
        record.setdefault("known_limitations", [])
        record.setdefault("lifecycle", {})
        return self.repository.create_opportunity(record, actor)

    def get_opportunity(
        self, opportunity_id: str, include_archived: bool = False
    ) -> dict[str, Any]:
        return self.repository.get_opportunity(opportunity_id, include_archived)

    def list_opportunities(self, include_archived: bool = False) -> list[dict[str, Any]]:
        return self.repository.list_opportunities(include_archived)

    def update_opportunity(
        self,
        opportunity_id: str,
        record: dict[str, Any],
        actor: str,
        expected_revision: int | None,
    ) -> dict[str, Any]:
        self._validate_opportunity(record)
        return self.repository.update_opportunity(
            opportunity_id, clean_system_fields(record), actor, expected_revision
        )

    def edit_opportunity(
        self,
        opportunity_id: str,
        fields: dict[str, Any],
        actor: str,
        expected_revision: int | None,
    ) -> dict[str, Any]:
        """Merge business-facing form fields without losing assessment inputs."""

        current = self.repository.get_opportunity(opportunity_id)
        merged = clean_system_fields(current)
        for key in OPPORTUNITY_EDITABLE:
            if key in fields:
                merged[key] = str(fields[key]).strip()
        if "description" in fields:
            merged["problem_statement"] = str(fields["description"]).strip()
        self._validate_opportunity(merged)
        return self.repository.update_opportunity(
            opportunity_id, merged, actor, expected_revision
        )

    def archive_opportunity(self, opportunity_id: str, actor: str) -> dict[str, Any]:
        return self.repository.archive_opportunity(opportunity_id, actor)

    @staticmethod
    def _validate_evidence(record: dict[str, Any]) -> None:
        if not str(record.get("opportunity_id", "")).strip():
            raise ApiError(400, "invalid_evidence", "opportunity_id is required")
        if not str(record.get("claim", "")).strip():
            raise ApiError(400, "invalid_evidence", "claim is required")
        state = str(record.get("state", "")).upper()
        if state not in EVIDENCE_STATES:
            raise ApiError(400, "invalid_evidence_state", "state must be V, S, A, U, or D")
        if state == "V" and not str(record.get("source", "")).strip():
            raise ApiError(400, "verified_source_required", "Verified evidence requires a source")

    def create_evidence(self, record: dict[str, Any], actor: str) -> dict[str, Any]:
        record = dict(record)
        record["state"] = str(record.get("state", "")).upper()
        record.setdefault("material", True)
        self._validate_evidence(record)
        return self.repository.create_evidence(record, actor)

    def get_evidence(self, evidence_id: str) -> dict[str, Any]:
        return self.repository.get_evidence(evidence_id)

    def list_evidence(self, opportunity_id: str | None = None) -> list[dict[str, Any]]:
        return self.repository.list_evidence(opportunity_id)

    def patch_evidence(
        self,
        evidence_id: str,
        patch: dict[str, Any],
        actor: str,
        expected_revision: int | None,
    ) -> dict[str, Any]:
        current = self.repository.get_evidence(evidence_id)
        merged = clean_system_fields(current)
        merged.update(patch)
        merged["evidence_id"] = evidence_id
        merged["opportunity_id"] = current["opportunity_id"]
        merged["state"] = str(merged.get("state", "")).upper()
        old_state = current["state"]
        new_state = merged["state"]
        if (
            new_state in {"S", "V"}
            and PROMOTION_RANK.get(new_state, -1) > PROMOTION_RANK.get(old_state, -1)
        ):
            raise ApiError(
                409,
                "verification_required",
                "Evidence promotion must use POST /v1/evidence/{id}/verify",
            )
        self._validate_evidence(merged)
        return self.repository.update_evidence(
            evidence_id, merged, actor, "evidence.reclassified", expected_revision
        )

    def verify_evidence(
        self,
        evidence_id: str,
        verification: dict[str, Any],
        actor: str,
        expected_revision: int | None,
    ) -> dict[str, Any]:
        current = self.repository.get_evidence(evidence_id)
        old_state = current["state"]
        if old_state not in PROMOTION:
            raise ApiError(
                409,
                "invalid_evidence_transition",
                f"Evidence in state {old_state} cannot be promoted; reclassify it first if appropriate",
            )
        note = str(verification.get("verification_note", "")).strip()
        source = str(verification.get("source", current.get("source", ""))).strip()
        if not note or not source:
            raise ApiError(
                400,
                "verification_support_required",
                "verification_note and source are required for evidence promotion",
            )
        merged = clean_system_fields(current)
        merged.update({key: value for key, value in verification.items() if key != "verification_note"})
        merged["evidence_id"] = evidence_id
        merged["opportunity_id"] = current["opportunity_id"]
        merged["state"] = PROMOTION[old_state]
        merged["source"] = source
        prior_notes = str(merged.get("notes", "")).strip()
        merged["notes"] = f"{prior_notes}\nVerification: {note}".strip()
        self._validate_evidence(merged)
        return self.repository.update_evidence(
            evidence_id, merged, actor, "evidence.promoted", expected_revision
        )

    def run_assessment(
        self,
        opportunity_id: str,
        actor: str,
        assessment_date: str | None = None,
        event_type: str = "run",
        reason: str = "Assessment requested",
        supersedes_assessment_id: str | None = None,
    ) -> dict[str, Any]:
        opportunity = self.repository.get_opportunity(opportunity_id)
        payload = clean_system_fields(opportunity)
        payload["assessment_date"] = assessment_date or date.today().isoformat()
        payload["evidence"] = [
            {
                key: value
                for key, value in item.items()
                if key not in {"opportunity_id", "revision", "created_at", "updated_at"}
            }
            for item in self.repository.list_evidence(opportunity_id)
        ]
        try:
            result_obj = self.engine.analyze(payload)
        except InputError as exc:
            raise ApiError(
                422,
                "assessment_input_incomplete",
                "Opportunity and evidence do not satisfy the S.P.A.T.I.A.L. engine contract",
                {"engine_error": str(exc)},
            ) from exc
        result = result_obj.to_dict()
        markdown = render_markdown(result_obj)
        return self.repository.create_assessment(
            opportunity_id,
            payload,
            result,
            markdown,
            actor,
            event_type,
            reason,
            supersedes_assessment_id,
        )

    def get_assessment(self, assessment_id: str) -> dict[str, Any]:
        return self.repository.get_assessment(assessment_id, include_report=False)

    def report_json(self, assessment_id: str) -> dict[str, Any]:
        assessment = self.repository.get_assessment(assessment_id, include_report=False)
        return assessment["result"]

    def report_markdown(self, assessment_id: str) -> str:
        assessment = self.repository.get_assessment(assessment_id, include_report=True)
        return assessment["report_markdown"]

    def reviews_due(self, as_of: str | None = None) -> list[dict[str, Any]]:
        try:
            cutoff = date.fromisoformat(as_of) if as_of else date.today()
        except ValueError as exc:
            raise ApiError(400, "invalid_date", "as_of must use YYYY-MM-DD") from exc
        due: list[dict[str, Any]] = []
        for opportunity in self.repository.list_opportunities():
            review_date = opportunity.get("lifecycle", {}).get("review_date", "")
            try:
                parsed = date.fromisoformat(review_date)
            except ValueError:
                continue
            if parsed <= cutoff:
                due.append(
                    {
                        "opportunity_id": opportunity["opportunity_id"],
                        "title": opportunity["title"],
                        "lifecycle_state": opportunity["lifecycle_state"],
                        "review_date": review_date,
                        "overdue": parsed < cutoff,
                    }
                )
        return sorted(due, key=lambda value: (value["review_date"], value["opportunity_id"]))

    def list_state(self, state: str) -> list[dict[str, Any]]:
        return self.repository.list_by_state(state)

    def revalidate(self, request: dict[str, Any], actor: str) -> dict[str, Any]:
        opportunity_id = str(request.get("opportunity_id", "")).strip()
        reason = str(request.get("reason", "")).strip()
        if not opportunity_id or not reason:
            raise ApiError(400, "invalid_revalidation", "opportunity_id and reason are required")
        latest = self.repository.latest_assessment(opportunity_id)
        if latest is None:
            raise ApiError(409, "no_prior_assessment", "Run an initial assessment before revalidation")

        lifecycle = request.get("lifecycle")
        if lifecycle is not None:
            opportunity = self.repository.get_opportunity(opportunity_id)
            updated = clean_system_fields(opportunity)
            current_lifecycle = dict(updated.get("lifecycle", {}))
            current_lifecycle.update(lifecycle)
            updated["lifecycle"] = current_lifecycle
            self._validate_opportunity(updated)
            self.repository.update_opportunity(
                opportunity_id, updated, actor, opportunity["revision"]
            )

        return self.run_assessment(
            opportunity_id=opportunity_id,
            actor=actor,
            assessment_date=request.get("assessment_date"),
            event_type="revalidated",
            reason=reason,
            supersedes_assessment_id=latest["assessment_id"],
        )

    def audit(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.repository.list_audit(limit)
