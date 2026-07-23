"""Versioned Knowledge Modules and deterministic local review execution."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .errors import ApiError


MODULE_ID_PATTERN = re.compile(r"AKM-[A-Z0-9]+-[A-Z0-9]+-[0-9]{3}")
REQUIRED_MODULE_FIELDS = {
    "module_id",
    "name",
    "version",
    "purpose",
    "scope",
    "domain",
    "jurisdiction",
    "publisher",
    "description",
    "applicability_criteria",
    "required_evidence_categories",
    "review_questions",
    "assumptions",
    "known_limitations",
    "output_schema",
    "effective_date",
    "review_date",
    "status",
    "integrity_hash",
}


def canonical_json(value: Any) -> str:
    """Return the stable JSON form used for hashes and replay comparisons."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def module_integrity_hash(module: dict[str, Any]) -> str:
    payload = deepcopy(module)
    payload.pop("integrity_hash", None)
    return sha256_json(payload)


def validate_module(module: Any, source: str = "module definition") -> dict[str, Any]:
    if not isinstance(module, dict):
        raise ApiError(500, "invalid_knowledge_module", f"{source} must be a JSON object")
    missing = sorted(REQUIRED_MODULE_FIELDS - set(module))
    if missing:
        raise ApiError(
            500,
            "invalid_knowledge_module",
            f"{source} is missing required fields",
            {"fields": missing},
        )
    module_id = str(module["module_id"])
    if not MODULE_ID_PATTERN.fullmatch(module_id):
        raise ApiError(
            500,
            "invalid_knowledge_module",
            f"{source} has an invalid module_id",
        )
    if not str(module["version"]).strip():
        raise ApiError(500, "invalid_knowledge_module", f"{source} requires a version")
    if module["status"] not in {"Active", "Inactive", "Retired"}:
        raise ApiError(500, "invalid_knowledge_module", f"{source} has an invalid status")
    for field_name in (
        "applicability_criteria",
        "required_evidence_categories",
        "review_questions",
        "assumptions",
        "known_limitations",
    ):
        if not isinstance(module[field_name], list):
            raise ApiError(
                500,
                "invalid_knowledge_module",
                f"{source} field {field_name} must be an array",
            )
    questions = module["review_questions"]
    if not questions or any(
        not isinstance(item, dict)
        or not str(item.get("question_id", "")).strip()
        or not str(item.get("question", "")).strip()
        for item in questions
    ):
        raise ApiError(
            500,
            "invalid_knowledge_module",
            f"{source} requires identified review questions",
        )
    for field_name in ("effective_date", "review_date"):
        try:
            date.fromisoformat(str(module[field_name]))
        except ValueError as exc:
            raise ApiError(
                500,
                "invalid_knowledge_module",
                f"{source} field {field_name} must use YYYY-MM-DD",
            ) from exc
    expected_hash = module_integrity_hash(module)
    if module["integrity_hash"] != expected_hash:
        raise ApiError(
            500,
            "knowledge_module_integrity_mismatch",
            f"{source} integrity hash does not match its canonical definition",
            {"expected": expected_hash, "actual": module["integrity_hash"]},
        )
    return deepcopy(module)


