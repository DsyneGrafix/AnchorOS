"""SQLite schema management for the AOS-140 Infrastructure Registry."""

from __future__ import annotations

import sqlite3
from pathlib import Path


EXPECTED_TABLES = {
    "registry_metadata",
    "organizations",
    "facilities",
    "asset_types",
    "assets",
    "relationships",
}


class RegistryDatabase:
    """Owns database connection creation and deterministic schema setup."""

    def __init__(self, database_path: Path, schema_version: str) -> None:
        self.database_path = Path(database_path)
        self.schema_version = schema_version

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize_schema(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS registry_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    external_id TEXT UNIQUE,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS facilities (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    location TEXT,
                    external_id TEXT UNIQUE,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (organization_id) REFERENCES organizations(id)
                        ON UPDATE RESTRICT ON DELETE RESTRICT
                );

                CREATE TABLE IF NOT EXISTS asset_types (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    asset_type_id TEXT NOT NULL,
                    facility_id TEXT,
                    name TEXT NOT NULL,
                    external_id TEXT UNIQUE,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (asset_type_id) REFERENCES asset_types(id)
                        ON UPDATE RESTRICT ON DELETE RESTRICT,
                    FOREIGN KEY (facility_id) REFERENCES facilities(id)
                        ON UPDATE RESTRICT ON DELETE RESTRICT
                );

                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    CHECK (source_id <> target_id)
                );

                CREATE INDEX IF NOT EXISTS idx_facilities_organization
                    ON facilities(organization_id);
                CREATE INDEX IF NOT EXISTS idx_assets_facility
                    ON assets(facility_id);
                CREATE INDEX IF NOT EXISTS idx_assets_type
                    ON assets(asset_type_id);
                CREATE INDEX IF NOT EXISTS idx_relationships_source
                    ON relationships(source_id);
                CREATE INDEX IF NOT EXISTS idx_relationships_target
                    ON relationships(target_id);
                """
            )
            connection.execute(
                """
                INSERT INTO registry_metadata(key, value)
                VALUES ('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (self.schema_version,),
            )

    def verify_schema(self) -> bool:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            tables = {row["name"] for row in rows}
            version_row = connection.execute(
                "SELECT value FROM registry_metadata WHERE key = 'schema_version'"
            ).fetchone()

        return EXPECTED_TABLES.issubset(tables) and (
            version_row is not None and version_row["value"] == self.schema_version
        )
