"""Business-capability services for the complete S.P.A.T.I.A.L. lifecycle."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from spatial_engine.engine import InputError, SpatialEngine
from spatial_engine.report import render_markdown

from .assessment import (
    ADAPTER_VERSION,
    ENGINE_VERSION,
    build_engine_input,
    build_operational_result,
)
from .archive import (
    ARCHIVE_FORMAT_VERSION,
    build_archive_package,
    canonical_json as archive_json,
    sha256_bytes as archive_sha256,
    verify_archive_package,
)
from .dossier import (
    DOSSIER_FORMAT_VERSION,
    build_artifacts,
    build_input_snapshot,
    render_json,
    sha256_json as dossier_sha256_json,
)
from .errors import ApiError
from .knowledge import KnowledgeModuleRegistry, execute_module, sha256_json
from .repository import Repository, utcnow


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
        archive_storage_dir: str | Path | None = None,
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
        if archive_storage_dir is None:
            if repository.database_path == ":memory:":
                archive_storage_dir = Path("data/archives")
            else:
                archive_storage_dir = Path(repository.database_path).parent / "archives"
        self.archive_storage_dir = Path(archive_storage_dir)
        self.archive_storage_dir.mkdir(parents=True, exist_ok=True)
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
        assessments = [
            self._annotate_operational_assessment(item)
            for item in self.repository.list_assessments(
                opportunity_id, assessment_kind="spatial_lifecycle"
            )
        ]
        current_assessment = next(
            (item for item in assessments if item["lifecycle_eligible"]), None
        )
        dossiers = [
            self._annotate_dossier(item)
            for item in self.repository.list_dossiers(opportunity_id)
        ]
        current_dossier = next(
            (item for item in dossiers if item["lifecycle_eligible"]), None
        )
        archives = self.repository.list_archives(opportunity_id)
        current_archive = next(
            (item for item in archives if item.get("archive_status") == "Archived"),
            None,
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
                else {
                    **step,
                    "state": "complete" if current_assessment else "pending",
                }
                if step.get("key") == "assessment"
                else {
                    **step,
                    "state": "complete" if current_dossier else "pending",
                }
                if step.get("key") == "dossier"
                else {
                    **step,
                    "state": "complete" if current_archive else "pending",
                }
                if step.get("key") == "archive"
                else dict(step)
                for step in workflow
            ]
        record["active_evidence_count"] = len(active_evidence)
        record["knowledge_review_count"] = len(knowledge_reviews)
        record["current_knowledge_review"] = current_review
        record["assessment_count"] = len(assessments)
        record["current_assessment"] = current_assessment
        record["dossier_count"] = len(dossiers)
        record["current_dossier"] = current_dossier
        record["archive_count"] = len(archives)
        record["current_archive"] = current_archive
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

        current = self.repository.get_opportunity(
            opportunity_id, include_archived=True
        )
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

    @staticmethod
    def _assessment_review_snapshot(review: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in review.items()
            if key not in {"stale", "stale_reasons", "lifecycle_eligible", "summary"}
        }

    def assessment_readiness(
        self, opportunity_id: str, review_id: str | None = None
    ) -> dict[str, Any]:
        """Return bounded readiness without persisting or advancing lifecycle state."""

        opportunity = self.repository.get_opportunity(
            opportunity_id, include_archived=True
        )
        errors: list[str] = []
        warnings: list[str] = []
        if opportunity.get("archived"):
            errors.append("The opportunity is archived.")
        active_evidence = self.repository.list_evidence(opportunity_id)
        if not active_evidence:
            errors.append("At least one active evidence record is required.")

        selected_review: dict[str, Any] | None = None
        if review_id:
            selected_review = self.get_knowledge_review(opportunity_id, review_id)
        else:
            reviews = self.list_knowledge_reviews(opportunity_id)
            selected_review = next(
                (item for item in reviews if item["lifecycle_eligible"]), None
            )
            if selected_review is None:
                selected_review = next(
                    (
                        item
                        for item in reviews
                        if item.get("review_status") not in {"Superseded", "Archived"}
                    ),
                    None,
                )
        if selected_review is None:
            errors.append("A completed current Knowledge Review is required.")
        else:
            if selected_review.get("review_status") != "Completed":
                errors.append("The selected Knowledge Review is not completed.")
            if selected_review.get("stale"):
                errors.extend(selected_review.get("stale_reasons", []))

        derivation: dict[str, Any] | None = None
        input_hash = ""
        if selected_review is not None and active_evidence:
            try:
                module = self.module_registry.get(selected_review["module_id"])
                payload, derivation = build_engine_input(
                    opportunity, active_evidence, selected_review, module
                )
                input_hash = sha256_json(payload)
                self.engine.analyze(payload)
            except (ApiError, InputError) as exc:
                if isinstance(exc, ApiError):
                    errors.append(exc.message)
                else:
                    errors.append(
                        "The derived inputs do not satisfy the S.P.A.T.I.A.L. engine contract: "
                        + str(exc)
                    )
            else:
                output = selected_review.get("output", {})
                if output.get("unknowns"):
                    warnings.append(
                        f"The current Knowledge Review contains {len(output['unknowns'])} material unknown(s)."
                    )
                if output.get("missing_evidence"):
                    warnings.append(
                        f"The current Knowledge Review identifies {len(output['missing_evidence'])} missing-evidence item(s)."
                    )
                warnings.append(
                    "Conservative adapter defaults are used for engine dimensions not covered by the current Knowledge Module."
                )
        return {
            "opportunity_id": opportunity_id,
            "ready": not errors,
            "errors": errors,
            "warnings": warnings,
            "knowledge_review": selected_review,
            "engine_version": ENGINE_VERSION,
            "adapter_version": ADAPTER_VERSION,
            "input_hash": input_hash,
            "derivation": derivation,
            "bounded_execution_notice": (
                "This run uses only persisted local records. It does not browse the internet, "
                "invoke an external AI model, create new evidence, or independently verify evidence."
            ),
        }

    def run_spatial_assessment(
        self,
        opportunity_id: str,
        actor: str,
        review_id: str | None = None,
        reason: str = "S.P.A.T.I.A.L. assessment requested",
    ) -> dict[str, Any]:
        readiness = self.assessment_readiness(opportunity_id, review_id)
        review = readiness.get("knowledge_review")
        if review is not None and (
            review.get("stale")
            or review.get("review_status") in {"Superseded", "Archived"}
        ):
            reasons = list(review.get("stale_reasons", []))
            if review.get("review_status") in {"Superseded", "Archived"}:
                reasons.append("The selected Knowledge Review is no longer active.")
            raise ApiError(
                409,
                "knowledge_review_stale",
                "The selected Knowledge Review is stale; rerun it before assessment",
                {"reasons": reasons},
            )
        if review is not None and review.get("review_status") != "Completed":
            raise ApiError(
                409,
                "knowledge_review_incomplete",
                "The selected Knowledge Review must be completed before assessment",
            )
        if not readiness["ready"]:
            raise ApiError(
                409,
                "assessment_not_ready",
                "The persisted lifecycle inputs are not ready for S.P.A.T.I.A.L. assessment",
                {"reasons": readiness["errors"]},
            )
        assert review is not None
        opportunity = self.repository.get_opportunity(opportunity_id)
        evidence = self.repository.list_evidence(opportunity_id)
        module = self.module_registry.get(review["module_id"])
        engine_input, derivation = build_engine_input(
            opportunity, evidence, review, module
        )
        evidence_trace = self._evidence_trace(evidence)
        try:
            result_obj = self.engine.analyze(engine_input)
        except InputError as exc:
            raise ApiError(
                422,
                "assessment_input_incomplete",
                "The replayable inputs do not satisfy the S.P.A.T.I.A.L. engine contract",
                {"engine_error": str(exc)},
            ) from exc
        operational_result = build_operational_result(
            result_obj.to_dict(), review, evidence_trace, derivation
        )
        review_snapshot = self._assessment_review_snapshot(review)
        evidence_snapshot = [
            {**clean_system_fields(item), "revision": item["revision"]}
            for item in sorted(evidence, key=lambda value: value["evidence_id"])
        ]
        opportunity_snapshot = {
            **clean_system_fields(opportunity),
            "revision": opportunity["revision"],
        }
        module_snapshot = {
            "module_id": module["module_id"],
            "version": module["version"],
            "integrity_hash": module["integrity_hash"],
            "effective_date": module["effective_date"],
            "review_date": module["review_date"],
        }
        provenance = {
            "contract_version": "anchorintel-assessment-provenance/1.0",
            "opportunity": {
                "opportunity_id": opportunity_id,
                "revision": opportunity["revision"],
            },
            "evidence_trace": evidence_trace,
            "knowledge_review": {
                "review_id": review["review_id"],
                "revision": review["revision"],
                "output_hash": review.get("output_hash", ""),
                "module_id": review["module_id"],
                "module_version": review["module_version"],
                "module_integrity_hash": review.get("module_integrity_hash", ""),
            },
            "engine": {
                "name": "S.P.A.T.I.A.L.",
                "version": ENGINE_VERSION,
            },
            "adapter": {
                "name": "AnchorIntel S.P.A.T.I.A.L. adapter",
                "version": ADAPTER_VERSION,
            },
            "engine_input_hash": sha256_json(engine_input),
        }
        replay_hash = sha256_json(
            {"provenance": provenance, "result": operational_result}
        )
        operational_result["replay_hash"] = replay_hash
        input_snapshot = {
            "contract_version": "anchorintel-assessment-snapshot/1.0",
            "opportunity": opportunity_snapshot,
            "active_evidence": evidence_snapshot,
            "knowledge_review": review_snapshot,
            "knowledge_module": module_snapshot,
            "engine_input": engine_input,
            "input_derivation": derivation,
        }
        current = next(
            (
                item
                for item in self.list_operational_assessments(opportunity_id)
                if item.get("lifecycle_eligible")
            ),
            None,
        )
        result = self.repository.create_assessment(
            opportunity_id,
            input_snapshot,
            operational_result,
            render_markdown(result_obj),
            actor,
            "spatial_completed",
            reason,
            current["assessment_id"] if current else None,
            assessment_kind="spatial_lifecycle",
            knowledge_review_id=review["review_id"],
            engine_version=ENGINE_VERSION,
            adapter_version=ADAPTER_VERSION,
            replay_hash=replay_hash,
            provenance=provenance,
        )
        return self._annotate_operational_assessment(result)

    def _annotate_operational_assessment(
        self, record: dict[str, Any]
    ) -> dict[str, Any]:
        assessment = dict(record)
        if assessment.get("assessment_kind") != "spatial_lifecycle":
            assessment["stale"] = False
            assessment["stale_reasons"] = []
            assessment["lifecycle_eligible"] = False
            return assessment
        reasons: list[str] = []
        provenance = assessment.get("provenance", {})
        try:
            opportunity = self.repository.get_opportunity(
                assessment["opportunity_id"], include_archived=True
            )
        except ApiError:
            reasons.append("The opportunity is no longer available.")
            opportunity = None
        if opportunity is not None:
            if opportunity.get("revision") != provenance.get("opportunity", {}).get(
                "revision"
            ):
                reasons.append("The opportunity revision has changed.")
            current_trace = self._evidence_trace(
                self.repository.list_evidence(assessment["opportunity_id"])
            )
            if current_trace != provenance.get("evidence_trace", []):
                reasons.append("The active evidence trace has changed.")
        try:
            review = self.get_knowledge_review(
                assessment["opportunity_id"], assessment["knowledge_review_id"]
            )
        except ApiError:
            reasons.append("The source Knowledge Review is unavailable.")
            review = None
        if review is not None:
            expected_review = provenance.get("knowledge_review", {})
            if not review.get("lifecycle_eligible"):
                reasons.append("The source Knowledge Review is no longer current.")
            if review.get("revision") != expected_review.get("revision"):
                reasons.append("The source Knowledge Review revision has changed.")
            if review.get("output_hash") != expected_review.get("output_hash"):
                reasons.append("The source Knowledge Review output hash has changed.")
        if assessment.get("engine_version") != ENGINE_VERSION:
            reasons.append("The S.P.A.T.I.A.L. engine version has changed.")
        if assessment.get("adapter_version") != ADAPTER_VERSION:
            reasons.append("The AnchorIntel assessment adapter version has changed.")
        successor_id = self.repository.assessment_successor_id(
            assessment["assessment_id"]
        )
        if successor_id:
            reasons.append(f"A newer assessment ({successor_id}) supersedes this result.")
        assessment["stale"] = bool(reasons)
        assessment["stale_reasons"] = list(dict.fromkeys(reasons))
        assessment["lifecycle_eligible"] = not reasons
        if reasons:
            self.repository.record_assessment_stale(
                assessment, assessment["stale_reasons"]
            )
        return assessment

    def list_operational_assessments(
        self, opportunity_id: str
    ) -> list[dict[str, Any]]:
        return [
            self._annotate_operational_assessment(item)
            for item in self.repository.list_assessments(
                opportunity_id, assessment_kind="spatial_lifecycle"
            )
        ]

    def get_operational_assessment(
        self, opportunity_id: str, assessment_id: str
    ) -> dict[str, Any]:
        assessment = self.repository.get_assessment(
            assessment_id, include_report=False
        )
        if (
            assessment["opportunity_id"] != opportunity_id
            or assessment.get("assessment_kind") != "spatial_lifecycle"
        ):
            raise ApiError(
                404,
                "assessment_not_found",
                f"Assessment {assessment_id} was not found for {opportunity_id}",
            )
        return self._annotate_operational_assessment(assessment)

    def replay_operational_assessment(
        self, opportunity_id: str, assessment_id: str, actor: str
    ) -> dict[str, Any]:
        assessment = self.repository.get_assessment(
            assessment_id, include_report=False, include_snapshot=True
        )
        if (
            assessment["opportunity_id"] != opportunity_id
            or assessment.get("assessment_kind") != "spatial_lifecycle"
        ):
            raise ApiError(
                404,
                "assessment_not_found",
                f"Assessment {assessment_id} was not found for {opportunity_id}",
            )
        snapshot = assessment["input_snapshot"]
        try:
            result_obj = self.engine.analyze(snapshot["engine_input"])
        except (InputError, KeyError) as exc:
            raise ApiError(
                409,
                "assessment_replay_failed",
                "The stored assessment snapshot cannot be replayed",
                {"reason": str(exc)},
            ) from exc
        recomputed = build_operational_result(
            result_obj.to_dict(),
            snapshot["knowledge_review"],
            assessment.get("provenance", {}).get("evidence_trace", []),
            snapshot["input_derivation"],
        )
        recomputed_hash = sha256_json(
            {"provenance": assessment["provenance"], "result": recomputed}
        )
        stored_without_hash = dict(assessment["result"])
        stored_without_hash.pop("replay_hash", None)
        replay = {
            "assessment_id": assessment_id,
            "opportunity_id": opportunity_id,
            "match": (
                recomputed_hash == assessment.get("replay_hash")
                and recomputed == stored_without_hash
            ),
            "stored_replay_hash": assessment.get("replay_hash"),
            "recomputed_replay_hash": recomputed_hash,
            "engine_version": ENGINE_VERSION,
            "stored_engine_version": assessment.get("engine_version"),
            "adapter_version": ADAPTER_VERSION,
            "stored_adapter_version": assessment.get("adapter_version"),
            "result": recomputed,
        }
        self.repository.record_assessment_replayed(assessment, actor, replay)
        return replay

    def dossier_readiness(
        self, opportunity_id: str, assessment_id: str | None = None
    ) -> dict[str, Any]:
        """Evaluate persisted report inputs without rerunning upstream engines."""

        opportunity = self.repository.get_opportunity(
            opportunity_id, include_archived=True
        )
        errors: list[str] = []
        warnings: list[str] = []
        if opportunity.get("archived"):
            errors.append("The opportunity is archived.")
        if assessment_id:
            try:
                assessment = self.get_operational_assessment(
                    opportunity_id, assessment_id
                )
            except ApiError as exc:
                if exc.status == 404:
                    assessment = None
                    errors.append(exc.message)
                else:
                    raise
        else:
            assessment = next(
                (
                    item
                    for item in self.list_operational_assessments(opportunity_id)
                    if item.get("lifecycle_eligible")
                ),
                None,
            )
            if assessment is None:
                errors.append("A current S.P.A.T.I.A.L. assessment is required.")
        review: dict[str, Any] | None = None
        if assessment is not None:
            if assessment.get("stale"):
                errors.extend(assessment.get("stale_reasons", []))
            try:
                review = self.get_knowledge_review(
                    opportunity_id, str(assessment.get("knowledge_review_id", ""))
                )
            except ApiError as exc:
                errors.append(exc.message)
            if review is not None and not review.get("lifecycle_eligible"):
                errors.extend(review.get("stale_reasons", []))
        evidence = self.repository.list_evidence(opportunity_id)
        if not evidence:
            errors.append("At least one active evidence record is required.")
        snapshot: dict[str, Any] | None = None
        input_hash = ""
        if assessment is not None and review is not None and not errors:
            snapshot = build_input_snapshot(
                opportunity, evidence, review, assessment
            )
            input_hash = dossier_sha256_json(snapshot)
            if assessment.get("result", {}).get("warnings"):
                warnings.extend(assessment["result"]["warnings"])
            if review.get("output", {}).get("missing_evidence"):
                warnings.append(
                    "The source Knowledge Review contains missing-evidence items; "
                    "the dossier will reproduce them without reinterpretation."
                )
        return {
            "opportunity_id": opportunity_id,
            "ready": not errors,
            "errors": list(dict.fromkeys(errors)),
            "warnings": list(dict.fromkeys(warnings)),
            "assessment": assessment,
            "knowledge_review": review,
            "active_evidence_count": len(evidence),
            "input_hash": input_hash,
            "input_snapshot": snapshot,
            "format_version": DOSSIER_FORMAT_VERSION,
            "bounded_execution_notice": (
                "This dossier uses only persisted local records. It does not browse the "
                "internet, invoke an external AI model, regenerate evidence, rerun the "
                "Knowledge Module, or rerun the S.P.A.T.I.A.L. assessment."
            ),
        }

    def generate_dossier(
        self,
        opportunity_id: str,
        actor: str,
        assessment_id: str | None = None,
    ) -> dict[str, Any]:
        readiness = self.dossier_readiness(opportunity_id, assessment_id)
        if not readiness["ready"]:
            raise ApiError(
                409,
                "dossier_not_ready",
                "Persisted lifecycle inputs are not ready for dossier generation",
                {"reasons": readiness["errors"]},
            )
        assessment = readiness["assessment"]
        review = readiness["knowledge_review"]
        snapshot = readiness["input_snapshot"]
        assert assessment is not None and review is not None and snapshot is not None
        existing = self.repository.find_dossier_by_input_hash(
            opportunity_id, readiness["input_hash"]
        )
        if existing is not None:
            result = self._annotate_dossier(existing)
            result["reused"] = True
            return result
        dossier_id = self.repository.next_dossier_id()
        document, html_report, pdf_report, _, input_hash, replay_hash = build_artifacts(
            dossier_id, snapshot
        )
        current = next(
            (
                item
                for item in self.list_dossiers(opportunity_id)
                if item.get("lifecycle_eligible")
            ),
            None,
        )
        created = self.repository.create_dossier(
            dossier_id,
            opportunity_id,
            review["review_id"],
            assessment["assessment_id"],
            snapshot,
            document,
            html_report,
            pdf_report,
            input_hash,
            replay_hash,
            DOSSIER_FORMAT_VERSION,
            actor,
            current["dossier_id"] if current else None,
        )
        result = self._annotate_dossier(created)
        result["reused"] = False
        return result

    def _annotate_dossier(self, record: dict[str, Any]) -> dict[str, Any]:
        dossier = dict(record)
        reasons: list[str] = []
        try:
            opportunity = self.repository.get_opportunity(
                dossier["opportunity_id"], include_archived=True
            )
        except ApiError:
            opportunity = None
            reasons.append("The opportunity is no longer available.")
        if opportunity is not None:
            expected_revision = dossier.get("document", {}).get(
                "opportunity_summary", {}
            ).get("revision")
            if opportunity.get("revision") != expected_revision:
                reasons.append("The opportunity revision has changed.")
        try:
            assessment = self.get_operational_assessment(
                dossier["opportunity_id"], dossier["assessment_id"]
            )
        except ApiError:
            assessment = None
            reasons.append("The source assessment is unavailable.")
        if assessment is not None and not assessment.get("lifecycle_eligible"):
            reasons.extend(assessment.get("stale_reasons", []))
        if assessment is not None:
            if assessment.get("knowledge_review_id") != dossier.get(
                "knowledge_review_id"
            ):
                reasons.append("The assessment-to-review provenance has changed.")
            try:
                review = self.get_knowledge_review(
                    dossier["opportunity_id"], dossier["knowledge_review_id"]
                )
            except ApiError:
                review = None
                reasons.append("The source Knowledge Review is unavailable.")
            if review is not None and not review.get("lifecycle_eligible"):
                reasons.extend(review.get("stale_reasons", []))
            if opportunity is not None and review is not None and not reasons:
                current_snapshot = build_input_snapshot(
                    opportunity,
                    self.repository.list_evidence(dossier["opportunity_id"]),
                    review,
                    assessment,
                )
                if dossier_sha256_json(current_snapshot) != dossier.get("input_hash"):
                    reasons.append("The persisted dossier input set has changed.")
        successor = self.repository.dossier_successor_id(dossier["dossier_id"])
        if successor:
            reasons.append(f"A newer dossier ({successor}) supersedes this artifact.")
        dossier["stale"] = bool(reasons)
        dossier["stale_reasons"] = list(dict.fromkeys(reasons))
        dossier["lifecycle_eligible"] = not reasons
        return dossier

    def list_dossiers(self, opportunity_id: str) -> list[dict[str, Any]]:
        return [
            self._annotate_dossier(item)
            for item in self.repository.list_dossiers(opportunity_id)
        ]

    def get_dossier(
        self, opportunity_id: str, dossier_id: str
    ) -> dict[str, Any]:
        dossier = self.repository.get_dossier(dossier_id)
        if dossier["opportunity_id"] != opportunity_id:
            raise ApiError(
                404,
                "dossier_not_found",
                f"Dossier {dossier_id} was not found for {opportunity_id}",
            )
        return self._annotate_dossier(dossier)

    def dossier_artifact(
        self, opportunity_id: str, dossier_id: str, artifact: str
    ) -> tuple[bytes, str, str]:
        dossier = self.repository.get_dossier(dossier_id, include_artifacts=True)
        if dossier["opportunity_id"] != opportunity_id:
            raise ApiError(
                404,
                "dossier_not_found",
                f"Dossier {dossier_id} was not found for {opportunity_id}",
            )
        if artifact == "html":
            return (
                dossier["html_report"].encode("utf-8"),
                "text/html; charset=utf-8",
                f"{dossier_id}.html",
            )
        if artifact == "pdf":
            return dossier["pdf_report"], "application/pdf", f"{dossier_id}.pdf"
        if artifact == "json":
            return (
                render_json(dossier["document"]),
                "application/json; charset=utf-8",
                f"{dossier_id}.json",
            )
        raise ApiError(404, "dossier_artifact_not_found", "Unknown dossier format")

    def replay_dossier(
        self, opportunity_id: str, dossier_id: str, actor: str
    ) -> dict[str, Any]:
        dossier = self.repository.get_dossier(
            dossier_id, include_artifacts=True, include_snapshot=True
        )
        if dossier["opportunity_id"] != opportunity_id:
            raise ApiError(
                404,
                "dossier_not_found",
                f"Dossier {dossier_id} was not found for {opportunity_id}",
            )
        document, html_report, pdf_report, json_report, input_hash, replay_hash = (
            build_artifacts(dossier_id, dossier["input_snapshot"])
        )
        artifact_matches = {
            "json": document == dossier["document"]
            and json_report == render_json(dossier["document"]),
            "html": html_report == dossier["html_report"],
            "pdf": pdf_report == dossier["pdf_report"],
        }
        replay = {
            "dossier_id": dossier_id,
            "opportunity_id": opportunity_id,
            "match": (
                input_hash == dossier["input_hash"]
                and replay_hash == dossier["replay_hash"]
                and all(artifact_matches.values())
            ),
            "stored_input_hash": dossier["input_hash"],
            "recomputed_input_hash": input_hash,
            "stored_replay_hash": dossier["replay_hash"],
            "recomputed_replay_hash": replay_hash,
            "artifact_matches": artifact_matches,
            "format_version": DOSSIER_FORMAT_VERSION,
        }
        self.repository.record_dossier_replayed(dossier, actor, replay)
        return replay

    def archive_readiness(self, opportunity_id: str) -> dict[str, Any]:
        """Validate the current persisted provenance chain without rerunning it."""

        opportunity = self.repository.get_opportunity(
            opportunity_id, include_archived=True
        )
        errors: list[str] = []
        warnings: list[str] = []
        existing = self.repository.current_archive(opportunity_id)
        if existing is not None:
            errors.append(f"A current archive ({existing['archive_id']}) already exists.")
        elif opportunity.get("archived"):
            errors.append(
                "The opportunity was archived without a BOOT-0020 archive package."
            )
        evidence = sorted(
            self.repository.list_evidence(opportunity_id),
            key=lambda item: str(item["evidence_id"]),
        )
        if not evidence:
            errors.append("At least one active evidence record is required.")
        review = next(
            (
                item
                for item in self.list_knowledge_reviews(opportunity_id)
                if item.get("lifecycle_eligible")
            ),
            None,
        )
        if review is None:
            errors.append("A current completed Knowledge Review is required.")
        assessment = next(
            (
                item
                for item in self.list_operational_assessments(opportunity_id)
                if item.get("lifecycle_eligible")
            ),
            None,
        )
        if assessment is None:
            errors.append("A current completed S.P.A.T.I.A.L. assessment is required.")
        dossier = next(
            (
                item
                for item in self.list_dossiers(opportunity_id)
                if item.get("lifecycle_eligible")
            ),
            None,
        )
        if dossier is None:
            errors.append("A current Executive Opportunity Dossier is required.")
        if assessment is not None and review is not None:
            if assessment.get("knowledge_review_id") != review.get("review_id"):
                errors.append("The assessment does not reference the current Knowledge Review.")
        if dossier is not None and assessment is not None and review is not None:
            if dossier.get("assessment_id") != assessment.get("assessment_id"):
                errors.append("The dossier does not reference the current assessment.")
            if dossier.get("knowledge_review_id") != review.get("review_id"):
                errors.append("The dossier does not reference the current Knowledge Review.")
            persisted = self.repository.get_dossier(
                dossier["dossier_id"], include_artifacts=True, include_snapshot=True
            )
            if (
                not persisted.get("html_report")
                or not persisted.get("pdf_report")
                or not persisted.get("document")
            ):
                errors.append("Required persisted dossier exports are unavailable.")
        return {
            "opportunity_id": opportunity_id,
            "ready": not errors,
            "errors": list(dict.fromkeys(errors)),
            "warnings": list(dict.fromkeys(warnings)),
            "opportunity": opportunity,
            "evidence": evidence,
            "knowledge_review": review,
            "assessment": assessment,
            "dossier": dossier,
            "existing_archive": existing,
            "archive_format_version": ARCHIVE_FORMAT_VERSION,
            "bounded_execution_notice": (
                "Archive creation uses only persisted local records and existing dossier "
                "outputs. It does not browse the internet, invoke external AI, create "
                "evidence, or rerun upstream analysis."
            ),
        }

    @staticmethod
    def _archive_provenance(
        opportunity: dict[str, Any],
        evidence: list[dict[str, Any]],
        review: dict[str, Any],
        assessment: dict[str, Any],
        dossier: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "opportunity": {
                "id": opportunity["opportunity_id"],
                "revision": opportunity["revision"],
            },
            "evidence": [
                {
                    "id": item["evidence_id"],
                    "revision": item["revision"],
                    "sha256": item.get("sha256", ""),
                }
                for item in evidence
            ],
            "knowledge_review": {
                "id": review["review_id"],
                "revision": review["revision"],
                "module_id": review["module_id"],
                "module_version": review["module_version"],
                "module_integrity_hash": review.get("module_integrity_hash", ""),
                "output_hash": review.get("output_hash", ""),
            },
            "assessment": {
                "id": assessment["assessment_id"],
                "revision": assessment["revision"],
                "engine_version": assessment.get("engine_version", ""),
                "replay_hash": assessment.get("replay_hash", ""),
            },
            "dossier": {
                "id": dossier["dossier_id"],
                "revision": dossier["revision"],
                "format_version": dossier["format_version"],
                "input_hash": dossier["input_hash"],
                "replay_hash": dossier["replay_hash"],
            },
        }

    def _opportunity_audit_summary(
        self, opportunity_id: str, artifact_ids: set[str]
    ) -> dict[str, Any]:
        events = []
        for event in reversed(self.repository.list_audit(500)):
            details = event.get("details", {})
            if (
                event.get("entity_id") in artifact_ids
                or details.get("opportunity_id") == opportunity_id
            ):
                events.append(event)
        return {"opportunity_id": opportunity_id, "events": events}

    def create_archive(
        self,
        opportunity_id: str,
        actor: str,
        reason: str = "BOOT-0020 lifecycle completion",
    ) -> dict[str, Any]:
        readiness = self.archive_readiness(opportunity_id)
        if not readiness["ready"]:
            code = (
                "archive_already_exists"
                if readiness.get("existing_archive") is not None
                else "archive_not_ready"
            )
            raise ApiError(
                409,
                code,
                "The persisted lifecycle is not ready for archival",
                {"reasons": readiness["errors"]},
            )
        opportunity = readiness["opportunity"]
        evidence = readiness["evidence"]
        review = readiness["knowledge_review"]
        assessment = readiness["assessment"]
        dossier = readiness["dossier"]
        assert review is not None and assessment is not None and dossier is not None

        dossier_replay = self.replay_dossier(
            opportunity_id, dossier["dossier_id"], actor
        )
        if not dossier_replay["match"]:
            raise ApiError(
                409,
                "dossier_replay_failed",
                "The current dossier did not pass deterministic replay",
                {"replay": dossier_replay},
            )
        archive_id = self.repository.next_archive_id()
        archive_timestamp = utcnow()
        raw_review = self.repository.get_knowledge_review(
            opportunity_id, review["review_id"]
        )
        raw_assessment = self.repository.get_assessment(
            assessment["assessment_id"], include_report=True, include_snapshot=True
        )
        raw_dossier = self.repository.get_dossier(
            dossier["dossier_id"], include_artifacts=True, include_snapshot=True
        )
        provenance = self._archive_provenance(
            opportunity, evidence, raw_review, raw_assessment, raw_dossier
        )
        replay_summary = {
            "dossier": dossier_replay,
            "assessment": {
                "assessment_id": raw_assessment["assessment_id"],
                "replay_hash": raw_assessment.get("replay_hash", ""),
                "engine_version": raw_assessment.get("engine_version", ""),
            },
            "knowledge_review": {
                "review_id": raw_review["review_id"],
                "module_id": raw_review["module_id"],
                "module_version": raw_review["module_version"],
                "module_integrity_hash": raw_review.get("module_integrity_hash", ""),
                "output_hash": raw_review.get("output_hash", ""),
            },
        }
        artifact_ids = {
            opportunity_id,
            *(item["evidence_id"] for item in evidence),
            raw_review["review_id"],
            raw_assessment["assessment_id"],
            raw_dossier["dossier_id"],
        }
        dossier_record = {
            key: value
            for key, value in raw_dossier.items()
            if key not in {"html_report", "pdf_report", "input_snapshot"}
        }
        members = {
            "opportunity.json": archive_json(opportunity),
            "evidence.json": archive_json(evidence),
            "knowledge-review.json": archive_json(raw_review),
            "assessment.json": archive_json(raw_assessment),
            "dossier.json": archive_json(dossier_record),
            "dossier.html": raw_dossier["html_report"].encode("utf-8"),
            "dossier.pdf": raw_dossier["pdf_report"],
            "audit-summary.json": archive_json(
                self._opportunity_audit_summary(opportunity_id, artifact_ids)
            ),
            "replay-summary.json": archive_json(replay_summary),
        }
        record_count = 4 + len(evidence)
        package, manifest = build_archive_package(
            archive_id=archive_id,
            opportunity_id=opportunity_id,
            archive_timestamp=archive_timestamp,
            provenance=provenance,
            record_count=record_count,
            members=members,
        )
        package_hash = archive_sha256(package)
        preflight = verify_archive_package(
            package,
            expected_package_hash=package_hash,
            expected_manifest=manifest,
            expected_provenance=provenance,
        )
        if not preflight["match"]:
            raise ApiError(
                500,
                "archive_preflight_failed",
                "The generated archive did not pass its own integrity verification",
                {"reasons": preflight["reasons"]},
            )
        replay_hash = archive_sha256(archive_json(replay_summary))
        filename = f"{archive_id}.zip"
        destination = self.archive_storage_dir / filename
        temporary = self.archive_storage_dir / f".{archive_id}.{uuid.uuid4().hex}.tmp"
        installed_package = False
        details = {
            "opportunity_id": opportunity_id,
            "dossier_id": raw_dossier["dossier_id"],
            "assessment_id": raw_assessment["assessment_id"],
            "knowledge_review_id": raw_review["review_id"],
            "evidence_trace": provenance["evidence"],
            "package_hash": package_hash,
            "replay_result": "PASS",
            "result_summary": "Archive package passed preflight verification",
        }
        self.repository.record_archive_event(
            actor=actor,
            action="archive.prepared",
            archive_id=archive_id,
            details=details,
        )
        try:
            temporary.write_bytes(package)
            try:
                os.link(temporary, destination)
            except FileExistsError as exc:
                raise ApiError(
                    409,
                    "archive_package_exists",
                    "The generated archive package name already exists in controlled storage",
                ) from exc
            temporary.unlink()
            installed_package = True
            created = self.repository.create_archive(
                {
                    "archive_id": archive_id,
                    "opportunity_id": opportunity_id,
                    "opportunity_revision": opportunity["revision"],
                    "evidence_trace": provenance["evidence"],
                    "knowledge_review_id": raw_review["review_id"],
                    "knowledge_review_revision": raw_review["revision"],
                    "assessment_id": raw_assessment["assessment_id"],
                    "assessment_revision": raw_assessment["revision"],
                    "dossier_id": raw_dossier["dossier_id"],
                    "dossier_format_version": raw_dossier["format_version"],
                    "archive_status": "Archived",
                    "archive_reason": str(reason).strip() or "Lifecycle completion",
                    "archived_by": actor,
                    "archive_timestamp": archive_timestamp,
                    "package_manifest": manifest,
                    "package_hash": package_hash,
                    "replay_hash": replay_hash,
                    "record_count": record_count,
                    "file_count": manifest["file_count"],
                    "storage_location": f"archives/{filename}",
                    "provenance": provenance,
                },
                actor,
            )
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            if installed_package:
                destination.unlink(missing_ok=True)
            self.repository.record_archive_event(
                actor=actor,
                action="archive.failed",
                archive_id=archive_id,
                details={**details, "replay_result": "FAIL", "result_summary": str(exc)},
            )
            raise
        return created

    def list_archives(self, opportunity_id: str) -> list[dict[str, Any]]:
        return self.repository.list_archives(opportunity_id)

    def get_archive(self, opportunity_id: str, archive_id: str) -> dict[str, Any]:
        archive = self.repository.get_archive(archive_id)
        if archive["opportunity_id"] != opportunity_id:
            raise ApiError(
                404,
                "archive_not_found",
                f"Archive {archive_id} was not found for {opportunity_id}",
            )
        return archive

    def _archive_path(self, archive: dict[str, Any]) -> Path:
        expected_name = f"{archive['archive_id']}.zip"
        stored_name = Path(str(archive.get("storage_location", ""))).name
        if stored_name != expected_name:
            raise ApiError(
                409,
                "unsafe_archive_location",
                "The persisted archive storage location is invalid",
            )
        path = (self.archive_storage_dir / stored_name).resolve()
        if path.parent != self.archive_storage_dir.resolve():
            raise ApiError(409, "unsafe_archive_location", "Archive path escaped storage")
        return path

    def archive_artifact(
        self, opportunity_id: str, archive_id: str, actor: str
    ) -> tuple[bytes, str, str]:
        archive = self.get_archive(opportunity_id, archive_id)
        path = self._archive_path(archive)
        if not path.is_file():
            raise ApiError(404, "archive_package_not_found", "Archive package is unavailable")
        payload = path.read_bytes()
        self.repository.record_archive_event(
            actor=actor,
            action="archive.downloaded",
            archive_id=archive_id,
            details={
                "opportunity_id": opportunity_id,
                "dossier_id": archive["dossier_id"],
                "assessment_id": archive["assessment_id"],
                "knowledge_review_id": archive["knowledge_review_id"],
                "evidence_trace": archive["evidence_trace"],
                "package_hash": archive["package_hash"],
                "replay_result": "NOT_RUN",
                "result_summary": "Archive package downloaded",
            },
        )
        return payload, "application/zip", f"{archive_id}.zip"

    def replay_archive(
        self, opportunity_id: str, archive_id: str, actor: str
    ) -> dict[str, Any]:
        archive = self.get_archive(opportunity_id, archive_id)
        path = self._archive_path(archive)
        if not path.is_file():
            result = {
                "result": "FAIL",
                "match": False,
                "checks": {},
                "reasons": ["The persisted archive package is unavailable."],
                "stored_package_hash": archive["package_hash"],
                "computed_package_hash": "",
            }
        else:
            result = verify_archive_package(
                path.read_bytes(),
                expected_package_hash=archive["package_hash"],
                expected_manifest=archive["package_manifest"],
                expected_provenance=archive["provenance"],
            )
        result.update(
            {
                "archive_id": archive_id,
                "opportunity_id": opportunity_id,
                "verified_at": utcnow(),
            }
        )
        action = "archive.replayed" if result["match"] else "archive.replay_failed"
        self.repository.record_archive_event(
            actor=actor,
            action=action,
            archive_id=archive_id,
            details={
                "opportunity_id": opportunity_id,
                "dossier_id": archive["dossier_id"],
                "assessment_id": archive["assessment_id"],
                "knowledge_review_id": archive["knowledge_review_id"],
                "evidence_trace": archive["evidence_trace"],
                "package_hash": archive["package_hash"],
                "replay_result": result["result"],
                "result_summary": "; ".join(result["reasons"]) or "All checks passed",
            },
        )
        return result

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
