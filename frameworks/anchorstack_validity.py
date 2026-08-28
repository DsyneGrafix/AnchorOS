"""Deterministic continuation-validity logic owned by AnchorStack.

This module determines whether execution remains admissible. It never chooses, routes,
or executes a response action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping


class Validity(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class DeterminationState(str, Enum):
    CONTINUATION_VALID = "CONTINUATION_VALID"
    PROTECTIVE_HOLD = "PROTECTIVE_HOLD"
    REASSESSMENT_REQUIRED = "REASSESSMENT_REQUIRED"
    AUTHORITY_SUSPENDED = "AUTHORITY_SUSPENDED"
    DETERMINATION_NOT_ESTABLISHED = "DETERMINATION_NOT_ESTABLISHED"


MATERIAL_DIMENSIONS = (
    "authority",
    "assumptions",
    "dependencies",
    "evidence",
    "constraints",
    "conditions",
    "scope",
    "communications",
)


@dataclass(frozen=True, slots=True)
class ContinuationSnapshot:
    execution_id: str
    observed_at: str
    dimensions: Mapping[str, Validity]
    safe_exit_available: bool
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.execution_id.strip():
            raise ValueError("execution_id is required")

        missing = [name for name in MATERIAL_DIMENSIONS if name not in self.dimensions]
        extra = [name for name in self.dimensions if name not in MATERIAL_DIMENSIONS]

        if missing or extra:
            raise ValueError(
                "dimension contract mismatch; "
                f"missing={missing}, extra={extra}"
            )

        for name, value in self.dimensions.items():
            if not isinstance(value, Validity):
                raise TypeError(f"{name} must be a Validity value")


@dataclass(frozen=True, slots=True)
class ContinuationDetermination:
    determination_id: str
    execution_id: str
    observed_at: str
    state: DeterminationState
    reason_codes: tuple[str, ...]
    invalid_dimensions: tuple[str, ...]
    stale_dimensions: tuple[str, ...]
    unknown_dimensions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    action_selected: bool = False

    @property
    def continuation_valid(self) -> bool:
        return self.state is DeterminationState.CONTINUATION_VALID

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "determination_id": self.determination_id,
            "execution_id": self.execution_id,
            "observed_at": self.observed_at,
            "state": self.state.value,
            "continuation_valid": self.continuation_valid,
            "reason_codes": list(self.reason_codes),
            "invalid_dimensions": list(self.invalid_dimensions),
            "stale_dimensions": list(self.stale_dimensions),
            "unknown_dimensions": list(self.unknown_dimensions),
            "evidence_ids": list(self.evidence_ids),
            "action_selected": self.action_selected,
        }


class ContinuationEvaluator:
    """Apply a fixed precedence order to a complete material-state snapshot."""

    def evaluate(self, snapshot: ContinuationSnapshot) -> ContinuationDetermination:
        invalid = tuple(
            name for name in MATERIAL_DIMENSIONS
            if snapshot.dimensions[name] is Validity.INVALID
        )
        stale = tuple(
            name for name in MATERIAL_DIMENSIONS
            if snapshot.dimensions[name] is Validity.STALE
        )
        unknown = tuple(
            name for name in MATERIAL_DIMENSIONS
            if snapshot.dimensions[name] is Validity.UNKNOWN
        )

        if snapshot.dimensions["authority"] is Validity.INVALID:
            state = DeterminationState.AUTHORITY_SUSPENDED
            reasons = ("AS-CV-AUTHORITY-INVALID",)
        elif not snapshot.safe_exit_available and (invalid or stale or unknown):
            state = DeterminationState.PROTECTIVE_HOLD
            reasons = (
                "AS-CV-SAFE-EXIT-UNAVAILABLE",
            ) + self._dimension_reasons(invalid, stale, unknown)
        elif any(name in invalid for name in ("constraints", "scope", "communications")):
            state = DeterminationState.PROTECTIVE_HOLD
            reasons = self._dimension_reasons(invalid, stale, unknown)
        elif invalid or stale:
            state = DeterminationState.REASSESSMENT_REQUIRED
            reasons = self._dimension_reasons(invalid, stale, unknown)
        elif unknown:
            state = DeterminationState.DETERMINATION_NOT_ESTABLISHED
            reasons = self._dimension_reasons(invalid, stale, unknown)
        else:
            state = DeterminationState.CONTINUATION_VALID
            reasons = ("AS-CV-ALL-MATERIAL-DIMENSIONS-VALID",)

        evidence_ids = tuple(sorted(set(snapshot.evidence_ids)))
        determination_id = self._determination_id(
            snapshot=snapshot,
            state=state,
            reasons=reasons,
            evidence_ids=evidence_ids,
        )

        return ContinuationDetermination(
            determination_id=determination_id,
            execution_id=snapshot.execution_id,
            observed_at=snapshot.observed_at,
            state=state,
            reason_codes=reasons,
            invalid_dimensions=invalid,
            stale_dimensions=stale,
            unknown_dimensions=unknown,
            evidence_ids=evidence_ids,
        )

    @staticmethod
    def _dimension_reasons(
        invalid: tuple[str, ...],
        stale: tuple[str, ...],
        unknown: tuple[str, ...],
    ) -> tuple[str, ...]:
        return tuple(
            [f"AS-CV-{name.upper()}-INVALID" for name in invalid]
            + [f"AS-CV-{name.upper()}-STALE" for name in stale]
            + [f"AS-CV-{name.upper()}-UNKNOWN" for name in unknown]
        )

    @staticmethod
    def _determination_id(
        *,
        snapshot: ContinuationSnapshot,
        state: DeterminationState,
        reasons: tuple[str, ...],
        evidence_ids: tuple[str, ...],
    ) -> str:
        material = {
            "execution_id": snapshot.execution_id,
            "observed_at": snapshot.observed_at,
            "dimensions": {
                name: snapshot.dimensions[name].value
                for name in MATERIAL_DIMENSIONS
            },
            "safe_exit_available": snapshot.safe_exit_available,
            "evidence_ids": list(evidence_ids),
            "state": state.value,
            "reason_codes": list(reasons),
        }
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return "AS-CV-" + sha256(canonical.encode("utf-8")).hexdigest()[:24]
