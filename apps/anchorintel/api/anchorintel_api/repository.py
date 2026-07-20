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
                    assessment_kind TEXT NOT NULL DEFAULT 'legacy',
                    knowledge_review_id TEXT,
                    engine_version TEXT NOT NULL DEFAULT '',
                    adapter_version TEXT NOT NULL DEFAULT '',
                    replay_hash TEXT NOT NULL DEFAULT '',
                    provenance_json TEXT NOT NULL DEFAULT '{}',
                    revision INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(opportunity_id) REFERENCES opportunities(opportunity_id),
                    FOREIGN KEY(supersedes_assessment_id) REFERENCES assessments(assessment_id),
                    FOREIGN KEY(knowledge_review_id) REFERENCES knowledge_reviews(review_id)
                );

                CREATE INDEX IF NOT EXISTS assessments_opportunity_idx
                    ON assessments(opportunity_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS knowledge_reviews (
                    review_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL,
                    module_id TEXT NOT NULL,
                    module_version TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    supersedes_review_id TEXT,
                    superseded_at TEXT,
                    revision INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(opportunity_id) REFERENCES opportunities(opportunity_id),
                    FOREIGN KEY(supersedes_review_id) REFERENCES knowledge_reviews(review_id)
                );

                CREATE INDEX IF NOT EXISTS knowledge_reviews_opportunity_idx
                    ON knowledge_reviews(opportunity_id, created_at DESC);

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
            evidence_columns = {
                row["name"] for row in db.execute("PRAGMA table_info(evidence)").fetchall()
            }
            if "archived" not in evidence_columns:
                db.execute(
                    "ALTER TABLE evidence ADD COLUMN archived INTEGER NOT NULL DEFAULT 0"
                )
            if "archived_at" not in evidence_columns:
                db.execute("ALTER TABLE evidence ADD COLUMN archived_at TEXT")
            db.execute(
                "CREATE INDEX IF NOT EXISTS evidence_active_opportunity_idx "
                "ON evidence(opportunity_id, archived, created_at)"
            )
            assessment_columns = {
                row["name"] for row in db.execute("PRAGMA table_info(assessments)").fetchall()
            }
            assessment_migrations = {
                "assessment_kind": "TEXT NOT NULL DEFAULT 'legacy'",
                "knowledge_review_id": "TEXT",
                "engine_version": "TEXT NOT NULL DEFAULT ''",
                "adapter_version": "TEXT NOT NULL DEFAULT ''",
                "replay_hash": "TEXT NOT NULL DEFAULT ''",
                "provenance_json": "TEXT NOT NULL DEFAULT '{}'",
                "revision": "INTEGER NOT NULL DEFAULT 1",
                "updated_at": "TEXT NOT NULL DEFAULT ''",
            }
            for column, definition in assessment_migrations.items():
                if column not in assessment_columns:
                    db.execute(f"ALTER TABLE assessments ADD COLUMN {column} {definition}")
            db.execute(
                "UPDATE assessments SET updated_at = created_at WHERE updated_at = ''"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS assessments_kind_opportunity_idx "
                "ON assessments(opportunity_id, assessment_kind, created_at DESC)"
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
        claim = str(record.get("claim", "")).strip()
        record.setdefault("title", claim)
        record.setdefault("description", claim)
        record.setdefault("evidence_type", "Other")
        record.setdefault("evidence_status", "Collected")
        record.setdefault("evidence_confidence", "Unknown")
        record.setdefault("source_date", "")
        record.setdefault("date_collected", row["created_at"][:10])
        record.setdefault("file_name", "")
        record.setdefault("file_type", "")
        record.setdefault("file_size", 0)
        record.setdefault("storage_location", "")
        record.setdefault("storage_name", "")
        record.setdefault("sha256", "")
        record.setdefault("notes", "")
        record.update(
            {
                "internal_id": row["internal_id"],
                "opportunity_id": row["opportunity_id"],
                "state": row["classification"],
                "archived": bool(row["archived"]),
                "archived_at": row["archived_at"],
                "revision": row["revision"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
        return record

    @staticmethod
    def _knowledge_review_row(row: sqlite3.Row) -> dict[str, Any]:
        record = json.loads(row["record_json"])
        record.update(
            {
                "review_id": row["review_id"],
                "opportunity_id": row["opportunity_id"],
                "module_id": row["module_id"],
                "module_version": row["module_version"],
                "review_status": row["review_status"],
                "confidence": row["confidence"],
                "supersedes_review_id": row["supersedes_review_id"],
                "superseded_at": row["superseded_at"],
                "revision": row["revision"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
        return record

    @staticmethod
    def _assessment_row(
        row: sqlite3.Row,
        include_report: bool = True,
        include_snapshot: bool = False,
    ) -> dict[str, Any]:
        result = {
            "assessment_id": row["assessment_id"],
            "opportunity_id": row["opportunity_id"],
            "assessment_kind": row["assessment_kind"],
            "knowledge_review_id": row["knowledge_review_id"],
            "engine_version": row["engine_version"],
            "adapter_version": row["adapter_version"],
            "replay_hash": row["replay_hash"],
            "provenance": json.loads(row["provenance_json"]),
            "result": json.loads(row["result_json"]),
            "recommendation": row["recommendation"],
            "score": row["score"],
            "evidence_confidence": row["evidence_confidence"],
            "supersedes_assessment_id": row["supersedes_assessment_id"],
            "revision": row["revision"],
            "execution_timestamp": row["created_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        if include_report:
            result["report_markdown"] = row["report_markdown"]
        if include_snapshot:
            result["input_snapshot"] = json.loads(row["input_snapshot_json"])
        return result

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
        now = utcnow()
        try:
            with self.connect() as db:
                evidence_id = record.get("evidence_id") or self._next_evidence_id(db)
                clean = dict(record)
                clean["evidence_id"] = evidence_id
                clean.pop("opportunity_id", None)
                classification = clean["state"]
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
                    {
                        "event_type": "evidence.created",
                        "evidence_id": evidence_id,
                        "opportunity_id": opportunity_id,
                        "revision": 1,
                        "state": classification,
                        "evidence_status": clean.get("evidence_status", "Collected"),
                        "summary": "Evidence record created",
                    },
                )
        except sqlite3.IntegrityError as exc:
            raise ApiError(409, "evidence_exists", f"Evidence {evidence_id} already exists") from exc
        return self.get_evidence(evidence_id)

    @staticmethod
    def _next_evidence_id(db: sqlite3.Connection) -> str:
        rows = db.execute(
            "SELECT evidence_id FROM evidence WHERE evidence_id GLOB 'EV-[0-9]*'"
        ).fetchall()
        used = {
            int(row["evidence_id"][3:])
            for row in rows
            if row["evidence_id"][3:].isdigit()
        }
        number = 1
        while number in used:
            number += 1
        return f"EV-{number:06d}"

    def get_evidence(
        self,
        evidence_id: str,
        opportunity_id: str | None = None,
        include_archived: bool = True,
    ) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT rowid AS internal_id, * FROM evidence WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
        if (
            row is None
            or (opportunity_id is not None and row["opportunity_id"] != opportunity_id)
            or (row["archived"] and not include_archived)
        ):
            raise ApiError(404, "evidence_not_found", f"Evidence {evidence_id} was not found")
        return self._evidence_row(row)

    def list_evidence(
        self, opportunity_id: str | None = None, include_archived: bool = False
    ) -> list[dict[str, Any]]:
        query = "SELECT rowid AS internal_id, * FROM evidence"
        clauses: list[str] = []
        params: list[Any] = []
        if opportunity_id:
            clauses.append("opportunity_id = ?")
            params.append(opportunity_id)
        if not include_archived:
            clauses.append("archived = 0")
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at ASC"
        with self.connect() as db:
            rows = db.execute(query, tuple(params)).fetchall()
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
        if current["archived"]:
            raise ApiError(409, "evidence_archived", "Archived evidence cannot be updated")
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
                {
                    "event_type": action,
                    "evidence_id": evidence_id,
                    "opportunity_id": current["opportunity_id"],
                    "revision": current["revision"] + 1,
                    "previous_revision": current["revision"],
                    "from_state": current["state"],
                    "to_state": classification,
                    "changed_fields": sorted(
                        key
                        for key in set(clean) | set(current)
                        if key not in {
                            "internal_id",
                            "opportunity_id",
                            "archived",
                            "archived_at",
                            "revision",
                            "created_at",
                            "updated_at",
                        }
                        and clean.get(key) != current.get(key)
                    ),
                    "summary": "Evidence metadata updated",
                },
            )
        return self.get_evidence(evidence_id)

    def record_evidence_file_uploaded(
        self, evidence_id: str, actor: str
    ) -> None:
        evidence = self.get_evidence(evidence_id)
        with self.connect() as db:
            self._audit(
                db,
                actor,
                "evidence.file_uploaded",
                "evidence",
                evidence_id,
                {
                    "event_type": "evidence.file_uploaded",
                    "evidence_id": evidence_id,
                    "opportunity_id": evidence["opportunity_id"],
                    "revision": evidence["revision"],
                    "file_name": evidence.get("file_name", ""),
                    "file_size": evidence.get("file_size", 0),
                    "sha256": evidence.get("sha256", ""),
                    "summary": "Evidence file stored and hashed",
                },
            )

    def archive_evidence(
        self,
        opportunity_id: str,
        evidence_id: str,
        actor: str,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        current = self.get_evidence(evidence_id, opportunity_id=opportunity_id)
        if expected_revision is not None and current["revision"] != expected_revision:
            raise ApiError(
                409,
                "revision_conflict",
                "Evidence revision does not match If-Match",
                {"expected": expected_revision, "actual": current["revision"]},
            )
        if current["archived"]:
            return current
        clean = {
            key: value
            for key, value in current.items()
            if key
            not in {
                "internal_id",
                "opportunity_id",
                "archived",
                "archived_at",
                "revision",
                "created_at",
                "updated_at",
            }
        }
        clean["status_before_archive"] = clean.get("evidence_status", "Collected")
        clean["evidence_status"] = "Archived"
        now = utcnow()
        with self.connect() as db:
            db.execute(
                "UPDATE evidence SET record_json = ?, archived = 1, archived_at = ?, "
                "revision = revision + 1, updated_at = ? WHERE evidence_id = ?",
                (json.dumps(clean), now, now, evidence_id),
            )
            self._audit(
                db,
                actor,
                "evidence.archived",
                "evidence",
                evidence_id,
                {
                    "event_type": "evidence.archived",
                    "evidence_id": evidence_id,
                    "opportunity_id": opportunity_id,
                    "revision": current["revision"] + 1,
                    "previous_revision": current["revision"],
                    "summary": "Evidence record archived; stored file retained",
                },
            )
        return self.get_evidence(evidence_id, opportunity_id=opportunity_id)

    @staticmethod
    def _next_review_id(db: sqlite3.Connection) -> str:
        rows = db.execute(
            "SELECT review_id FROM knowledge_reviews WHERE review_id GLOB 'KR-[0-9]*'"
        ).fetchall()
        used = {
            int(row["review_id"][3:])
            for row in rows
            if row["review_id"][3:].isdigit()
        }
        number = 1
        while number in used:
            number += 1
        return f"KR-{number:06d}"

    def record_knowledge_module_loaded(
        self, module: dict[str, Any], actor: str = "anchorintel-module-loader"
    ) -> None:
        with self.connect() as db:
            self._audit(
                db,
                actor,
                "knowledge_module.loaded",
                "knowledge_module",
                module["module_id"],
                {
                    "event_type": "knowledge_module.loaded",
                    "module_id": module["module_id"],
                    "module_version": module["version"],
                    "module_integrity_hash": module["integrity_hash"],
                    "status": module["status"],
                    "summary": "Version-controlled Knowledge Module loaded and integrity checked",
                },
            )

    def create_knowledge_review(
        self,
        record: dict[str, Any],
        actor: str,
        supersedes_review_id: str | None = None,
    ) -> dict[str, Any]:
        opportunity_id = record["opportunity_id"]
        self.get_opportunity(opportunity_id)
        status = record["review_status"]
        if status not in {"Draft", "Ready", "Incomplete", "Completed"}:
            raise ApiError(400, "invalid_review_status", "Review cannot be created in that status")
        now = utcnow()
        with self.connect() as db:
            review_id = record.get("review_id") or self._next_review_id(db)
            prior: dict[str, Any] | None = None
            if supersedes_review_id:
                row = db.execute(
                    "SELECT * FROM knowledge_reviews WHERE review_id = ? AND opportunity_id = ?",
                    (supersedes_review_id, opportunity_id),
                ).fetchone()
                if row is None:
                    raise ApiError(
                        404,
                        "knowledge_review_not_found",
                        f"Knowledge review {supersedes_review_id} was not found",
                    )
                prior = self._knowledge_review_row(row)
                if prior["review_status"] in {"Superseded", "Archived"}:
                    raise ApiError(
                        409,
                        "knowledge_review_not_active",
                        "Only an active review may be superseded",
                    )

            clean = dict(record)
            clean.pop("review_id", None)
            clean.pop("opportunity_id", None)
            clean.pop("review_status", None)
            clean.pop("confidence", None)
            clean.pop("supersedes_review_id", None)
            clean["module_id"] = record["module_id"]
            clean["module_version"] = record["module_version"]
            try:
                db.execute(
                    "INSERT INTO knowledge_reviews(review_id, opportunity_id, module_id, "
                    "module_version, record_json, review_status, confidence, "
                    "supersedes_review_id, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        review_id,
                        opportunity_id,
                        record["module_id"],
                        record["module_version"],
                        json.dumps(clean),
                        status,
                        record["confidence"],
                        supersedes_review_id,
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ApiError(
                    409,
                    "knowledge_review_exists",
                    f"Knowledge review {review_id} already exists",
                ) from exc

            trace = clean.get("evidence_trace", [])
            details = {
                "opportunity_id": opportunity_id,
                "review_id": review_id,
                "module_id": record["module_id"],
                "module_version": record["module_version"],
                "module_integrity_hash": clean.get("module_integrity_hash", ""),
                "opportunity_revision": clean.get("opportunity_revision"),
                "evidence_trace": trace,
                "result_summary": {
                    "status": status,
                    "confidence": record["confidence"],
                    "finding_count": len(clean.get("output", {}).get("findings", [])),
                    "unknown_count": len(clean.get("output", {}).get("unknowns", [])),
                },
            }
            self._audit(
                db,
                actor,
                "knowledge_review.started",
                "knowledge_review",
                review_id,
                {**details, "event_type": "knowledge_review.started"},
            )
            if status == "Completed":
                self._audit(
                    db,
                    actor,
                    "knowledge_review.completed",
                    "knowledge_review",
                    review_id,
                    {**details, "event_type": "knowledge_review.completed"},
                )

            if prior is not None:
                prior_clean = {
                    key: value
                    for key, value in prior.items()
                    if key
                    not in {
                        "review_id",
                        "opportunity_id",
                        "review_status",
                        "confidence",
                        "supersedes_review_id",
                        "superseded_at",
                        "revision",
                        "created_at",
                        "updated_at",
                        "stale",
                        "stale_reasons",
                        "lifecycle_eligible",
                    }
                }
                db.execute(
                    "UPDATE knowledge_reviews SET record_json = ?, review_status = 'Superseded', "
                    "superseded_at = ?, revision = revision + 1, updated_at = ? "
                    "WHERE review_id = ?",
                    (json.dumps(prior_clean), now, now, supersedes_review_id),
                )
                prior_details = {
                    "event_type": "knowledge_review.superseded",
                    "opportunity_id": opportunity_id,
                    "review_id": supersedes_review_id,
                    "module_id": prior["module_id"],
                    "module_version": prior["module_version"],
                    "opportunity_revision": prior.get("opportunity_revision"),
                    "evidence_trace": prior.get("evidence_trace", []),
                    "result_summary": {"status": "Superseded", "successor_review_id": review_id},
                }
                self._audit(
                    db,
                    actor,
                    "knowledge_review.superseded",
                    "knowledge_review",
                    supersedes_review_id,
                    prior_details,
                )
                self._audit(
                    db,
                    actor,
                    "knowledge_review.rerun",
                    "knowledge_review",
                    review_id,
                    {
                        **details,
                        "event_type": "knowledge_review.rerun",
                        "supersedes_review_id": supersedes_review_id,
                    },
                )
        return self.get_knowledge_review(opportunity_id, review_id)

    def get_knowledge_review(
        self, opportunity_id: str, review_id: str
    ) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM knowledge_reviews WHERE review_id = ? AND opportunity_id = ?",
                (review_id, opportunity_id),
            ).fetchone()
        if row is None:
            raise ApiError(
                404,
                "knowledge_review_not_found",
                f"Knowledge review {review_id} was not found",
            )
        return self._knowledge_review_row(row)

    def list_knowledge_reviews(self, opportunity_id: str) -> list[dict[str, Any]]:
        self.get_opportunity(opportunity_id, include_archived=True)
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM knowledge_reviews WHERE opportunity_id = ? "
                "ORDER BY created_at DESC, review_id DESC",
                (opportunity_id,),
            ).fetchall()
        return [self._knowledge_review_row(row) for row in rows]

    def complete_knowledge_review(
        self,
        opportunity_id: str,
        review_id: str,
        actor: str,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        current = self.get_knowledge_review(opportunity_id, review_id)
        if current["review_status"] == "Completed":
            return current
        if current["review_status"] not in {"Draft", "Ready", "Incomplete"}:
            raise ApiError(409, "knowledge_review_not_active", "Review cannot be completed")
        if expected_revision is not None and current["revision"] != expected_revision:
            raise ApiError(
                409,
                "revision_conflict",
                "Knowledge review revision does not match If-Match",
                {"expected": expected_revision, "actual": current["revision"]},
            )
        clean = {
            key: value
            for key, value in current.items()
            if key
            not in {
                "review_id",
                "opportunity_id",
                "review_status",
                "confidence",
                "supersedes_review_id",
                "superseded_at",
                "revision",
                "created_at",
                "updated_at",
                "stale",
                "stale_reasons",
                "lifecycle_eligible",
            }
        }
        now = utcnow()
        with self.connect() as db:
            db.execute(
                "UPDATE knowledge_reviews SET record_json = ?, review_status = 'Completed', "
                "revision = revision + 1, updated_at = ? WHERE review_id = ?",
                (json.dumps(clean), now, review_id),
            )
            self._audit(
                db,
                actor,
                "knowledge_review.completed",
                "knowledge_review",
                review_id,
                {
                    "event_type": "knowledge_review.completed",
                    "opportunity_id": opportunity_id,
                    "review_id": review_id,
                    "module_id": current["module_id"],
                    "module_version": current["module_version"],
                    "opportunity_revision": current.get("opportunity_revision"),
                    "evidence_trace": current.get("evidence_trace", []),
                    "result_summary": {
                        "status": "Completed",
                        "confidence": current["confidence"],
                    },
                },
            )
        return self.get_knowledge_review(opportunity_id, review_id)

    def record_knowledge_review_failed(
        self, review: dict[str, Any], actor: str, error: ApiError
    ) -> None:
        with self.connect() as db:
            self._audit(
                db,
                actor,
                "knowledge_review.failed",
                "knowledge_review",
                review["review_id"],
                {
                    "event_type": "knowledge_review.failed",
                    "opportunity_id": review["opportunity_id"],
                    "review_id": review["review_id"],
                    "module_id": review["module_id"],
                    "module_version": review["module_version"],
                    "opportunity_revision": review.get("opportunity_revision"),
                    "evidence_trace": review.get("evidence_trace", []),
                    "result_summary": {
                        "status": "Incomplete",
                        "error_code": error.code,
                        "message": error.message,
                    },
                },
            )

    def record_knowledge_review_stale(
        self, review: dict[str, Any], reasons: list[str]
    ) -> None:
        with self.connect() as db:
            existing = db.execute(
                "SELECT 1 FROM audit_log WHERE action = 'knowledge_review.stale' "
                "AND entity_type = 'knowledge_review' AND entity_id = ? LIMIT 1",
                (review["review_id"],),
            ).fetchone()
            if existing is not None:
                return
            self._audit(
                db,
                "anchorintel-staleness-detector",
                "knowledge_review.stale",
                "knowledge_review",
                review["review_id"],
                {
                    "event_type": "knowledge_review.stale",
                    "opportunity_id": review["opportunity_id"],
                    "review_id": review["review_id"],
                    "module_id": review["module_id"],
                    "module_version": review["module_version"],
                    "opportunity_revision": review.get("opportunity_revision"),
                    "evidence_trace": review.get("evidence_trace", []),
                    "result_summary": {
                        "status": review.get("review_status"),
                        "stale": True,
                        "reasons": reasons,
                    },
                },
            )

    @staticmethod
    def _next_assessment_id(db: sqlite3.Connection) -> str:
        rows = db.execute(
            "SELECT assessment_id FROM assessments WHERE assessment_id GLOB 'AS-[0-9]*'"
        ).fetchall()
        used = {
            int(row["assessment_id"][3:])
            for row in rows
            if row["assessment_id"][3:].isdigit()
        }
        number = 1
        while number in used:
            number += 1
        return f"AS-{number:06d}"

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
        *,
        assessment_kind: str = "legacy",
        knowledge_review_id: str | None = None,
        engine_version: str = "",
        adapter_version: str = "",
        replay_hash: str = "",
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utcnow()
        current = self.get_opportunity(opportunity_id)
        from_state = current["lifecycle_state"]
        to_state = result["recommendation"]
        event_id = new_id("LEV")
        with self.connect() as db:
            assessment_id = self._next_assessment_id(db)
            db.execute(
                "INSERT INTO assessments(assessment_id, opportunity_id, input_snapshot_json, "
                "result_json, report_markdown, recommendation, score, evidence_confidence, "
                "supersedes_assessment_id, assessment_kind, knowledge_review_id, engine_version, "
                "adapter_version, replay_hash, provenance_json, revision, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    assessment_kind,
                    knowledge_review_id,
                    engine_version,
                    adapter_version,
                    replay_hash,
                    json.dumps(provenance or {}),
                    1,
                    now,
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
                {
                    "event_type": f"assessment.{event_type}",
                    "opportunity_id": opportunity_id,
                    "knowledge_review_id": knowledge_review_id,
                    "engine_version": engine_version,
                    "adapter_version": adapter_version,
                    "replay_hash": replay_hash,
                    "from_state": from_state,
                    "to_state": to_state,
                    "result_summary": {
                        "recommendation": to_state,
                        "score": result["score"],
                        "confidence": result["confidence"],
                    },
                },
            )
        return self.get_assessment(assessment_id, include_report=False)

    def get_assessment(
        self,
        assessment_id: str,
        include_report: bool = True,
        include_snapshot: bool = False,
    ) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM assessments WHERE assessment_id = ?", (assessment_id,)
            ).fetchone()
        if row is None:
            raise ApiError(404, "assessment_not_found", f"Assessment {assessment_id} was not found")
        return self._assessment_row(row, include_report, include_snapshot)

    def list_assessments(
        self, opportunity_id: str, assessment_kind: str | None = None
    ) -> list[dict[str, Any]]:
        self.get_opportunity(opportunity_id, include_archived=True)
        query = "SELECT * FROM assessments WHERE opportunity_id = ?"
        params: list[Any] = [opportunity_id]
        if assessment_kind:
            query += " AND assessment_kind = ?"
            params.append(assessment_kind)
        query += " ORDER BY created_at DESC, assessment_id DESC"
        with self.connect() as db:
            rows = db.execute(query, tuple(params)).fetchall()
        return [self._assessment_row(row, include_report=False) for row in rows]

    def assessment_successor_id(self, assessment_id: str) -> str | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT assessment_id FROM assessments "
                "WHERE supersedes_assessment_id = ? "
                "ORDER BY created_at DESC, assessment_id DESC LIMIT 1",
                (assessment_id,),
            ).fetchone()
        return str(row["assessment_id"]) if row else None

    def record_assessment_replayed(
        self, assessment: dict[str, Any], actor: str, replay: dict[str, Any]
    ) -> None:
        with self.connect() as db:
            self._audit(
                db,
                actor,
                "assessment.replayed",
                "assessment",
                assessment["assessment_id"],
                {
                    "event_type": "assessment.replayed",
                    "opportunity_id": assessment["opportunity_id"],
                    "knowledge_review_id": assessment.get("knowledge_review_id"),
                    "engine_version": assessment.get("engine_version"),
                    "adapter_version": assessment.get("adapter_version"),
                    "stored_replay_hash": assessment.get("replay_hash"),
                    "recomputed_replay_hash": replay.get("recomputed_replay_hash"),
                    "match": replay.get("match"),
                },
            )

    def record_assessment_stale(
        self, assessment: dict[str, Any], reasons: list[str]
    ) -> None:
        with self.connect() as db:
            existing = db.execute(
                "SELECT 1 FROM audit_log WHERE action = 'assessment.stale' "
                "AND entity_type = 'assessment' AND entity_id = ? LIMIT 1",
                (assessment["assessment_id"],),
            ).fetchone()
            if existing is not None:
                return
            self._audit(
                db,
                "anchorintel-staleness-detector",
                "assessment.stale",
                "assessment",
                assessment["assessment_id"],
                {
                    "event_type": "assessment.stale",
                    "opportunity_id": assessment["opportunity_id"],
                    "knowledge_review_id": assessment.get("knowledge_review_id"),
                    "replay_hash": assessment.get("replay_hash"),
                    "reasons": reasons,
                },
            )

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
