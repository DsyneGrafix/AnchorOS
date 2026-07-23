"""Deterministic Executive Opportunity Dossier rendering.

This module is intentionally a pure reporting boundary.  It accepts a persisted
snapshot and never queries the network, invokes an AI model, or reruns either a
Knowledge Module or the S.P.A.T.I.A.L. engine.
"""

from __future__ import annotations

import hashlib
import json
import textwrap
from html import escape
from typing import Any


DOSSIER_FORMAT_VERSION = "1.0.0"
DOSSIER_CONTRACT_VERSION = "anchorintel-executive-dossier/1.0"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def build_input_snapshot(
    opportunity: dict[str, Any],
    evidence: list[dict[str, Any]],
    review: dict[str, Any],
    assessment: dict[str, Any],
) -> dict[str, Any]:
    """Select the persisted fields needed to reproduce a dossier."""

    evidence_snapshot = [
        {
            "evidence_id": item["evidence_id"],
            "title": item.get("title", ""),
            "evidence_type": item.get("evidence_type", ""),
            "source": item.get("source", ""),
            "evidence_status": item.get("evidence_status", ""),
            "evidence_confidence": item.get("evidence_confidence", ""),
            "revision": item.get("revision"),
            "sha256": item.get("sha256", ""),
            "updated_at": item.get("updated_at", ""),
        }
        for item in sorted(evidence, key=lambda value: str(value["evidence_id"]))
    ]
    review_output = review.get("output", {})
    assessment_result = assessment.get("result", {})
    return {
        "contract_version": DOSSIER_CONTRACT_VERSION,
        "opportunity": {
            "opportunity_id": opportunity["opportunity_id"],
            "title": opportunity.get("title", ""),
            "organization": opportunity.get("organization", ""),
            "sector": opportunity.get("sector", ""),
            "geography": opportunity.get("geography", ""),
            "infrastructure_class": opportunity.get("infrastructure_class", ""),
            "status": opportunity.get("status", ""),
            "description": opportunity.get("description", ""),
            "revision": opportunity.get("revision"),
            "created_at": opportunity.get("created_at", ""),
            "updated_at": opportunity.get("updated_at", ""),
        },
        "active_evidence": evidence_snapshot,
        "knowledge_review": {
            "review_id": review["review_id"],
            "revision": review.get("revision"),
            "review_status": review.get("review_status", ""),
            "confidence": review.get("confidence", ""),
            "module_id": review.get("module_id", ""),
            "module_version": review.get("module_version", ""),
            "module_integrity_hash": review.get("module_integrity_hash", ""),
            "output_hash": review.get("output_hash", ""),
            "created_at": review.get("created_at", ""),
            "updated_at": review.get("updated_at", ""),
            "output": {
                "findings": review_output.get("findings", []),
                "assumptions": review_output.get("assumptions", []),
                "unknowns": review_output.get("unknowns", []),
                "risks": review_output.get("risks", []),
                "missing_evidence": review_output.get("missing_evidence", []),
                "limitations": review_output.get("limitations", []),
                "disclaimer": review_output.get("disclaimer", ""),
            },
        },
        "assessment": {
            "assessment_id": assessment["assessment_id"],
            "revision": assessment.get("revision"),
            "knowledge_review_id": assessment.get("knowledge_review_id", ""),
            "engine_version": assessment.get("engine_version", ""),
            "adapter_version": assessment.get("adapter_version", ""),
            "assessment_replay_hash": assessment.get("replay_hash", ""),
            "engine_input_hash": assessment.get("provenance", {}).get(
                "engine_input_hash", ""
            ),
            "execution_timestamp": assessment.get("execution_timestamp", ""),
            "updated_at": assessment.get("updated_at", ""),
            "result": {
                "recommendation": assessment_result.get("recommendation", ""),
                "recommendation_reason": assessment_result.get(
                    "recommendation_reason", ""
                ),
                "score": assessment_result.get("score"),
                "confidence": assessment_result.get("confidence", ""),
                "risk_profile": assessment_result.get("risk_profile", {}),
                "gates": assessment_result.get("gates", {}),
                "explanation": assessment_result.get("explanation", {}),
                "warnings": assessment_result.get("warnings", []),
                "known_limitations": assessment_result.get(
                    "known_limitations", []
                ),
                "lifecycle": assessment_result.get("lifecycle", {}),
                "evidence_trace": assessment_result.get("evidence_trace", []),
            },
        },
    }


