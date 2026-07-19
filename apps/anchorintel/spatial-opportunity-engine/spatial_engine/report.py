"""Markdown and JSON-friendly reporting for S.P.A.T.I.A.L. results."""

from __future__ import annotations

from .models import AnalysisResult, EvidenceItem


def _evidence_lines(items: tuple[EvidenceItem, ...]) -> list[str]:
    if not items:
        return ["- None recorded."]
    lines = []
    for item in items:
        source = f" — {item.source}" if item.source else ""
        lines.append(f"- `{item.evidence_id}` [{item.state.value}] {item.claim}{source}")
    return lines


def render_markdown(result: AnalysisResult) -> str:
    provisional = " — PROVISIONAL" if result.provisional else ""
    lines = [
        f"# S.P.A.T.I.A.L. Opportunity Decision — {result.opportunity_id}",
        "",
        f"**Title:** {result.title}  ",
        f"**Assessment date:** {result.assessment_date}  ",
        f"**Methodology:** {result.methodology}  ",
        f"**Engine:** {result.engine_version}  ",
        f"**Recommendation:** **{result.recommendation.value}**{provisional}  ",
        f"**Opportunity Confidence Score:** {result.score:.2f}/100  ",
        f"**Evidence confidence:** {result.confidence.value} ({result.confidence_index:.3f})",
        "",
        "## Decision basis",
        "",
        result.recommendation_reason,
        "",
        "## Weighted score",
        "",
        "| Dimension | Weight | Score | Points | Evidence |",
        "|---|---:|---:|---:|---|",
    ]
    for item in result.dimensions:
        refs = ", ".join(f"`{v}`" for v in item.evidence_refs) or "—"
        lines.append(
            f"| {item.label} | {item.weight} | {item.score:.1f}/5 | "
            f"{item.weighted_points:.2f} | {refs} |"
        )

    lines.extend(["", "## Mandatory gates", "", "| Gate | Status | Rationale |", "|---|---|---|"])
    for key, gate in result.gates.items():
        lines.append(f"| {key} | **{gate.status.value.upper()}** | {gate.rationale} |")

    lines.extend(["", "## Evidence record", "", "### Verified facts", ""])
    lines.extend(_evidence_lines(result.facts))
    lines.extend(["", "### Supported inferences", ""])
    lines.extend(_evidence_lines(result.inferences))
    lines.extend(["", "### Assumptions", ""])
    lines.extend(_evidence_lines(result.assumptions))
    lines.extend(["", "### Unknowns or disputes", ""])
    lines.extend(_evidence_lines(result.unknowns_or_disputes))

    lines.extend(["", "## Fatal constraints", ""])
    if result.fatal_constraints:
        for constraint in result.fatal_constraints:
            lines.append(
                f"- `{constraint.constraint_id}` **{constraint.disposition.value.upper()}** — "
                f"{constraint.description}"
            )
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Known limitations", ""])
    lines.extend(f"- {v}" for v in result.known_limitations or ("None recorded.",))
    lines.extend(
        [
            "",
            "## Authorized lifecycle control",
            "",
            f"- **Owner:** {result.lifecycle.owner or 'Not supplied'}",
            f"- **Next action:** {result.lifecycle.next_action or 'Not supplied'}",
            f"- **Resource ceiling:** {result.lifecycle.resource_ceiling or 'Not supplied'}",
            f"- **Review date:** {result.lifecycle.review_date or 'Not supplied'}",
            "- **Revalidation triggers:** "
            + ("; ".join(result.lifecycle.revalidation_triggers) or "None supplied"),
        ]
    )

    if result.warnings:
        lines.extend(["", "## Review warnings", ""])
        lines.extend(f"- {v}" for v in result.warnings)

    lines.extend(
        [
            "",
            "## Boundary statement",
            "",
            "This result is an opportunity-intelligence decision, not engineering, legal, "
            "funding, safety, cybersecurity, regulatory, or commercial certification.",
            "",
        ]
    )
    return "\n".join(lines)