class KnowledgeModuleRegistry:
    """Load immutable module definitions from version-controlled JSON files."""

    def __init__(self, module_dir: str | Path | None = None):
        self.module_dir = Path(module_dir) if module_dir else Path(__file__).parent / "knowledge_modules"
        self._modules: dict[str, dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        modules: dict[str, dict[str, Any]] = {}
        if not self.module_dir.is_dir():
            raise ApiError(
                500,
                "knowledge_module_directory_missing",
                f"Knowledge Module directory was not found: {self.module_dir}",
            )
        for path in sorted(self.module_dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ApiError(
                    500,
                    "invalid_knowledge_module",
                    f"Knowledge Module file could not be read: {path.name}",
                ) from exc
            module = validate_module(raw, path.name)
            module_id = module["module_id"]
            if module_id in modules:
                raise ApiError(
                    500,
                    "duplicate_knowledge_module",
                    f"Knowledge Module {module_id} is defined more than once",
                )
            modules[module_id] = module
        if not modules:
            raise ApiError(500, "knowledge_modules_empty", "No Knowledge Modules were loaded")
        self._modules = modules

    def list(self, active_only: bool = True) -> list[dict[str, Any]]:
        result = []
        for module in self._modules.values():
            if active_only and module["status"] != "Active":
                continue
            item = deepcopy(module)
            item["review_question_count"] = len(item["review_questions"])
            result.append(item)
        return sorted(result, key=lambda item: item["module_id"])

    def get(self, module_id: str) -> dict[str, Any]:
        try:
            return deepcopy(self._modules[module_id])
        except KeyError as exc:
            raise ApiError(
                404,
                "knowledge_module_not_found",
                f"Knowledge Module {module_id} was not found",
            ) from exc


def _contains_any(records: list[dict[str, Any]], terms: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for record in records:
        text = " ".join(
            str(record.get(field, ""))
            for field in ("title", "description", "notes", "source")
        ).lower()
        if any(term in text for term in terms):
            matches.append(record["evidence_id"])
    return sorted(matches)


def _finding(
    questions: dict[str, str],
    question_id: str,
    disposition: str,
    rationale: str,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "question": questions[question_id],
        "disposition": disposition,
        "rationale": rationale,
        "evidence_ids": sorted(evidence_ids or []),
    }


def execute_florida_geographic_review(
    module: dict[str, Any],
    opportunity: dict[str, Any],
    active_evidence: list[dict[str, Any]],
    excluded_archived_evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Execute AKM-GEO-FL-001 without network, AI, or mutable external inputs."""

    questions = {
        item["question_id"]: item["question"] for item in module["review_questions"]
    }
    evidence = sorted(active_evidence, key=lambda item: item["evidence_id"])
    evidence_ids = [item["evidence_id"] for item in evidence]
    findings: list[dict[str, Any]] = []
    assumptions: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    missing_evidence: list[dict[str, Any]] = []

    geography_is_florida = str(opportunity.get("geography", "")).strip().lower() == "florida"
    florida_evidence = _contains_any(evidence, ("florida",))
    if geography_is_florida and florida_evidence:
        findings.append(_finding(questions, "FL-Q01", "Partially Supported", "The opportunity identifies Florida and active reference evidence contains Florida context; the record does not independently establish location.", florida_evidence))
    elif geography_is_florida:
        findings.append(_finding(questions, "FL-Q01", "Partially Supported", "The opportunity identifies Florida, but no active evidence independently supports the geographic field."))
        missing_evidence.append({"category": "Geographic evidence", "reason": "Independent location evidence is absent."})
    else:
        findings.append(_finding(questions, "FL-Q01", "Unsupported", "The opportunity geography does not identify Florida."))

    infrastructure_class = str(opportunity.get("infrastructure_class", "")).strip()
    findings.append(_finding(questions, "FL-Q02", "Partially Supported" if infrastructure_class else "Unknown", "The infrastructure class is identified in the opportunity record but is not treated as independently verified." if infrastructure_class else "The infrastructure class is not identified."))
    if not infrastructure_class:
        missing_evidence.append({"category": "Infrastructure classification", "reason": "Infrastructure class is missing."})

    organization = str(opportunity.get("organization", "")).strip()
    findings.append(_finding(questions, "FL-Q03", "Partially Supported" if organization else "Unknown", "The organization is named in the opportunity record but the module does not treat that field as proof of relationship or intent." if organization else "The organization is not identified."))
    if organization:
        assumptions.append({"assumption_id": "FL-A01", "statement": f"The opportunity is being evaluated in relation to {organization}.", "basis": "Opportunity metadata only", "evidence_ids": []})

    findings.append(_finding(questions, "FL-Q04", "Partially Supported" if florida_evidence else "Unsupported", "Active evidence contains Florida context but does not independently verify project location." if florida_evidence else "No active evidence contains supporting Florida geographic context.", florida_evidence))

    service_territory_evidence = sorted(
        item["evidence_id"]
        for item in evidence
        if item.get("evidence_type") == "Regulatory Record"
        and _contains_any([item], ("service territory", "territory", "fpsc"))
    )
    if service_territory_evidence:
        findings.append(_finding(questions, "FL-Q05", "Partially Supported", "A regulatory record references service-territory context; legal or operational applicability is not independently verified.", service_territory_evidence))
    else:
        findings.append(_finding(questions, "FL-Q05", "Unknown", "No active regulatory evidence establishes the relevant utility or service territory."))
        unknowns.append({"unknown_id": "FL-U01", "statement": "Applicable utility or service territory is not established by active evidence.", "evidence_ids": []})
        missing_evidence.append({"category": "Service-territory evidence", "reason": "A dated authoritative territory record is absent."})

    environmental_evidence = _contains_any(evidence, ("hurricane", "flood", "storm", "wildfire", "environmental exposure"))
    findings.append(_finding(questions, "FL-Q06", "Partially Supported" if environmental_evidence else "Unknown", "Active evidence identifies at least one environmental exposure factor, without engineering validation." if environmental_evidence else "Environmental exposure factors are not identified in active evidence.", environmental_evidence))
    if not environmental_evidence:
        unknowns.append({"unknown_id": "FL-U02", "statement": "Material environmental exposure factors have not been documented.", "evidence_ids": []})
        missing_evidence.append({"category": "Environmental context", "reason": "No dated exposure or hazard evidence is present."})

    regulatory_evidence = _contains_any(evidence, ("permit", "regulatory", "approval", "fpsc"))
    findings.append(_finding(questions, "FL-Q07", "Partially Supported" if regulatory_evidence else "Unknown", "Active evidence identifies permitting or regulatory context but does not establish approval." if regulatory_evidence else "Permitting and regulatory dependencies are not identified in active evidence.", regulatory_evidence))
    if not regulatory_evidence:
        unknowns.append({"unknown_id": "FL-U03", "statement": "Permitting and regulatory dependencies remain unknown.", "evidence_ids": []})
        missing_evidence.append({"category": "Regulatory dependencies", "reason": "No dated dependency or approval evidence is present."})

    ownership_evidence = _contains_any(evidence, ("ownership", "owner", "title"))
    findings.append(_finding(questions, "FL-Q08", "Partially Supported" if ownership_evidence else "Unknown", "Active evidence documents an ownership-related statement, but the module does not independently validate title or control." if ownership_evidence else "Infrastructure ownership assumptions are not documented in active evidence.", ownership_evidence))
    if not ownership_evidence:
        assumptions.append({"assumption_id": "FL-A02", "statement": "Infrastructure ownership and control remain unestablished.", "basis": "No active ownership evidence", "evidence_ids": []})
        missing_evidence.append({"category": "Ownership evidence", "reason": "Ownership or control documentation is absent."})

    findings.append(_finding(questions, "FL-Q09", "Supported" if unknowns else "Partially Supported", f"The review records {len(unknowns)} material unknown(s) produced by bounded rules."))

    dated_ids = sorted(item["evidence_id"] for item in evidence if item.get("source_date"))
    confident_ids = sorted(item["evidence_id"] for item in evidence if item.get("evidence_confidence") not in {"", "Unknown"})
    if evidence and len(dated_ids) == len(evidence) and len(confident_ids) == len(evidence):
        date_disposition = "Supported"
        date_rationale = "Every consumed evidence record has a source date and a non-Unknown confidence classification."
    elif dated_ids or confident_ids:
        date_disposition = "Partially Supported"
        date_rationale = "Some consumed evidence has source dates or confidence classifications, but the trace is incomplete."
    else:
        date_disposition = "Unsupported"
        date_rationale = "Consumed evidence lacks source dates and usable confidence classifications."
    findings.append(_finding(questions, "FL-Q10", date_disposition, date_rationale, sorted(set(dated_ids + confident_ids))))

    effective_date = date.fromisoformat(module["effective_date"])
    stale_cutoff = effective_date - timedelta(days=int(module.get("evidence_stale_after_days", 365)))
    stale_ids: list[str] = []
    questioned_ids: list[str] = []
    unsupported_ids: list[str] = []
    for item in evidence:
        source_date = str(item.get("source_date", ""))
        if source_date:
            try:
                if date.fromisoformat(source_date) < stale_cutoff:
                    stale_ids.append(item["evidence_id"])
            except ValueError:
                stale_ids.append(item["evidence_id"])
        if item.get("evidence_status") in {"Questioned", "Superseded"}:
            questioned_ids.append(item["evidence_id"])
        if item.get("state") in {"U", "D"}:
            unsupported_ids.append(item["evidence_id"])
    flagged_ids = sorted(set(stale_ids + questioned_ids + unsupported_ids))
    excluded_archived = sorted(excluded_archived_evidence_ids or [])
    caution_ids = sorted(set(flagged_ids + excluded_archived))
    findings.append(_finding(questions, "FL-Q11", "Partially Supported" if caution_ids else "Supported", "The trace identifies active or excluded archived evidence requiring caution." if caution_ids else "No consumed active evidence is stale by the module rule, Questioned, Superseded, Unknown, or Disputed, and no archived evidence was identified.", caution_ids))
    if flagged_ids:
        risks.append({"risk_id": "FL-R01", "statement": "One or more consumed evidence records require caution because of age, status, or classification.", "evidence_ids": flagged_ids})

    if excluded_archived:
        risks.append({"risk_id": "FL-R02", "statement": "Archived evidence exists but was intentionally excluded from active review inputs.", "evidence_ids": excluded_archived})

    confidence_values = {item.get("evidence_confidence", "Unknown") for item in evidence}
    if not evidence:
        confidence = "Unknown"
    elif confidence_values & {"Moderate", "High", "Verified"}:
        confidence = "High" if not missing_evidence and confidence_values <= {"High", "Verified"} else "Moderate"
    else:
        confidence = "Low"

    return {
        "module_id": module["module_id"],
        "module_version": module["version"],
        "review_basis": "Local deterministic rules over persisted opportunity and active evidence records",
        "confidence": confidence,
        "findings": findings,
        "assumptions": assumptions,
        "unknowns": unknowns,
        "risks": risks,
        "missing_evidence": missing_evidence,
        "consumed_evidence_ids": evidence_ids,
        "excluded_archived_evidence_ids": excluded_archived,
        "reference_evidence_notice": (
            "EV-000001 is Sirius Logic Systems reference analysis. It is not an "
            "official Florida Power & Light record and does not establish endorsement, "
            "procurement intent, ownership, service territory, funding availability, or "
            "regulatory approval. Additional independent evidence is required before "
            "high-confidence conclusions can be made."
            if "EV-000001" in evidence_ids
            else ""
        ),
        "limitations": deepcopy(module["known_limitations"]),
        "disclaimer": "This review is not legal, regulatory, engineering, environmental, or investment advice and does not independently verify evidence.",
    }


def execute_module(
    module: dict[str, Any],
    opportunity: dict[str, Any],
    active_evidence: list[dict[str, Any]],
    excluded_archived_evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    if module["module_id"] == "AKM-GEO-FL-001":
        return execute_florida_geographic_review(
            module, opportunity, active_evidence, excluded_archived_evidence_ids
        )
    raise ApiError(
        422,
        "knowledge_module_executor_unavailable",
        f"No deterministic executor is installed for {module['module_id']}",
    )