def _state_timestamp(snapshot: dict[str, Any]) -> str:
    values = [
        snapshot["opportunity"].get("updated_at", ""),
        snapshot["knowledge_review"].get("updated_at", ""),
        snapshot["assessment"].get("updated_at", ""),
        snapshot["assessment"].get("execution_timestamp", ""),
    ]
    values.extend(item.get("updated_at", "") for item in snapshot["active_evidence"])
    return max((str(value) for value in values if value), default="")


def _finding_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("question_id", ""),
        "disposition": item.get("disposition", ""),
        "finding": item.get("rationale", item.get("question", "")),
        "evidence_ids": item.get("evidence_ids", []),
    }


def _statement_summary(item: dict[str, Any], id_fields: tuple[str, ...]) -> dict[str, Any]:
    identifier = next((item.get(field) for field in id_fields if item.get(field)), "")
    return {
        "id": identifier,
        "statement": item.get("statement", item.get("reason", str(item))),
        "evidence_ids": item.get("evidence_ids", []),
    }


def build_document(dossier_id: str, snapshot: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    """Build the canonical dossier document and its two integrity hashes."""

    input_hash = sha256_json(snapshot)
    opportunity = snapshot["opportunity"]
    evidence = snapshot["active_evidence"]
    review = snapshot["knowledge_review"]
    review_output = review["output"]
    assessment = snapshot["assessment"]
    result = assessment["result"]
    recommendation = result.get("recommendation", "")
    score = result.get("score")
    confidence = result.get("confidence", "")
    trace = [opportunity["opportunity_id"]]
    trace.extend(item["evidence_id"] for item in evidence)
    trace.extend([review["review_id"], assessment["assessment_id"], dossier_id])
    document = {
        "contract_version": DOSSIER_CONTRACT_VERSION,
        "dossier_id": dossier_id,
        "format_version": DOSSIER_FORMAT_VERSION,
        "report_state_timestamp": _state_timestamp(snapshot),
        "executive_summary": {
            "opportunity": opportunity.get("title", ""),
            "customer": opportunity.get("organization", ""),
            "sector": opportunity.get("sector", ""),
            "geography": opportunity.get("geography", ""),
            "current_status": opportunity.get("status", ""),
            "assessment_recommendation": recommendation,
            "overall_score": score,
            "confidence": confidence,
            "summary": (
                f"The persisted S.P.A.T.I.A.L. assessment recommends {recommendation} "
                f"with an overall score of {score}/100 and {confidence} confidence. "
                "This dossier summarizes the recorded opportunity, active evidence, "
                "Knowledge Review, and assessment without re-executing upstream analysis."
            ),
        },
        "opportunity_summary": {
            "opportunity_id": opportunity["opportunity_id"],
            "organization": opportunity.get("organization", ""),
            "infrastructure_class": opportunity.get("infrastructure_class", ""),
            "revision": opportunity.get("revision"),
            "created_at": opportunity.get("created_at", ""),
            "updated_at": opportunity.get("updated_at", ""),
            "description": opportunity.get("description", ""),
        },
        "evidence_summary": {
            "count": len(evidence),
            "records": [
                {
                    "evidence_id": item["evidence_id"],
                    "title": item.get("title", ""),
                    "status": item.get("evidence_status", ""),
                    "confidence": item.get("evidence_confidence", ""),
                    "revision": item.get("revision"),
                }
                for item in evidence
            ],
        },
        "knowledge_review_summary": {
            "review_id": review["review_id"],
            "module_id": review.get("module_id", ""),
            "module_version": review.get("module_version", ""),
            "confidence": review.get("confidence", ""),
            "findings": [
                _finding_summary(item) for item in review_output.get("findings", [])
            ],
            "assumptions": [
                _statement_summary(item, ("assumption_id", "id"))
                for item in review_output.get("assumptions", [])
            ],
            "unknowns": [
                _statement_summary(item, ("unknown_id", "id"))
                for item in review_output.get("unknowns", [])
            ],
            "risks": [
                _statement_summary(item, ("risk_id", "id"))
                for item in review_output.get("risks", [])
            ],
            "missing_evidence": [
                {
                    "category": item.get("category", ""),
                    "reason": item.get("reason", ""),
                }
                for item in review_output.get("missing_evidence", [])
            ],
        },
        "spatial_assessment_summary": {
            "assessment_id": assessment["assessment_id"],
            "engine_version": assessment.get("engine_version", ""),
            "recommendation": recommendation,
            "score": score,
            "confidence": confidence,
            "risk_profile": result.get("risk_profile", {}),
            "gate_results": result.get("gates", {}),
            "explanation": result.get("explanation", {}),
            "recommendation_reason": result.get("recommendation_reason", ""),
            "warnings": result.get("warnings", []),
        },
        "traceability": {
            "chain": trace,
            "display": " -> ".join(trace),
        },
        "replay_information": {
            "input_hash": input_hash,
            "assessment_replay_hash": assessment.get(
                "assessment_replay_hash", ""
            ),
            "engine_input_hash": assessment.get("engine_input_hash", ""),
            "engine_version": assessment.get("engine_version", ""),
            "module_version": review.get("module_version", ""),
        },
        "footer": [
            "This dossier summarizes persisted records contained within AnchorIntel.",
            "It does not independently verify evidence.",
            "It does not browse the internet.",
            "It does not invoke an external AI model.",
            "It reflects the system state at the recorded execution time.",
        ],
    }
    replay_hash = sha256_json({"input_hash": input_hash, "document": document})
    document["replay_information"]["replay_hash"] = replay_hash
    return document, input_hash, replay_hash


def _html_list(items: list[str], empty: str = "None recorded") -> str:
    if not items:
        return f'<p class="muted">{escape(empty)}</p>'
    return "<ul>" + "".join(f"<li>{escape(str(item))}</li>" for item in items) + "</ul>"


def render_html(document: dict[str, Any]) -> str:
    """Render a standalone, print-friendly HTML dossier."""

    executive = document["executive_summary"]
    opportunity = document["opportunity_summary"]
    evidence = document["evidence_summary"]
    review = document["knowledge_review_summary"]
    assessment = document["spatial_assessment_summary"]
    replay = document["replay_information"]
    evidence_rows = "".join(
        "<tr>"
        f"<td>{escape(str(item['evidence_id']))}</td>"
        f"<td>{escape(str(item['title']))}</td>"
        f"<td>{escape(str(item['status']))}</td>"
        f"<td>{escape(str(item['confidence']))}</td>"
        f"<td>{escape(str(item['revision']))}</td>"
        "</tr>"
        for item in evidence["records"]
    ) or '<tr><td colspan="5">No active evidence records.</td></tr>'
    finding_rows = "".join(
        "<tr>"
        f"<td>{escape(str(item['id']))}</td>"
        f"<td>{escape(str(item['disposition']))}</td>"
        f"<td>{escape(str(item['finding']))}</td>"
        f"<td>{escape(', '.join(item['evidence_ids']))}</td>"
        "</tr>"
        for item in review["findings"]
    ) or '<tr><td colspan="4">No findings recorded.</td></tr>'
    gate_rows = "".join(
        "<tr>"
        f"<td>{escape(str(key))}</td>"
        f"<td>{escape(str(value.get('status', '')))}</td>"
        f"<td>{escape(str(value.get('rationale', '')))}</td>"
        "</tr>"
        for key, value in assessment["gate_results"].items()
    )
    assumptions = [item["statement"] for item in review["assumptions"]]
    unknowns = [item["statement"] for item in review["unknowns"]]
    missing = [
        f"{item['category']}: {item['reason']}" for item in review["missing_evidence"]
    ]
    footer = " ".join(document["footer"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(document['dossier_id'])} · Executive Opportunity Dossier</title>
<style>
:root{{--ink:#10211c;--muted:#60716b;--anchor:#075d4f;--signal:#d9a441;--line:#dce5e1;--wash:#f2f7f5}}
*{{box-sizing:border-box}}body{{margin:0;color:var(--ink);font:14px/1.55 Arial,sans-serif;background:#edf5f2}}
main{{max-width:960px;margin:36px auto;background:white;padding:48px;box-shadow:0 16px 50px #10211c18}}
.eyebrow{{color:var(--anchor);font-size:12px;font-weight:bold;letter-spacing:.12em;text-transform:uppercase}}
h1{{font-size:38px;line-height:1.05;margin:8px 0}}h2{{margin:30px 0 12px;border-bottom:2px solid var(--signal);padding-bottom:6px}}
.decision{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:24px 0}}.decision div,.panel{{background:var(--wash);padding:16px}}
dt{{color:var(--muted);font-size:11px;text-transform:uppercase}}dd{{margin:2px 0 12px;font-weight:bold}}
table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;vertical-align:top;padding:9px;border-bottom:1px solid var(--line)}}th{{font-size:11px;text-transform:uppercase;color:var(--muted)}}
.hash{{font-family:monospace;overflow-wrap:anywhere}}.muted{{color:var(--muted)}}footer{{margin-top:40px;border-top:2px solid var(--signal);padding-top:18px;color:var(--muted);font-size:12px}}
@media(max-width:700px){{main{{margin:0;padding:24px}}.decision{{grid-template-columns:1fr}}}}@media print{{body{{background:white}}main{{margin:0;max-width:none;box-shadow:none}}}}
</style></head><body><main>
<div class="eyebrow">{escape(document['dossier_id'])} · Executive Opportunity Dossier</div>
<h1>{escape(executive['opportunity'])}</h1><p>{escape(executive['customer'])} · {escape(executive['sector'])} · {escape(executive['geography'])}</p>
<div class="decision"><div><dt>Recommendation</dt><dd>{escape(str(executive['assessment_recommendation']))}</dd></div><div><dt>Overall score</dt><dd>{escape(str(executive['overall_score']))}/100</dd></div><div><dt>Confidence</dt><dd>{escape(str(executive['confidence']))}</dd></div></div>
<h2>Executive Summary</h2><p>{escape(executive['summary'])}</p>
<h2>Opportunity Summary</h2><dl class="panel"><dt>Opportunity ID</dt><dd>{escape(str(opportunity['opportunity_id']))}</dd><dt>Organization</dt><dd>{escape(str(opportunity['organization']))}</dd><dt>Infrastructure class</dt><dd>{escape(str(opportunity['infrastructure_class']))}</dd><dt>Revision</dt><dd>{escape(str(opportunity['revision']))}</dd><dt>Created / updated</dt><dd>{escape(str(opportunity['created_at']))} / {escape(str(opportunity['updated_at']))}</dd></dl><p>{escape(str(opportunity['description']))}</p>
<h2>Evidence Summary</h2><p>{evidence['count']} active evidence record(s).</p><table><thead><tr><th>ID</th><th>Title</th><th>Status</th><th>Confidence</th><th>Revision</th></tr></thead><tbody>{evidence_rows}</tbody></table>
<h2>Knowledge Review Summary</h2><p>{escape(review['review_id'])} · {escape(review['module_id'])} v{escape(str(review['module_version']))}</p><table><thead><tr><th>ID</th><th>Disposition</th><th>Finding</th><th>Evidence</th></tr></thead><tbody>{finding_rows}</tbody></table>
<h3>Assumptions</h3>{_html_list(assumptions)}<h3>Unknowns</h3>{_html_list(unknowns)}<h3>Missing Evidence</h3>{_html_list(missing)}
<h2>S.P.A.T.I.A.L. Assessment Summary</h2><dl class="panel"><dt>Assessment ID</dt><dd>{escape(assessment['assessment_id'])}</dd><dt>Engine version</dt><dd>{escape(str(assessment['engine_version']))}</dd><dt>Recommendation</dt><dd>{escape(str(assessment['recommendation']))}</dd><dt>Score / confidence</dt><dd>{escape(str(assessment['score']))}/100 · {escape(str(assessment['confidence']))}</dd><dt>Risk profile</dt><dd>{escape(str(assessment['risk_profile'].get('level','')))}</dd><dt>Explanation</dt><dd>{escape(str(assessment['explanation'].get('engine','')))}</dd></dl><table><thead><tr><th>Gate</th><th>Status</th><th>Rationale</th></tr></thead><tbody>{gate_rows}</tbody></table>
<h2>Traceability</h2><p class="hash">{escape(document['traceability']['display'])}</p>
<h2>Replay Information</h2><dl class="panel hash"><dt>Replay hash</dt><dd>{escape(replay['replay_hash'])}</dd><dt>Input hash</dt><dd>{escape(replay['input_hash'])}</dd><dt>Assessment replay hash</dt><dd>{escape(replay['assessment_replay_hash'])}</dd><dt>Engine input hash</dt><dd>{escape(replay['engine_input_hash'])}</dd><dt>Engine / module versions</dt><dd>{escape(str(replay['engine_version']))} / {escape(str(replay['module_version']))}</dd></dl>
<footer>{escape(footer)} State timestamp: {escape(document['report_state_timestamp'])}.</footer>
</main></body></html>"""


def render_json(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def _pdf_lines(document: dict[str, Any]) -> list[str]:
    executive = document["executive_summary"]
    opportunity = document["opportunity_summary"]
    evidence = document["evidence_summary"]
    review = document["knowledge_review_summary"]
    assessment = document["spatial_assessment_summary"]
    replay = document["replay_information"]
    lines = [
        "ANCHORINTEL EXECUTIVE OPPORTUNITY DOSSIER",
        document["dossier_id"],
        "",
        executive["opportunity"],
        f"Customer: {executive['customer']}",
        f"Sector: {executive['sector']} | Geography: {executive['geography']}",
        f"Recommendation: {executive['assessment_recommendation']} | Score: {executive['overall_score']}/100 | Confidence: {executive['confidence']}",
        "",
        "EXECUTIVE SUMMARY",
        executive["summary"],
        "",
        "OPPORTUNITY SUMMARY",
        f"ID: {opportunity['opportunity_id']} | Organization: {opportunity['organization']}",
        f"Infrastructure class: {opportunity['infrastructure_class']} | Revision: {opportunity['revision']}",
        f"Created: {opportunity['created_at']} | Updated: {opportunity['updated_at']}",
        opportunity["description"],
        "",
        f"EVIDENCE SUMMARY ({evidence['count']} ACTIVE)",
    ]
    lines.extend(
        f"{item['evidence_id']} | {item['title']} | {item['status']} | {item['confidence']} | rev {item['revision']}"
        for item in evidence["records"]
    )
    lines.extend(
        [
            "",
            "KNOWLEDGE REVIEW SUMMARY",
            f"{review['review_id']} | {review['module_id']} v{review['module_version']} | {review['confidence']}",
        ]
    )
    lines.extend(
        f"Finding {item['id']} [{item['disposition']}]: {item['finding']}"
        for item in review["findings"]
    )
    lines.append("Assumptions:")
    lines.extend(f"- {item['statement']}" for item in review["assumptions"])
    lines.append("Unknowns:")
    lines.extend(f"- {item['statement']}" for item in review["unknowns"])
    lines.append("Missing evidence:")
    lines.extend(
        f"- {item['category']}: {item['reason']}" for item in review["missing_evidence"]
    )
    lines.extend(
        [
            "",
            "S.P.A.T.I.A.L. ASSESSMENT SUMMARY",
            f"{assessment['assessment_id']} | Engine {assessment['engine_version']}",
            f"Recommendation: {assessment['recommendation']} | Score: {assessment['score']}/100 | Confidence: {assessment['confidence']}",
            f"Risk profile: {assessment['risk_profile'].get('level', '')}",
            f"Explanation: {assessment['explanation'].get('engine', '')}",
        ]
    )
    lines.extend(
        f"Gate {key}: {value.get('status', '')} - {value.get('rationale', '')}"
        for key, value in assessment["gate_results"].items()
    )
    lines.extend(
        [
            "",
            "TRACEABILITY",
            document["traceability"]["display"],
            "",
            "REPLAY INFORMATION",
            f"Replay hash: {replay['replay_hash']}",
            f"Input hash: {replay['input_hash']}",
            f"Assessment replay hash: {replay['assessment_replay_hash']}",
            f"Engine input hash: {replay['engine_input_hash']}",
            f"Engine version: {replay['engine_version']} | Module version: {replay['module_version']}",
            "",
        ]
    )
    lines.extend(document["footer"])
    lines.append(f"Recorded state timestamp: {document['report_state_timestamp']}")
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(textwrap.wrap(str(line), width=92, subsequent_indent="  ") or [""])
    return wrapped


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_pdf(document: dict[str, Any]) -> bytes:
    """Create a deterministic, standards-compliant text PDF using only stdlib."""

    lines = _pdf_lines(document)
    page_capacity = 44
    pages = [
        lines[index : index + page_capacity]
        for index in range(0, len(lines), page_capacity)
    ] or [[]]
    page_ids = [4 + index * 2 for index in range(len(pages))]
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            f"<< /Type /Pages /Count {len(pages)} /Kids "
            f"[{' '.join(f'{value} 0 R' for value in page_ids)}] >>"
        ).encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for index, page in enumerate(pages):
        page_id = page_ids[index]
        content_id = page_id + 1
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        commands = ["BT", "/F1 10 Tf", "50 748 Td", "14 TL"]
        for line in page:
            safe = str(line).encode("latin-1", errors="replace").decode("latin-1")
            commands.extend([f"({_pdf_escape(safe)}) Tj", "T*"])
        commands.append("ET")
        footer = f"{document['dossier_id']} | Page {index + 1} of {len(pages)}"
        commands.extend(
            [
                "BT",
                "/F1 8 Tf",
                "50 28 Td",
                f"({_pdf_escape(footer)}) Tj",
                "ET",
            ]
        )
        stream = "\n".join(commands).encode("latin-1")
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
    payload = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{number} 0 obj\n".encode("ascii"))
        payload.extend(obj)
        payload.extend(b"\nendobj\n")
    xref = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(payload)


def build_artifacts(
    dossier_id: str, snapshot: dict[str, Any]
) -> tuple[dict[str, Any], str, bytes, bytes, str, str]:
    document, input_hash, replay_hash = build_document(dossier_id, snapshot)
    html = render_html(document)
    return (
        document,
        html,
        render_pdf(document),
        render_json(document),
        input_hash,
        replay_hash,
    )
