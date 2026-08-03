
"""CIR-002 SQLite database bootstrap and verification helpers."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

SCHEMA_VERSION = 1
ENTITY_PREFIXES = {
    "market": "MKT",
    "organization": "ORG",
    "membership": "MEM",
    "contact": "CON",
    "relationship": "REL",
    "opportunity": "OPP",
    "topic": "TOP",
    "signal": "SIG",
    "evidence": "EVD",
    "assessment": "AST",
    "scorecard": "SCR",
    "assumption": "ASM",
    "risk": "RSK",
    "action": "ACT",
    "lifecycle_event": "LCE",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RegistryDatabase:
    """Owns SQLite connection lifecycle and schema initialization."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self, schema_path: str | Path | None = None) -> None:
        if schema_path is None:
            schema_path = Path(__file__).with_name("schema.sql")
        sql = Path(schema_path).read_text(encoding="utf-8")
        connection = self.connect()
        try:
            connection.executescript(sql)
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations(version, name, applied_at)
                VALUES (?, ?, ?)
                """,
                (SCHEMA_VERSION, "initial_registry_schema", utc_now()),
            )
            connection.commit()
        finally:
            connection.close()

    def health(self) -> dict[str, Any]:
        connection = self.connect()
        try:
            version_row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
            ).fetchone()
            fk_issues = connection.execute("PRAGMA foreign_key_check").fetchall()
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            return {
                "database": str(self.database_path),
                "schema_version": version_row["version"],
                "foreign_key_issues": len(fk_issues),
                "integrity": integrity,
                "status": "HEALTHY"
                if version_row["version"] == SCHEMA_VERSION
                and not fk_issues
                and integrity == "ok"
                else "DEGRADED",
            }
        finally:
            connection.close()

    def next_cof_id(self, entity_type: str, year: int | None = None) -> str:
        key = entity_type.strip().lower()
        if key not in ENTITY_PREFIXES:
            raise ValueError(f"Unsupported COF entity type: {entity_type}")
        year = year or datetime.now(timezone.utc).year
        with self.transaction() as connection:
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
                SET last_value = last_value + 1
                WHERE entity_type = ? AND year = ?
                """,
                (key, year),
            )
            value = connection.execute(
                """
                SELECT last_value FROM cof_id_sequences
                WHERE entity_type = ? AND year = ?
                """,
                (key, year),
            ).fetchone()["last_value"]
        return f"COF-{ENTITY_PREFIXES[key]}-{year}-{value:03d}"

    @staticmethod
    def internal_id() -> str:
        return str(uuid4())

    def create_market(
        self,
        *,
        name: str,
        definition: str,
        lifecycle_state: str = "Investigating",
        decision_outcome: str | None = "Validate",
        priority: str = "High",
        cof_market_id: str | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        record = {
            "market_id": self.internal_id(),
            "cof_market_id": cof_market_id or self.next_cof_id("market"),
            "name": name.strip(),
            "normalized_name": name.strip().casefold(),
            "definition": definition.strip(),
            "lifecycle_state": lifecycle_state,
            "decision_outcome": decision_outcome,
            "priority": priority,
            "created_at": now,
            "updated_at": now,
        }
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO markets(
                    market_id, cof_market_id, name, normalized_name, definition,
                    lifecycle_state, decision_outcome, priority, created_at, updated_at
                ) VALUES (
                    :market_id, :cof_market_id, :name, :normalized_name, :definition,
                    :lifecycle_state, :decision_outcome, :priority, :created_at, :updated_at
                )
                """,
                record,
            )
        return record

    def create_organization(
        self,
        *,
        legal_name: str,
        role: str,
        common_name: str | None = None,
        industry: str | None = None,
        sector: str | None = None,
        website: str | None = None,
        headquarters: str | None = None,
        cof_status: str = "Validate",
        priority: str = "High",
        strategic_value: str | None = None,
        cof_organization_id: str | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        primary_domain = None
        if website:
            primary_domain = (
                website.replace("https://", "")
                .replace("http://", "")
                .split("/")[0]
                .lower()
            )
        record = {
            "organization_id": self.internal_id(),
            "cof_organization_id": cof_organization_id
            or self.next_cof_id("organization"),
            "legal_name": legal_name.strip(),
            "common_name": common_name,
            "normalized_name": legal_name.strip().casefold(),
            "primary_domain": primary_domain,
            "industry": industry,
            "sector": sector,
            "role": role,
            "website": website,
            "headquarters": headquarters,
            "cof_status": cof_status,
            "strategic_value": strategic_value,
            "priority": priority,
            "created_at": now,
            "updated_at": now,
        }
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO organizations(
                    organization_id, cof_organization_id, legal_name, common_name,
                    normalized_name, primary_domain, industry, sector, role,
                    website, headquarters, cof_status, strategic_value, priority,
                    created_at, updated_at
                ) VALUES (
                    :organization_id, :cof_organization_id, :legal_name, :common_name,
                    :normalized_name, :primary_domain, :industry, :sector, :role,
                    :website, :headquarters, :cof_status, :strategic_value, :priority,
                    :created_at, :updated_at
                )
                """,
                record,
            )
        return record

    def add_market_membership(
        self,
        market_id: str,
        organization_id: str,
        *,
        relevance: str = "Primary",
        market_role: str | None = None,
        priority: str = "High",
    ) -> dict[str, Any]:
        now = utc_now()
        record = {
            "membership_id": self.internal_id(),
            "cof_membership_id": self.next_cof_id("membership"),
            "market_id": market_id,
            "organization_id": organization_id,
            "relevance": relevance,
            "market_role": market_role,
            "priority": priority,
            "created_at": now,
            "updated_at": now,
        }
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO market_organization_memberships(
                    membership_id, cof_membership_id, market_id, organization_id,
                    relevance, market_role, priority, created_at, updated_at
                ) VALUES (
                    :membership_id, :cof_membership_id, :market_id, :organization_id,
                    :relevance, :market_role, :priority, :created_at, :updated_at
                )
                """,
                record,
            )
        return record

    def create_scorecard(
        self,
        *,
        subject_type: str,
        subject_id: str,
        score_model: str,
        model_version: str,
        criterion_scores: dict[str, float],
        maximum_score: float,
        decision_outcome: str,
        reviewer: str,
        recommendation: str | None = None,
        status: str = "Approved",
        supersedes_scorecard_id: str | None = None,
    ) -> dict[str, Any]:
        total_score = float(sum(criterion_scores.values()))
        normalized_score = round(total_score / maximum_score * 100, 2)
        now = utc_now()
        record = {
            "scorecard_id": self.internal_id(),
            "cof_scorecard_id": self.next_cof_id("scorecard"),
            "subject_type": subject_type,
            "subject_id": subject_id,
            "score_model": score_model,
            "model_version": model_version,
            "criterion_scores_json": json.dumps(
                criterion_scores, sort_keys=True
            ),
            "maximum_score": maximum_score,
            "total_score": total_score,
            "normalized_score": normalized_score,
            "decision_outcome": decision_outcome,
            "recommendation": recommendation,
            "reviewer": reviewer,
            "assessment_date": now,
            "effective_at": now,
            "supersedes_scorecard_id": supersedes_scorecard_id,
            "status": status,
            "created_at": now,
        }
        with self.transaction() as connection:
            if supersedes_scorecard_id:
                connection.execute(
                    """
                    UPDATE scorecards
                    SET status = 'Superseded'
                    WHERE scorecard_id = ? AND status IN ('Draft','Under Review')
                    """,
                    (supersedes_scorecard_id,),
                )
            connection.execute(
                """
                INSERT INTO scorecards(
                    scorecard_id, cof_scorecard_id, subject_type, subject_id,
                    score_model, model_version, criterion_scores_json,
                    maximum_score, total_score, normalized_score,
                    decision_outcome, recommendation, reviewer, assessment_date,
                    effective_at, supersedes_scorecard_id, status, created_at
                ) VALUES (
                    :scorecard_id, :cof_scorecard_id, :subject_type, :subject_id,
                    :score_model, :model_version, :criterion_scores_json,
                    :maximum_score, :total_score, :normalized_score,
                    :decision_outcome, :recommendation, :reviewer, :assessment_date,
                    :effective_at, :supersedes_scorecard_id, :status, :created_at
                )
                """,
                record,
            )
        return record

    def organization_profile(self, organization_id: str) -> dict[str, Any]:
        connection = self.connect()
        try:
            organization = connection.execute(
                "SELECT * FROM organizations WHERE organization_id = ?",
                (organization_id,),
            ).fetchone()
            if organization is None:
                raise KeyError(f"Organization not found: {organization_id}")

            markets = connection.execute(
                """
                SELECT m.*, mom.relevance, mom.market_role, mom.priority AS membership_priority
                FROM markets m
                JOIN market_organization_memberships mom ON mom.market_id = m.market_id
                WHERE mom.organization_id = ?
                ORDER BY mom.priority, m.name
                """,
                (organization_id,),
            ).fetchall()

            scorecards = connection.execute(
                """
                SELECT * FROM scorecards
                WHERE subject_type = 'Organization' AND subject_id = ?
                ORDER BY assessment_date DESC
                """,
                (organization_id,),
            ).fetchall()

            actions = connection.execute(
                """
                SELECT * FROM actions
                WHERE subject_type = 'Organization' AND subject_id = ?
                AND status NOT IN ('Completed','Cancelled','Archived')
                ORDER BY due_at IS NULL, due_at
                """,
                (organization_id,),
            ).fetchall()

            return {
                "organization": dict(organization),
                "markets": [dict(row) for row in markets],
                "scorecards": [dict(row) for row in scorecards],
                "open_actions": [dict(row) for row in actions],
            }
        finally:
            connection.close()
