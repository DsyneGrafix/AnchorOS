from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApiError(Exception):
    status: int
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message

