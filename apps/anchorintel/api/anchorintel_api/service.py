"""Business-capability services for the complete S.P.A.T.I.A.L. lifecycle."""

from __future__ import annotations

import hashlib
import mimetypes
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from spatial_engine.engine import InputError, SpatialEngine
from spatial_engine.report import render_markdown

from .errors import ApiError
from .knowledge import KnowledgeModuleRegistry, execute_module, sha256_json
from .repository import Repository


EVIDENCE_STATES = {"V", "S", "A", "U", "D"}
PROMOTION = {"A": "S", "S": "V"}
PROMOTION_RANK = {"U": 0, "D": 0, "A": 1, "S": 2, "V": 3}
EVIDENCE_TYPES = {
    "Document",
    "Dataset",
    "Web Source",
    "Field Observation",
    "Photograph",
    "Correspondence",
    "Regulatory Record",
    "Financial Record",
    "Technical Record",
    "Other",
}
EVIDENCE_STATUSES = {
    "Collected",
    "Under Review",
    "Accepted",
    "Questioned",
    "Superseded",
    "Archived",
}
EVIDENCE_CONFIDENCE = {"Unknown", "Low", "Moderate", "High", "Verified"}
EVIDENCE_EDITABLE = {
    "title",
    "evidence_type",
    "source",
    "source_date",
    "date_collected",
    "description",
    "evidence_status",
    "evidence_confidence",
    "notes",
}
EVIDENCE_CREATE_FIELDS = EVIDENCE_EDITABLE | {"evidence_id"}
DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024
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
        if key
        not in {
            "internal_id",
            "lifecycle_state",
            "archived",
            "archived_at",
            "revision",
            "created_at",
            "updated_at",
        }
    }


