"""Reusable validation helpers for Infrastructure Registry services."""

from __future__ import annotations

from core.infrastructure_registry.exceptions import RegistryValidationError


def require_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise RegistryValidationError(f"{field_name} is required.")
    return normalized


def normalize_optional_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
