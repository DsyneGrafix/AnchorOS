"""Shared lifecycle rules for AOS-140 managed entities."""

from __future__ import annotations

from core.infrastructure_registry.exceptions import InvalidLifecycleTransitionError

PLANNED = "PLANNED"
ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"
RETIRED = "RETIRED"
ARCHIVED = "ARCHIVED"

LIFECYCLE_STATES = frozenset({PLANNED, ACTIVE, INACTIVE, RETIRED, ARCHIVED})

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    PLANNED: frozenset({ACTIVE, ARCHIVED}),
    ACTIVE: frozenset({INACTIVE, RETIRED}),
    INACTIVE: frozenset({ACTIVE, RETIRED}),
    RETIRED: frozenset({ARCHIVED}),
    ARCHIVED: frozenset(),
}


def normalize_state(value: str) -> str:
    state = value.strip().upper()
    if state not in LIFECYCLE_STATES:
        raise InvalidLifecycleTransitionError(f"Unknown lifecycle state: {value}")
    return state


def validate_transition(current: str, target: str) -> str:
    current_state = normalize_state(current)
    target_state = normalize_state(target)
    if current_state == target_state:
        return target_state
    if target_state not in ALLOWED_TRANSITIONS[current_state]:
        raise InvalidLifecycleTransitionError(
            f"Invalid lifecycle transition: {current_state} -> {target_state}"
        )
    return target_state
