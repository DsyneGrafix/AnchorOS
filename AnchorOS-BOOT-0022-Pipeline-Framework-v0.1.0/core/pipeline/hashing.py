"""Canonical normalization and integrity hashing for pipeline evidence."""
from dataclasses import asdict, is_dataclass
from enum import Enum
import hashlib
import json
from typing import Any


def normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return normalize(value.value)
    if is_dataclass(value):
        return normalize(asdict(value))
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in sorted(value.items(), key=lambda i: str(i[0]))}
    if isinstance(value, (list, tuple)):
        return [normalize(v) for v in value]
    if isinstance(value, (set, frozenset)):
        normalized = [normalize(v) for v in value]
        return sorted(normalized, key=lambda v: json.dumps(v, sort_keys=True, separators=(",", ":")))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return normalize(value.to_dict())
    raise TypeError(f"Unsupported value for canonical serialization: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
