"""SQLite persistence for AnchorIntel v1 business resources."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .errors import ApiError


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


class Repository:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._memory_connection: sqlite3.Connection | None = None
        if self.database_path == ":memory:":
            self._memory_connection = self._new_connection()
        self.initialize()

    def _new_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = self._memory_connection or self._new_connection()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            if self._memory_connection is None:
                connection.close()

    def close(self) -> None:
        if self._memory_connection is not None:
            self._memory_connection.close()
            self._memory_connection = None

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS opportunities (
                    opportunity_id TEXT PRIMARY KEY,
                    record_json TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL DEFAULT 'Unassessed',
                    archived INTEGER NOT NULL DEFAULT 0,
                    revision INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(opportunity_id) REFERENCES opportunities(opportunity_id)
                );

                CREATE INDEX IF NOT EXISTS evidence_opportunity_idx
                    ON evidence(opportunity_id);

                CREATE TABLE IF NOT EXISTS assessments (
                    assessment_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL,
                    input_snapshot_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    report_markdown TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    score REAL NOT NULL,
                    evidence_confidence TEXT NOT NULL,
                    supersedes_assessment_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(opportunity_id) REFERENCES opportunities(opportunity_id),
                    FOREIGN KEY(supersedes_assessment_id) REFERENCES assessments(assessment_id)
                );

                CREATE INDEX IF NOT EXISTS assessments_opportunity_idx
                    ON assessments(opportunity_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS lifecycle_events (
                    event_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    assessment_id TEXT,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(opportunity_id) REFERENCES opportunities(opportunity_id),
                    FOREIGN KEY(assessment_id) REFERENCES assessments(assessment_id)
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _audit(
        db: sqlite3.Connection,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        db.execute(
            "INSERT INTO audit_log(actor, action, entity_type, entity_id, details_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (actor, action, entity_type, entity_id, json.dumps(details or {}), utcnow()),
        )

    @staticmethod
    def _opportunity_row(row: sqlite3.Row) -> dict[str, Any]:
        record = json.loads(row["record_json"])
        record.update(
            {
                "lifecycle_state": row["lifecycle_state"],
                "archived": bool(row["archived"]),
                "revision": row["revision"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
        return record

    @staticmethod
    def _evidence_row(row: sqlite3.Row) -> dict[str, Any]:
        record = json.loads(row["record_json"])
        record.update(
            {
                "opportunity_id": row["opportunity_id"],
                "state": row["classification"],
                "revision": row["revision"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
        return record

    def create_opportunity(self, record: dict[str, Any], actor: str) -> dict[str, Any]:
        opportunity_id = record.get("opportunity_id") or new_id("OPP")
        record = dict(record)
        record["opportunity_id"] = opportunity_id
        now = utcnow()
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO opportunities(opportunity_id, record_json, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (opportunity_id, json.dumps(record), now, now),
                )
                self._audit(db, actor, "opportunity.created", "opportunity", opportunity_id)
        except sqlite3.IntegrityError as exc:
            raise ApiError(409, "opportunity_exists", f"Opportunity {opportunity_id} already exists") from exc
        return self.get_opportunity(opportunity_id, include_archived=True)

    def get_opportunity(self, opportunity_id: str, include_archived: bool = False) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM opportunities WHERE opportunity_id = ?", (opportunity_id,)
            ).fetchone()
        if row is None or (row["archived"] and not include_archived):
            raise ApiError(404, "opportunity_not_found", f"Opportunity {opportunity_id} was not found")
        return self._opportunity_row(row)

    def list_opportunities(self, include_archived: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM opportunities"
        params: tuple[Any, ...] = ()
        if not include_archived:
            query += " WHERE archived = 0"
        query += " ORDER BY updated_at DESC"
        with self.connect() as db:
            rows = db.execute(query, params).fetchall()
        return [self._opportunity_row(row) for row in rows]

    def update_opportunity(
        self,
        opportunity_id: str,
        record: dict[str, Any],
        actor: str,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        current = self.get_opportunity(opportunity_id, include_archived=True)
        if current["archived"]:
            raise ApiError(409, "opportunity_archived", "Archived opportunities cannot be updated")
        if expected_revision is not None and current["revision"] != expected_revision:
            raise ApiError(
                409,
                "revision_conflict",
                "Opportunity revision does not match If-Match",
                {"expected": expected_revision, "actual": current["revision"]},
            )
        clean = dict(record)
        clean["opportunity_id"] = opportunity_id
        now = utcnow()
        with self.connect() as db:
            db.execute(
                "UPDATE opportunities SET record_json = ?, revision = revision + 1, updated_at = ? "
                "WHERE opportunity_id = ?",
                (json.dumps(clean), now, opportunity_id),
            )
            self._audit(
                db,
                actor,
                "opportunity.updated",
                "opportunity",
                opportunity_id,
                {"previous_revision": current["revision"]},
            )
        return self.get_opportunity(opportunity_id, include_archived=True)

    def archive_opportunity(self, opportunity_id: str, actor: str) -> dict[str, Any]:
        current = self.get_opportunity(opportunity_id, include_archived=True)
        if current["archived"]:
            return current
        now = utcnow()
        with self.connect() as db:
            db.execute(
                "UPDATE opportunities SET archived = 1, lifecycle_state = 'Archived', "
                "revision = revision + 1, updated_at = ? WHERE opportunity_id = ?",
                (now, opportunity_id),
            )
            self._audit(db, actor, "opportunity.archived", "opportunity", opportunity_id)
        return self.get_opportunity(opportunity_id, include_archived=True)

    def create_evidence(self, record: dict[str, Any], actor: str) -> dict[str, Any]:
        opportunity_id = record["opportunity_id"]
        self.get_opportunity(opportunity_id)
        evidence_id = record.get("evidence_id") or new_id("E")
        clean = dict(record)
        clean["evidence_id"] = evidence_id
        clean.pop("opportunity_id", None)
        classification = clean["state"]
        now = utcnow()
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO evidence(evidence_id, opportunity_id, record_json, classification, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (evidence_id, opportunity_id, json.dumps(clean), classification, now, now),
                )
                self._audit(
                    db,
                    actor,
                    "evidence.created",
                    "evidence",
                    evidence_id,
                    {"opportunity_id": opportunity_id, "state": classification},
                )
        except sqlite3.IntegrityError as exc:
            raise ApiError(409, "evidence_exists", f"Evidence {evidence_id} already exists") from exc
        return self.get_evidence(evidence_id)

    def get_evidence(self, evidence_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
        if row is None:
            raise ApiError(404, "evidence_not_found", f"Evidence {evidence_id} was not found")
        return self._evidence_row(row)

    def list_evidence(self, opportunity_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM evidence"
        params: tuple[Any, ...] = ()
        if opportunity_id:
            query += " WHERE opportunity_id = ?"
            params = (opportunity_id,)
        query += " ORDER BY created_at ASC"
        with self.connect() as db:
            rows = db.execute(query, params).fetchall()
        return [self._evidence_row(row) for row in rows]

    def update_evidence(
        self,
        evidence_id: str,
        record: dict[str, Any],
        actor: str,
        action: str,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        current = self.get_evidence(evidence_id)
        if expected_revision is not None and current["revision"] != expected_revision:
            raise ApiError(
                409,
                "revision_conflict",
                "Evidence revision does not match If-Match",
                {"expected": expected_revision, "actual": current["revision"]},
            )
        clean = dict(record)
        clean["evidence_id"] = evidence_id
        clean.pop("opportunity_id", None)
        classification = clean["state"]
        now = utcnow()
        with self.connect() as db:
            db.execute(
                "UPDATE evidence SET record_json = ?, classification = ?, revision = revision + 1, "
                "updated_at = ? WHERE evidence_id = ?",
                (json.dumps(clean), classification, now, evidence_id),
            )
            self._audit(
                db,
                actor,
                action,
                "evidence",
                evidence_id,
                {"from_state": current["state"], "to_state": classification},
            )
        return self.get_evidence(evidence_id)

    def create_assessment(
        self,
        opportunity_id: str,
        input_snapshot: dict[str, Any],
        result: dict[str, Any],
        report_markdown: str,
        actor: str,
        event_type: str,
        reason: str,
        supersedes_assessment_id: str | None = None,
    ) -> dict[str, Any]:
        assessment_id = new_id("ASM")
        now = utcnow()
        current = self.get_opportunity(opportunity_id)
        from_state = current["lifecycle_state"]
        to_state = result["recommendation"]
        event_id = new_id("LEV")
        with self.connect() as db:
            db.execute(
                "INSERT INTO assessments(assessment_id, opportunity_id, input_snapshot_json, "
                "result_json, report_markdown, recommendation, score, evidence_confidence, "
                "supersedes_assessment_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    assessment_id,
                    opportunity_id,
                    json.dumps(input_snapshot),
                    json.dumps(result),
                    report_markdown,
                    to_state,
                    result["score"],
                    result["confidence"],
                    supersedes_assessment_id,
                    now,
                ),
            )
            db.execute(
                "UPDATE opportunities SET lifecycle_state = ?, updated_at = ? WHERE opportunity_id = ?",
                (to_state, now, opportunity_id),
            )
            db.execute(
                "INSERT INTO lifecycle_events(event_id, opportunity_id, event_type, from_state, "
                "to_state, assessment_id, reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (event_id, opportunity_id, event_type, from_state, to_state, assessment_id, reason, now),
            )
            self._audit(
                db,
                actor,
                f"assessment.{event_type}",
                "assessment",
                assessment_id,
                {"opportunity_id": opportunity_id, "from_state": from_state, "to_state": to_state},
            )
        return self.get_assessment(assessment_id, include_report=False)

    def get_assessment(self, assessment_id: str, include_report: bool = True) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM assessments WHERE assessment_id = ?", (assessment_id,)
            ).fetchone()
        if row is None:
            raise ApiError(404, "assessment_not_found", f"Assessment {assessment_id} was not found")
        result = {
            "assessment_id": row["assessment_id"],
            "opportunity_id": row["opportunity_id"],
            "result": json.loads(row["result_json"]),
            "supersedes_assessment_id": row["supersedes_assessment_id"],
            "created_at": row["created_at"],
        }
        if include_report:
            result["report_markdown"] = row["report_markdown"]
        return result

    def latest_assessment(self, opportunity_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT assessment_id FROM assessments WHERE opportunity_id = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (opportunity_id,),
            ).fetchone()
        return self.get_assessment(row["assessment_id"]) if row else None

    def list_by_state(self, state: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM opportunities WHERE archived = 0 AND lifecycle_state = ? "
                "ORDER BY updated_at DESC",
                (state,),
            ).fetchall()
        return [self._opportunity_row(row) for row in rows]

    def list_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM audit_log ORDER BY audit_id DESC LIMIT ?", (min(max(limit, 1), 500),)
            ).fetchall()
        return [
            {
                "audit_id": row["audit_id"],
                "actor": row["actor"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "details": json.loads(row["details_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