class AnchorIntelService:
    def __init__(
        self,
        repository: Repository,
        engine: SpatialEngine | None = None,
        evidence_storage_dir: str | Path | None = None,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        module_registry: KnowledgeModuleRegistry | None = None,
        knowledge_module_dir: str | Path | None = None,
    ):
        self.repository = repository
        self.engine = engine or SpatialEngine()
        if evidence_storage_dir is None:
            if repository.database_path == ":memory:":
                evidence_storage_dir = Path("data/evidence-files")
            else:
                evidence_storage_dir = Path(repository.database_path).parent / "evidence-files"
        self.evidence_storage_dir = Path(evidence_storage_dir)
        self.evidence_storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self.module_registry = module_registry or KnowledgeModuleRegistry(
            knowledge_module_dir
        )
        for module in self.module_registry.list(active_only=False):
            self.repository.record_knowledge_module_loaded(module)

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
        record = self.repository.get_opportunity(opportunity_id, include_archived)
        active_evidence = self.repository.list_evidence(opportunity_id)
        knowledge_reviews = [
            self._annotate_knowledge_review(item)
            for item in self.repository.list_knowledge_reviews(opportunity_id)
        ]
        current_review = next(
            (item for item in knowledge_reviews if item["lifecycle_eligible"]), None
        )
        workflow = record.get("workflow")
        if isinstance(workflow, list):
            record["workflow"] = [
                {
                    **step,
                    "state": "complete" if active_evidence else "pending",
                }
                if step.get("key") == "evidence"
                else {
                    **step,
                    "state": "complete" if current_review else "pending",
                }
                if step.get("key") == "knowledge"
                else dict(step)
                for step in workflow
            ]
        record["active_evidence_count"] = len(active_evidence)
        record["knowledge_review_count"] = len(knowledge_reviews)
        record["current_knowledge_review"] = current_review
        return record

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

    @staticmethod
    def _validate_managed_evidence(record: dict[str, Any]) -> None:
        evidence_id = str(record.get("evidence_id", "")).strip()
        if evidence_id and not re.fullmatch(r"EV-\d{6}", evidence_id):
            raise ApiError(
                400,
                "invalid_evidence_id",
                "Managed evidence IDs must use EV- followed by six digits",
            )
        if not str(record.get("title", "")).strip():
            raise ApiError(400, "invalid_evidence", "title is required")
        evidence_type = str(record.get("evidence_type", "")).strip()
        if evidence_type not in EVIDENCE_TYPES:
            raise ApiError(
                400,
                "invalid_evidence_type",
                "evidence_type is not an allowed value",
                {"allowed": sorted(EVIDENCE_TYPES)},
            )
        status = str(record.get("evidence_status", "")).strip()
        if status not in EVIDENCE_STATUSES or status == "Archived":
            raise ApiError(
                400,
                "invalid_evidence_status",
                "evidence_status is not an allowed active value",
                {"allowed": sorted(EVIDENCE_STATUSES - {"Archived"})},
            )
        confidence = str(record.get("evidence_confidence", "")).strip()
        if confidence not in EVIDENCE_CONFIDENCE:
            raise ApiError(
                400,
                "invalid_evidence_confidence",
                "evidence_confidence is not an allowed value",
                {"allowed": sorted(EVIDENCE_CONFIDENCE)},
            )
        if not str(record.get("date_collected", "")).strip():
            raise ApiError(
                400, "invalid_date", "date_collected is required and must use YYYY-MM-DD"
            )
        for field_name in ("source_date", "date_collected"):
            value = str(record.get(field_name, "")).strip()
            if not value:
                continue
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ApiError(
                    400, "invalid_date", f"{field_name} must use YYYY-MM-DD"
                ) from exc

    @staticmethod
    def _validate_original_filename(filename: str) -> str:
        if (
            not filename
            or filename != filename.strip()
            or filename in {".", ".."}
            or "/" in filename
            or "\\" in filename
            or '"' in filename
            or any(ord(character) < 32 or ord(character) == 127 for character in filename)
            or Path(filename).name != filename
        ):
            raise ApiError(
                400,
                "unsafe_filename",
                "Uploaded filename must be a plain filename without paths or control characters",
            )
        return filename

    def _store_evidence_file(
        self, filename: str, content_type: str, content: bytes
    ) -> dict[str, Any]:
        safe_original = self._validate_original_filename(filename)
        if len(content) > self.max_file_size:
            raise ApiError(
                413,
                "file_too_large",
                f"Evidence files may not exceed {self.max_file_size} bytes",
            )
        suffix = Path(safe_original).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
            suffix = ""
        storage_name = f"{uuid.uuid4().hex}{suffix}"
        destination = self.evidence_storage_dir / storage_name
        with destination.open("xb") as stored_file:
            stored_file.write(content)
        file_type = content_type.strip() or mimetypes.guess_type(safe_original)[0] or "application/octet-stream"
        return {
            "file_name": safe_original,
            "file_type": file_type,
            "file_size": len(content),
            "storage_name": storage_name,
            "storage_location": f"evidence-files/{storage_name}",
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    def create_managed_evidence(
        self,
        opportunity_id: str,
        fields: dict[str, Any],
        actor: str,
        upload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.repository.get_opportunity(opportunity_id)
        unknown_fields = sorted(set(fields) - EVIDENCE_CREATE_FIELDS)
        if unknown_fields:
            raise ApiError(
                400,
                "invalid_evidence_fields",
                "Request contains unsupported evidence fields",
                {"fields": unknown_fields},
            )
        record = {key: str(value).strip() for key, value in fields.items()}
        record["opportunity_id"] = opportunity_id
        record.setdefault("evidence_id", "")
        record.setdefault("evidence_type", "Other")
        record.setdefault("source", "")
        record.setdefault("source_date", "")
        if not record.get("date_collected"):
            record["date_collected"] = date.today().isoformat()
        record.setdefault("description", "")
        record.setdefault("evidence_status", "Collected")
        record.setdefault("evidence_confidence", "Unknown")
        record.setdefault("notes", "")
        record["claim"] = record["description"] or record.get("title", "")
        record["state"] = "A"
        record["material"] = True
        stored: dict[str, Any] | None = None
        if upload and upload.get("filename"):
            stored = self._store_evidence_file(
                str(upload["filename"]),
                str(upload.get("content_type", "")),
                bytes(upload.get("content", b"")),
            )
            record.update(stored)
        else:
            record.update(
                {
                    "file_name": "",
                    "file_type": "",
                    "file_size": 0,
                    "storage_name": "",
                    "storage_location": "",
                    "sha256": "",
                }
            )
        self._validate_managed_evidence(record)
        try:
            created = self.repository.create_evidence(record, actor)
        except Exception:
            if stored:
                (self.evidence_storage_dir / stored["storage_name"]).unlink(
                    missing_ok=True
                )
            raise
        if stored:
            self.repository.record_evidence_file_uploaded(created["evidence_id"], actor)
        return created

    def get_managed_evidence(
        self, opportunity_id: str, evidence_id: str, include_archived: bool = True
    ) -> dict[str, Any]:
        self.repository.get_opportunity(opportunity_id, include_archived=True)
        return self.repository.get_evidence(
            evidence_id, opportunity_id=opportunity_id, include_archived=include_archived
        )

    def list_managed_evidence(
        self, opportunity_id: str, include_archived: bool = False
    ) -> list[dict[str, Any]]:
        self.repository.get_opportunity(opportunity_id, include_archived=True)
        return self.repository.list_evidence(opportunity_id, include_archived)

    def update_managed_evidence(
        self,
        opportunity_id: str,
        evidence_id: str,
        patch: dict[str, Any],
        actor: str,
        expected_revision: int | None,
    ) -> dict[str, Any]:
        unknown_fields = sorted(set(patch) - EVIDENCE_EDITABLE)
        if unknown_fields:
            raise ApiError(
                400,
                "invalid_evidence_fields",
                "Request contains unsupported evidence fields",
                {"fields": unknown_fields},
            )
        current = self.get_managed_evidence(opportunity_id, evidence_id)
        merged = clean_system_fields(current)
        for key in EVIDENCE_EDITABLE:
            if key in patch:
                merged[key] = str(patch[key]).strip()
        merged["opportunity_id"] = opportunity_id
        merged["evidence_id"] = evidence_id
        merged["claim"] = merged.get("description") or merged.get("title", "")
        self._validate_managed_evidence(merged)
        return self.repository.update_evidence(
            evidence_id,
            merged,
            actor,
            "evidence.metadata_updated",
            expected_revision,
        )

    def archive_managed_evidence(
        self,
        opportunity_id: str,
        evidence_id: str,
        actor: str,
        expected_revision: int | None,
    ) -> dict[str, Any]:
        return self.repository.archive_evidence(
            opportunity_id, evidence_id, actor, expected_revision
        )

    def evidence_file(
        self, opportunity_id: str, evidence_id: str
    ) -> tuple[Path, dict[str, Any]]:
        evidence = self.get_managed_evidence(opportunity_id, evidence_id)
        storage_name = str(evidence.get("storage_name", ""))
        if not storage_name or Path(storage_name).name != storage_name:
            raise ApiError(404, "evidence_file_not_found", "Evidence has no attached file")
        path = self.evidence_storage_dir / storage_name
        if not path.is_file():
            raise ApiError(404, "evidence_file_not_found", "Stored evidence file was not found")
        return path, evidence

    def list_knowledge_modules(self, active_only: bool = True) -> list[dict[str, Any]]:
        return self.module_registry.list(active_only=active_only)

    def get_knowledge_module(self, module_id: str) -> dict[str, Any]:
        return self.module_registry.get(module_id)

    @staticmethod
    def _evidence_trace(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "evidence_id": item["evidence_id"],
                "revision": item["revision"],
                "sha256": item.get("sha256", ""),
                "evidence_status": item.get("evidence_status", ""),
                "evidence_confidence": item.get("evidence_confidence", "Unknown"),
            }
            for item in sorted(records, key=lambda value: value["evidence_id"])
        ]

    def _knowledge_review_inputs(
        self, opportunity_id: str, module: dict[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], list[dict[str, Any]], str]:
        opportunity = self.repository.get_opportunity(opportunity_id)
        active_evidence = self.repository.list_evidence(opportunity_id)
        all_evidence = self.repository.list_evidence(
            opportunity_id, include_archived=True
        )
        archived_ids = sorted(
            item["evidence_id"] for item in all_evidence if item.get("archived")
        )
        trace = self._evidence_trace(active_evidence)
        evidence_snapshot = []
        for item in sorted(active_evidence, key=lambda value: value["evidence_id"]):
            clean = clean_system_fields(item)
            clean["revision"] = item["revision"]
            evidence_snapshot.append(clean)
        snapshot = {
            "module": {
                "module_id": module["module_id"],
                "version": module["version"],
                "integrity_hash": module["integrity_hash"],
            },
            "opportunity": {
                **clean_system_fields(opportunity),
                "revision": opportunity["revision"],
            },
            "active_evidence": evidence_snapshot,
            "evidence_trace": trace,
            "excluded_archived_evidence_ids": archived_ids,
        }
        return opportunity, active_evidence, archived_ids, trace, sha256_json(snapshot)

    def run_knowledge_review(
        self,
        opportunity_id: str,
        module_id: str,
        actor: str,
        review_status: str = "Completed",
        supersedes_review_id: str | None = None,
    ) -> dict[str, Any]:
        module = self.module_registry.get(module_id)
        if module["status"] != "Active":
            raise ApiError(
                409,
                "knowledge_module_inactive",
                f"Knowledge Module {module_id} is not active",
            )
        opportunity, active_evidence, archived_ids, trace, snapshot_hash = (
            self._knowledge_review_inputs(opportunity_id, module)
        )
        try:
            output = execute_module(module, opportunity, active_evidence, archived_ids)
        except ApiError as exc:
            failed_output = {
                "module_id": module_id,
                "module_version": module["version"],
                "confidence": "Unknown",
                "findings": [],
                "assumptions": [],
                "unknowns": [],
                "risks": [],
                "missing_evidence": [],
                "consumed_evidence_ids": [item["evidence_id"] for item in trace],
                "failure": {"code": exc.code, "message": exc.message},
            }
            failed = self.repository.create_knowledge_review(
                {
                    "opportunity_id": opportunity_id,
                    "module_id": module_id,
                    "module_version": module["version"],
                    "module_integrity_hash": module["integrity_hash"],
                    "opportunity_revision": opportunity["revision"],
                    "evidence_trace": trace,
                    "input_snapshot_hash": snapshot_hash,
                    "output": failed_output,
                    "output_hash": sha256_json(failed_output),
                    "review_status": "Incomplete",
                    "confidence": "Unknown",
                    "reviewer_source": actor,
                },
                actor,
                supersedes_review_id,
            )
            self.repository.record_knowledge_review_failed(failed, actor, exc)
            raise ApiError(
                exc.status,
                exc.code,
                exc.message,
                {**exc.details, "failed_review_id": failed["review_id"]},
            ) from exc
        record = {
            "opportunity_id": opportunity_id,
            "module_id": module_id,
            "module_version": module["version"],
            "module_integrity_hash": module["integrity_hash"],
            "opportunity_revision": opportunity["revision"],
            "evidence_trace": trace,
            "input_snapshot_hash": snapshot_hash,
            "output": output,
            "output_hash": sha256_json(output),
            "review_status": review_status,
            "confidence": output["confidence"],
            "reviewer_source": actor,
        }
        result = self.repository.create_knowledge_review(
            record, actor, supersedes_review_id
        )
        return self._annotate_knowledge_review(result)

    def _annotate_knowledge_review(
        self, record: dict[str, Any]
    ) -> dict[str, Any]:
        review = dict(record)
        reasons: list[str] = []
        try:
            opportunity = self.repository.get_opportunity(
                review["opportunity_id"], include_archived=True
            )
        except ApiError:
            reasons.append("The opportunity is no longer available.")
            opportunity = None
        if opportunity is not None:
            if opportunity.get("archived"):
                reasons.append("The opportunity is archived.")
            if opportunity.get("revision") != review.get("opportunity_revision"):
                reasons.append("The opportunity revision has changed.")
            current_trace = self._evidence_trace(
                self.repository.list_evidence(review["opportunity_id"])
            )
            if current_trace != review.get("evidence_trace", []):
                reasons.append("The active evidence trace has changed.")
        try:
            module = self.module_registry.get(review["module_id"])
        except ApiError:
            reasons.append("The reviewed Knowledge Module is unavailable.")
        else:
            if module["status"] != "Active":
                reasons.append("The reviewed Knowledge Module is not active.")
            if module["version"] != review.get("module_version"):
                reasons.append("The Knowledge Module version has changed.")
            if module["integrity_hash"] != review.get("module_integrity_hash"):
                reasons.append("The Knowledge Module integrity hash has changed.")
        review["stale"] = bool(reasons)
        review["stale_reasons"] = reasons
        review["lifecycle_eligible"] = (
            review.get("review_status") == "Completed" and not reasons
        )
        output = review.get("output", {})
        review["summary"] = {
            "finding_count": len(output.get("findings", [])),
            "assumption_count": len(output.get("assumptions", [])),
            "unknown_count": len(output.get("unknowns", [])),
            "risk_count": len(output.get("risks", [])),
            "missing_evidence_count": len(output.get("missing_evidence", [])),
        }
        if reasons and review.get("review_status") not in {"Superseded", "Archived"}:
            self.repository.record_knowledge_review_stale(review, reasons)
        return review

    def list_knowledge_reviews(self, opportunity_id: str) -> list[dict[str, Any]]:
        return [
            self._annotate_knowledge_review(item)
            for item in self.repository.list_knowledge_reviews(opportunity_id)
        ]

    def get_knowledge_review(
        self, opportunity_id: str, review_id: str
    ) -> dict[str, Any]:
        return self._annotate_knowledge_review(
            self.repository.get_knowledge_review(opportunity_id, review_id)
        )

    def complete_knowledge_review(
        self,
        opportunity_id: str,
        review_id: str,
        actor: str,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        current = self.get_knowledge_review(opportunity_id, review_id)
        if current["stale"]:
            raise ApiError(
                409,
                "knowledge_review_stale",
                "A stale review cannot be completed; run the module again",
                {"reasons": current["stale_reasons"]},
            )
        result = self.repository.complete_knowledge_review(
            opportunity_id, review_id, actor, expected_revision
        )
        return self._annotate_knowledge_review(result)

    def supersede_knowledge_review(
        self, opportunity_id: str, review_id: str, actor: str
    ) -> dict[str, Any]:
        current = self.repository.get_knowledge_review(opportunity_id, review_id)
        return self.run_knowledge_review(
            opportunity_id,
            current["module_id"],
            actor,
            review_status="Completed",
            supersedes_review_id=review_id,
        )

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
