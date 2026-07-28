"""Persistence-only repository for AOS-140 registry entities."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import fields
from typing import Any, TypeVar

from core.infrastructure_registry.database import RegistryDatabase
from core.infrastructure_registry.models import (
    Asset,
    AssetType,
    Facility,
    Organization,
    RegistryEntity,
    Relationship,
    utc_now,
)

EntityT = TypeVar("EntityT", bound=RegistryEntity)


class EntityNotFoundError(LookupError):
    pass


class InfrastructureRegistryRepository:
    """CRUD persistence without domain/business-policy decisions."""

    _TABLES: dict[type[RegistryEntity], str] = {
        Organization: "organizations",
        Facility: "facilities",
        AssetType: "asset_types",
        Asset: "assets",
        Relationship: "relationships",
    }

    def __init__(self, database: RegistryDatabase) -> None:
        self.database = database

    def create(self, entity: EntityT) -> EntityT:
        table = self._table_for(type(entity))
        record = self._serialize(entity)
        columns = list(record)
        placeholders = ", ".join("?" for _ in columns)
        sql = (
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"VALUES ({placeholders})"
        )
        with self.database.connect() as connection:
            connection.execute(sql, tuple(record[column] for column in columns))
        return entity

    def get(self, entity_type: type[EntityT], entity_id: str) -> EntityT | None:
        table = self._table_for(entity_type)
        with self.database.connect() as connection:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE id = ?", (entity_id,)
            ).fetchone()
        return self._deserialize(entity_type, row) if row else None

    def require(self, entity_type: type[EntityT], entity_id: str) -> EntityT:
        entity = self.get(entity_type, entity_id)
        if entity is None:
            raise EntityNotFoundError(
                f"{entity_type.__name__} not found: {entity_id}"
            )
        return entity

    def list(self, entity_type: type[EntityT]) -> list[EntityT]:
        table = self._table_for(entity_type)
        with self.database.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM {table} ORDER BY created_at, id"
            ).fetchall()
        return [self._deserialize(entity_type, row) for row in rows]

    def list_facilities_by_organization(
        self, organization_id: str
    ) -> list[Facility]:
        """Return persisted facilities belonging to one organization."""
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM facilities
                WHERE organization_id = ?
                ORDER BY created_at, id
                """,
                (organization_id,),
            ).fetchall()
        return [self._deserialize(Facility, row) for row in rows]

    def update(self, entity: EntityT) -> EntityT:
        table = self._table_for(type(entity))
        current = self.require(type(entity), entity.id)
        entity.version = current.version + 1
        entity.created_at = current.created_at
        entity.updated_at = utc_now()
        record = self._serialize(entity)
        assignments = ", ".join(
            f"{column} = ?" for column in record if column != "id"
        )
        values = [record[column] for column in record if column != "id"]
        values.append(entity.id)
        with self.database.connect() as connection:
            cursor = connection.execute(
                f"UPDATE {table} SET {assignments} WHERE id = ?", values
            )
            if cursor.rowcount != 1:
                raise EntityNotFoundError(
                    f"{type(entity).__name__} not found: {entity.id}"
                )
        return entity

    def delete(self, entity_type: type[EntityT], entity_id: str) -> None:
        table = self._table_for(entity_type)
        with self.database.connect() as connection:
            cursor = connection.execute(
                f"DELETE FROM {table} WHERE id = ?", (entity_id,)
            )
            if cursor.rowcount != 1:
                raise EntityNotFoundError(
                    f"{entity_type.__name__} not found: {entity_id}"
                )

    def count(self, entity_type: type[EntityT]) -> int:
        table = self._table_for(entity_type)
        with self.database.connect() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS total FROM {table}"
            ).fetchone()
        return int(row["total"])

    @classmethod
    def _table_for(cls, entity_type: type[RegistryEntity]) -> str:
        try:
            return cls._TABLES[entity_type]
        except KeyError as error:
            raise TypeError(
                f"Unsupported registry entity type: {entity_type.__name__}"
            ) from error

    @staticmethod
    def _serialize(entity: RegistryEntity) -> dict[str, Any]:
        record = entity.to_record()
        record["metadata"] = json.dumps(record["metadata"], sort_keys=True)
        return record

    @staticmethod
    def _deserialize(entity_type: type[EntityT], row: sqlite3.Row) -> EntityT:
        accepted = {model_field.name for model_field in fields(entity_type)}
        values = {key: row[key] for key in row.keys() if key in accepted}
        values["metadata"] = json.loads(values.get("metadata") or "{}")
        return entity_type(**values)
