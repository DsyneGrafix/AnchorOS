"""AIN-101 — AnchorInsight Commercial Intelligence Registry Service.

This service is the controlled application boundary between websites/APIs and
the CIR-002 persistence layer. Callers do not execute raw SQL.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse

from .db import RegistryDatabase, utc_now
from .errors import ConflictError, NotFoundError, ValidationError


MARKET_STATES = {
    "Observed", "Investigating", "Qualified", "Active", "Scaling", "Monitor", "Archive"
}
COF_STATUSES = {
    "Observed", "Investigating", "Validate", "Monitor", "Hold", "Pursue", "Reject", "Archive"
}
PRIORITIES = {"High", "Medium", "Low"}
EVIDENCE_CLASSES = {"Verified", "Supported", "Assumption", "Unknown", "Disputed"}
ACTION_STATES = {"Open", "In Progress", "Blocked", "Completed", "Cancelled", "Archived"}


@dataclass(frozen=True, slots=True)
class ServiceHealth:
    name: str
    version: str
    status: str
    database: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "database": self.database,
        }


class CommercialIntelligenceRegistryService:
    """Validated business service for AnchorInsight registry operations."""

    name = "Commercial Intelligence Registry Service"
    version = "1.0.0"

    def __init__(self, database: RegistryDatabase | str | Path) -> None:
        self.db = database if isinstance(database, RegistryDatabase) else RegistryDatabase(database)
        self.db.initialize()

    # ------------------------------------------------------------------
    # Health and read access
    # ------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        db_health = self.db.health()
        status = "HEALTHY" if db_health["status"] == "HEALTHY" else "DEGRADED"
        return ServiceHealth(self.name, self.version, status, db_health).to_dict()

    def get_market(self, identifier: str) -> dict[str, Any]:
        return self._fetch_one(
            """
            SELECT * FROM markets
            WHERE market_id = ? OR cof_market_id = ?
            """,
            (identifier, identifier),
            "Market",
            identifier,
        )

    def list_markets(
        self,
        *,
        lifecycle_state: str | None = None,
        priority: str | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if lifecycle_state:
            self._require_choice("lifecycle_state", lifecycle_state, MARKET_STATES)
            clauses.append("lifecycle_state = ?")
            params.append(lifecycle_state)
        if priority:
            self._require_choice("priority", priority, PRIORITIES)
            clauses.append("priority = ?")
            params.append(priority)
        if not include_archived:
            clauses.append("status <> 'Archived'")
        return self._fetch_all(
            "SELECT * FROM markets"
            + (" WHERE " + " AND ".join(clauses) if clauses else "")
            + " ORDER BY priority, name",
            tuple(params),
        )

    def get_organization(self, identifier: str) -> dict[str, Any]:
        return self._fetch_one(
            """
            SELECT * FROM organizations
            WHERE organization_id = ? OR cof_organization_id = ?
            """,
            (identifier, identifier),
            "Organization",
            identifier,
        )

    def list_organizations(
        self,
        *,
        market_identifier: str | None = None,
        cof_status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        include_archived: bool = False,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        if limit < 1 or limit > 1000:
            raise ValidationError("limit must be between 1 and 1000")
        clauses: list[str] = []
        params: list[Any] = []
        joins = ""
        if market_identifier:
            market = self.get_market(market_identifier)
            joins = (
                " JOIN market_organization_memberships mom"
                " ON mom.organization_id = o.organization_id"
            )
            clauses.append("mom.market_id = ?")
            params.append(market["market_id"])
        if cof_status:
            self._require_choice("cof_status", cof_status, COF_STATUSES)
            clauses.append("o.cof_status = ?")
            params.append(cof_status)
        if priority:
            self._require_choice("priority", priority, PRIORITIES)
            clauses.append("o.priority = ?")
            params.append(priority)
        if search:
            term = f"%{search.strip().casefold()}%"
            clauses.append(
                "(o.normalized_name LIKE ? OR LOWER(COALESCE(o.common_name,'')) LIKE ? "
                "OR LOWER(COALESCE(o.sector,'')) LIKE ?)"
            )
            params.extend([term, term, term])
        if not include_archived:
            clauses.append("o.status <> 'Archived'")
        params.append(limit)
        sql = (
            "SELECT DISTINCT o.* FROM organizations o"
            + joins
            + (" WHERE " + " AND ".join(clauses) if clauses else "")
            + " ORDER BY o.priority, COALESCE(o.common_name, o.legal_name) LIMIT ?"
        )
        return self._fetch_all(sql, tuple(params))

    # ------------------------------------------------------------------
    # Market and organization commands
    # ------------------------------------------------------------------

    def create_market(
        self,
        *,
        name: str,
        definition: str,
        owner: str | None = None,
        lifecycle_state: str = "Investigating",
        decision_outcome: str | None = "Validate",
        priority: str = "High",
        geographic_scope: str | None = None,
        actor: str,
        reason: str = "Market registered.",
        cof_market_id: str | None = None,
    ) -> dict[str, Any]:
        name = self._required_text("name", name)
        definition = self._required_text("definition", definition)
        actor = self._required_text("actor", actor)
        self._require_choice("lifecycle_state", lifecycle_state, MARKET_STATES)
        self._require_choice("priority", priority, PRIORITIES)

        if cof_market_id:
            self._reserve_explicit_cof_id("market", cof_market_id)
        try:
            record = self.db.create_market(
                name=name,
                definition=definition,
                lifecycle_state=lifecycle_state,
                decision_outcome=decision_outcome,
                priority=priority,
                cof_market_id=cof_market_id,
            )
            if owner or geographic_scope:
                now = utc_now()
                with self.db.transaction() as connection:
                    connection.execute(
                        """
                        UPDATE markets
                        SET owner = ?, geographic_scope = ?, updated_at = ?
                        WHERE market_id = ?
                        """,
                        (owner, geographic_scope, now, record["market_id"]),
                    )
            current = self.get_market(record["market_id"])
            self._audit(
                actor=actor,
                action="market.created",
                subject_type="Market",
                subject_id=current["market_id"],
                previous=None,
                new=current,
                reason=reason,
            )
            return current
        except sqlite3.IntegrityError as exc:
            raise ConflictError(f"Market already exists or violates a constraint: {name}") from exc

    def create_organization(
        self,
        *,
        legal_name: str,
        role: str,
        actor: str,
        common_name: str | None = None,
        industry: str | None = None,
        sector: str | None = None,
        website: str | None = None,
        headquarters: str | None = None,
        cof_status: str = "Validate",
        priority: str = "High",
        strategic_value: str | None = None,
        owner: str | None = None,
        reason: str = "Organization registered.",
        cof_organization_id: str | None = None,
    ) -> dict[str, Any]:
        legal_name = self._required_text("legal_name", legal_name)
        role = self._required_text("role", role)
        actor = self._required_text("actor", actor)
        self._require_choice("cof_status", cof_status, COF_STATUSES)
        self._require_choice("priority", priority, PRIORITIES)
        if website:
            parsed = urlparse(website if "://" in website else f"https://{website}")
            if not parsed.netloc:
                raise ValidationError("website must contain a valid host")

        if cof_organization_id:
            self._reserve_explicit_cof_id("organization", cof_organization_id)
        try:
            record = self.db.create_organization(
                legal_name=legal_name,
                role=role,
                common_name=common_name,
                industry=industry,
                sector=sector,
                website=website,
                headquarters=headquarters,
                cof_status=cof_status,
                priority=priority,
                strategic_value=strategic_value,
                cof_organization_id=cof_organization_id,
            )
            now = utc_now()
            lifecycle_id = self.db.internal_id()
            lifecycle_cof_id = self.db.next_cof_id("lifecycle_event")
            with self.db.transaction() as connection:
                if owner:
                    connection.execute(
                        "UPDATE organizations SET owner = ?, updated_at = ? WHERE organization_id = ?",
                        (owner, now, record["organization_id"]),
                    )
                connection.execute(
                    """
                    INSERT INTO lifecycle_events(
                        lifecycle_event_id, cof_lifecycle_event_id, subject_type,
                        subject_id, event_type, previous_state, new_state, reason,
                        actor, occurred_at, created_at
                    ) VALUES (?, ?, 'Organization', ?, 'organization.registered',
                              NULL, ?, ?, ?, ?, ?)
                    """,
                    (
                        lifecycle_id,
                        lifecycle_cof_id,
                        record["organization_id"],
                        cof_status,
                        reason,
                        actor,
                        now,
                        now,
                    ),
                )
            current = self.get_organization(record["organization_id"])
            self._audit(
                actor=actor,
                action="organization.created",
                subject_type="Organization",
                subject_id=current["organization_id"],
                previous=None,
                new=current,
                reason=reason,
            )
            return current
        except sqlite3.IntegrityError as exc:
            raise ConflictError(
                f"Organization already exists or violates a constraint: {legal_name}"
            ) from exc

    def add_market_membership(
        self,
        *,
        market_identifier: str,
        organization_identifier: str,
        actor: str,
        relevance: str = "Primary",
        market_role: str | None = None,
        priority: str = "High",
        reason: str = "Organization linked to market.",
    ) -> dict[str, Any]:
        actor = self._required_text("actor", actor)
        self._require_choice("priority", priority, PRIORITIES)
        market = self.get_market(market_identifier)
        organization = self.get_organization(organization_identifier)
        try:
            membership = self.db.add_market_membership(
                market["market_id"],
                organization["organization_id"],
                relevance=relevance,
                market_role=market_role,
                priority=priority,
            )
            self._audit(
                actor=actor,
                action="market_membership.created",
                subject_type="Organization",
                subject_id=organization["organization_id"],
                previous=None,
                new=membership,
                reason=reason,
            )
            return membership
        except sqlite3.IntegrityError as exc:
            raise ConflictError("Organization is already linked to this market") from exc

    # ------------------------------------------------------------------
    # Evidence, scoring, and action commands
    # ------------------------------------------------------------------

    def create_source(
        self,
        *,
        source_type: str,
        title: str,
        actor: str,
        publisher: str | None = None,
        url: str | None = None,
        publication_date: str | None = None,
        author: str | None = None,
        confidentiality: str = "Public",
        content: bytes | str | None = None,
    ) -> dict[str, Any]:
        source_type = self._required_text("source_type", source_type)
        title = self._required_text("title", title)
        actor = self._required_text("actor", actor)
        if confidentiality not in {"Public", "Internal", "Confidential", "Restricted"}:
            raise ValidationError("invalid confidentiality")
        checksum = None
        if content is not None:
            raw = content.encode("utf-8") if isinstance(content, str) else content
            checksum = hashlib.sha256(raw).hexdigest()
        now = utc_now()
        source_id = self.db.internal_id()
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id, source_type, title, publisher, url,
                    publication_date, accessed_at, author, checksum_sha256,
                    confidentiality, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
                """,
                (
                    source_id, source_type, title, publisher, url,
                    publication_date, now, author, checksum, confidentiality, now,
                ),
            )
        source = self._fetch_one(
            "SELECT * FROM sources WHERE source_id = ?",
            (source_id,),
            "Source",
            source_id,
        )
        self._audit(
            actor=actor,
            action="source.created",
            subject_type="Source",
            subject_id=source_id,
            previous=None,
            new=source,
            reason="Source captured.",
        )
        return source

    def add_evidence(
        self,
        *,
        source_identifier: str,
        assertion: str,
        evidence_type: str,
        classification: str,
        actor: str,
        subject_type: str | None = None,
        subject_identifier: str | None = None,
        confidence: float | None = None,
        source_date: str | None = None,
        reviewer: str | None = None,
        expires_at: str | None = None,
        relevance: str = "High",
        link_type: str = "Supports",
        assertion_supported: str | None = None,
    ) -> dict[str, Any]:
        assertion = self._required_text("assertion", assertion)
        evidence_type = self._required_text("evidence_type", evidence_type)
        actor = self._required_text("actor", actor)
        self._require_choice("classification", classification, EVIDENCE_CLASSES)
        if confidence is not None and not 0 <= confidence <= 1:
            raise ValidationError("confidence must be between 0 and 1")
        source = self._fetch_one(
            "SELECT * FROM sources WHERE source_id = ? OR url = ?",
            (source_identifier, source_identifier),
            "Source",
            source_identifier,
        )
        evidence_id = self.db.internal_id()
        cof_id = self.db.next_cof_id("evidence")
        now = utc_now()
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO evidence(
                    evidence_id, cof_evidence_id, source_id, assertion,
                    evidence_type, classification, confidence, source_date,
                    captured_at, reviewer, review_date, expires_at,
                    status, content_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
                """,
                (
                    evidence_id, cof_id, source["source_id"], assertion,
                    evidence_type, classification, confidence, source_date,
                    now, reviewer or actor, now, expires_at,
                    source.get("checksum_sha256"), now,
                ),
            )
            if subject_type and subject_identifier:
                resolved = self._resolve_subject(subject_type, subject_identifier)
                connection.execute(
                    """
                    INSERT INTO evidence_links(
                        evidence_link_id, evidence_id, subject_type, subject_id,
                        assertion_supported, relevance, link_type, created_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.db.internal_id(), evidence_id, subject_type,
                        resolved["id"], assertion_supported or assertion,
                        relevance, link_type, actor, now,
                    ),
                )
        evidence = self._fetch_one(
            "SELECT * FROM evidence WHERE evidence_id = ?",
            (evidence_id,),
            "Evidence",
            evidence_id,
        )
        self._audit(
            actor=actor,
            action="evidence.created",
            subject_type="Evidence",
            subject_id=evidence_id,
            previous=None,
            new=evidence,
            reason="Evidence captured and classified.",
            related_evidence_id=evidence_id,
        )
        return evidence

    def create_scorecard(
        self,
        *,
        subject_type: str,
        subject_identifier: str,
        score_model: str,
        model_version: str,
        criterion_scores: Mapping[str, float],
        maximum_score: float,
        decision_outcome: str,
        reviewer: str,
        actor: str,
        recommendation: str | None = None,
        evidence_ids: Sequence[str] = (),
        status: str = "Approved",
    ) -> dict[str, Any]:
        actor = self._required_text("actor", actor)
        reviewer = self._required_text("reviewer", reviewer)
        if not criterion_scores:
            raise ValidationError("criterion_scores cannot be empty")
        if maximum_score <= 0:
            raise ValidationError("maximum_score must be greater than zero")
        if any(value < 0 for value in criterion_scores.values()):
            raise ValidationError("criterion scores cannot be negative")
        if sum(criterion_scores.values()) > maximum_score:
            raise ValidationError("criterion score total exceeds maximum_score")
        resolved = self._resolve_subject(subject_type, subject_identifier)
        scorecard = self.db.create_scorecard(
            subject_type=subject_type,
            subject_id=resolved["id"],
            score_model=score_model,
            model_version=model_version,
            criterion_scores=dict(criterion_scores),
            maximum_score=maximum_score,
            decision_outcome=decision_outcome,
            reviewer=reviewer,
            recommendation=recommendation,
            status=status,
        )
        if evidence_ids:
            now = utc_now()
            with self.db.transaction() as connection:
                for evidence_identifier in evidence_ids:
                    evidence = self._fetch_one_using(
                        connection,
                        """
                        SELECT * FROM evidence
                        WHERE evidence_id = ? OR cof_evidence_id = ?
                        """,
                        (evidence_identifier, evidence_identifier),
                        "Evidence",
                        evidence_identifier,
                    )
                    connection.execute(
                        """
                        INSERT INTO scorecard_evidence(
                            scorecard_id, evidence_id, criterion_name, created_at
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (scorecard["scorecard_id"], evidence["evidence_id"], "", now),
                    )
        self._audit(
            actor=actor,
            action="scorecard.created",
            subject_type=subject_type,
            subject_id=resolved["id"],
            previous=None,
            new=scorecard,
            reason=f"{score_model} scorecard created.",
        )
        return scorecard

    def add_action(
        self,
        *,
        subject_type: str,
        subject_identifier: str,
        description: str,
        actor: str,
        owner: str | None = None,
        priority: str = "Medium",
        due_at: str | None = None,
    ) -> dict[str, Any]:
        description = self._required_text("description", description)
        actor = self._required_text("actor", actor)
        self._require_choice("priority", priority, PRIORITIES)
        subject = self._resolve_subject(subject_type, subject_identifier)
        action_id = self.db.internal_id()
        cof_id = self.db.next_cof_id("action")
        now = utc_now()
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO actions(
                    action_id, cof_action_id, subject_type, subject_id,
                    description, owner, priority, due_at, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Open', ?, ?)
                """,
                (
                    action_id, cof_id, subject_type, subject["id"],
                    description, owner or actor, priority, due_at, now, now,
                ),
            )
        action = self._fetch_one(
            "SELECT * FROM actions WHERE action_id = ?",
            (action_id,),
            "Action",
            action_id,
        )
        self._audit(
            actor=actor,
            action="action.created",
            subject_type=subject_type,
            subject_id=subject["id"],
            previous=None,
            new=action,
            reason="Next action created.",
        )
        return action

    # ------------------------------------------------------------------
    # One-page organization read model
    # ------------------------------------------------------------------

    def get_organization_profile(self, identifier: str) -> dict[str, Any]:
        organization = self.get_organization(identifier)
        oid = organization["organization_id"]
        connection = self.db.connect()
        try:
            profile = {
                "organization": organization,
                "markets": self._rows(connection.execute(
                    """
                    SELECT m.*, mom.cof_membership_id, mom.relevance,
                           mom.market_role, mom.priority AS membership_priority,
                           mom.lifecycle_state AS membership_state
                    FROM markets m
                    JOIN market_organization_memberships mom ON mom.market_id = m.market_id
                    WHERE mom.organization_id = ?
                    ORDER BY CASE mom.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                             m.name
                    """,
                    (oid,),
                ).fetchall()),
                "contacts": self._rows(connection.execute(
                    "SELECT * FROM contacts WHERE organization_id = ? AND status <> 'Archived' ORDER BY full_name",
                    (oid,),
                ).fetchall()),
                "opportunities": self._rows(connection.execute(
                    "SELECT * FROM opportunities WHERE organization_id = ? ORDER BY updated_at DESC",
                    (oid,),
                ).fetchall()),
                "scorecards": self._rows(connection.execute(
                    """
                    SELECT * FROM scorecards
                    WHERE subject_type = 'Organization' AND subject_id = ?
                    ORDER BY assessment_date DESC
                    """,
                    (oid,),
                ).fetchall()),
                "evidence": self._rows(connection.execute(
                    """
                    SELECT e.*, el.link_type, el.relevance, s.title AS source_title,
                           s.publisher, s.url
                    FROM evidence e
                    JOIN evidence_links el ON el.evidence_id = e.evidence_id
                    JOIN sources s ON s.source_id = e.source_id
                    WHERE el.subject_type = 'Organization' AND el.subject_id = ?
                    ORDER BY e.captured_at DESC
                    """,
                    (oid,),
                ).fetchall()),
                "assumptions": self._rows(connection.execute(
                    """
                    SELECT * FROM assumptions
                    WHERE subject_type = 'Organization' AND subject_id = ?
                    AND status <> 'Archived' ORDER BY created_at DESC
                    """,
                    (oid,),
                ).fetchall()),
                "risks": self._rows(connection.execute(
                    """
                    SELECT * FROM risks
                    WHERE subject_type = 'Organization' AND subject_id = ?
                    AND status <> 'Archived'
                    ORDER BY risk_score DESC, created_at DESC
                    """,
                    (oid,),
                ).fetchall()),
                "open_actions": self._rows(connection.execute(
                    """
                    SELECT * FROM actions
                    WHERE subject_type = 'Organization' AND subject_id = ?
                    AND status NOT IN ('Completed','Cancelled','Archived')
                    ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                             due_at IS NULL, due_at
                    """,
                    (oid,),
                ).fetchall()),
                "lifecycle": self._rows(connection.execute(
                    """
                    SELECT * FROM lifecycle_events
                    WHERE subject_type = 'Organization' AND subject_id = ?
                    ORDER BY occurred_at DESC
                    """,
                    (oid,),
                ).fetchall()),
            }
            profile["summary"] = self._organization_summary(profile)
            return profile
        finally:
            connection.close()

    def export_organization_profile(self, identifier: str) -> dict[str, Any]:
        """Return a JSON-safe profile payload for AOS-180 or an API response."""
        return json.loads(json.dumps(self.get_organization_profile(identifier), default=str))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _organization_summary(self, profile: Mapping[str, Any]) -> dict[str, Any]:
        current_by_model: dict[str, dict[str, Any]] = {}
        for scorecard in profile["scorecards"]:
            current_by_model.setdefault(scorecard["score_model"], scorecard)
        return {
            "market_count": len(profile["markets"]),
            "contact_count": len(profile["contacts"]),
            "opportunity_count": len(profile["opportunities"]),
            "evidence_count": len(profile["evidence"]),
            "open_action_count": len(profile["open_actions"]),
            "current_scores": {
                model: {
                    "score": item["normalized_score"],
                    "decision": item["decision_outcome"],
                    "recommendation": item["recommendation"],
                    "assessed_at": item["assessment_date"],
                }
                for model, item in current_by_model.items()
            },
        }

    def _resolve_subject(self, subject_type: str, identifier: str) -> dict[str, str]:
        subject_type = self._required_text("subject_type", subject_type)
        if subject_type == "Organization":
            record = self.get_organization(identifier)
            return {"id": record["organization_id"], "cof_id": record["cof_organization_id"]}
        if subject_type == "Market":
            record = self.get_market(identifier)
            return {"id": record["market_id"], "cof_id": record["cof_market_id"]}
        if subject_type == "Opportunity":
            record = self._fetch_one(
                """
                SELECT * FROM opportunities
                WHERE opportunity_id = ? OR cof_opportunity_id = ?
                """,
                (identifier, identifier),
                "Opportunity",
                identifier,
            )
            return {"id": record["opportunity_id"], "cof_id": record["cof_opportunity_id"]}
        raise ValidationError(f"Unsupported subject_type: {subject_type}")


    def _reserve_explicit_cof_id(self, entity_type: str, cof_id: str) -> None:
        """Advance the yearly sequence so imported explicit IDs are not reissued."""
        key = entity_type.strip().lower()
        prefix = {
            "market": "MKT",
            "organization": "ORG",
        }.get(key)
        if prefix is None:
            raise ValidationError(f"Explicit COF ID reservation unsupported for {entity_type}")
        match = __import__("re").fullmatch(
            rf"COF-{prefix}-(\d{{4}})-(\d{{3,}})", cof_id.strip()
        )
        if not match:
            raise ValidationError(
                f"Invalid explicit COF ID for {entity_type}: {cof_id}"
            )
        year, value = int(match.group(1)), int(match.group(2))
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO cof_id_sequences(entity_type, year, last_value)
                VALUES (?, ?, 0)
                """,
                (key, year),
            )
            connection.execute(
                """
                UPDATE cof_id_sequences
                SET last_value = CASE
                    WHEN last_value < ? THEN ?
                    ELSE last_value
                END
                WHERE entity_type = ? AND year = ?
                """,
                (value, value, key, year),
            )

    def _audit(
        self,
        *,
        actor: str,
        action: str,
        subject_type: str,
        subject_id: str,
        previous: Mapping[str, Any] | None,
        new: Mapping[str, Any] | None,
        reason: str,
        related_evidence_id: str | None = None,
    ) -> None:
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO registry_audit_log(
                    audit_id, actor, action, subject_type, subject_id,
                    previous_value_json, new_value_json, reason,
                    related_evidence_id, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.db.internal_id(), actor, action, subject_type, subject_id,
                    json.dumps(previous, default=str, sort_keys=True) if previous else None,
                    json.dumps(new, default=str, sort_keys=True) if new else None,
                    reason, related_evidence_id, utc_now(),
                ),
            )

    def _fetch_one(
        self,
        sql: str,
        params: Sequence[Any],
        label: str,
        identifier: str,
    ) -> dict[str, Any]:
        connection = self.db.connect()
        try:
            return self._fetch_one_using(connection, sql, params, label, identifier)
        finally:
            connection.close()

    @staticmethod
    def _fetch_one_using(
        connection: sqlite3.Connection,
        sql: str,
        params: Sequence[Any],
        label: str,
        identifier: str,
    ) -> dict[str, Any]:
        row = connection.execute(sql, params).fetchone()
        if row is None:
            raise NotFoundError(f"{label} not found: {identifier}")
        return dict(row)

    def _fetch_all(self, sql: str, params: Sequence[Any]) -> list[dict[str, Any]]:
        connection = self.db.connect()
        try:
            return self._rows(connection.execute(sql, params).fetchall())
        finally:
            connection.close()

    @staticmethod
    def _rows(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

    @staticmethod
    def _required_text(field: str, value: str) -> str:
        clean = value.strip() if isinstance(value, str) else ""
        if not clean:
            raise ValidationError(f"{field} is required")
        return clean

    @staticmethod
    def _require_choice(field: str, value: str, allowed: set[str]) -> None:
        if value not in allowed:
            raise ValidationError(
                f"{field} must be one of: {', '.join(sorted(allowed))}"
            )
