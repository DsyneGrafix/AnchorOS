"""Lifecycle enforcement for Customer Onboarding Pipeline v1."""

from .models import (
    CustomerRecord,
    CustomerState,
    TransitionRecord,
    canonical_hash,
)
from .stages import CUSTOMER_PIPELINE_STAGES, StageDefinition


class CustomerLifecycleManager:
    """Apply and verify fail-closed customer lifecycle transitions."""

    def advance(
        self,
        record: CustomerRecord,
        stage: StageDefinition,
        *,
        input_hash: str,
        details: dict[str, object],
    ) -> TransitionRecord:
        if record.state is not stage.entry_state:
            raise RuntimeError(
                f"{stage.code} cannot execute from "
                f"{record.state.value}; expected "
                f"{stage.entry_state.value}."
            )

        transition = TransitionRecord.create(
            sequence=len(record.transitions) + 1,
            stage_code=stage.code,
            stage_name=stage.name,
            from_state=record.state,
            to_state=stage.exit_state,
            outcome="PASS",
            input_hash=input_hash,
            previous_hash=record.final_hash,
            details=details,
        )
        record.transitions.append(transition)
        record.state = stage.exit_state
        record.last_successful_state = stage.exit_state
        return transition

    def fail(
        self,
        record: CustomerRecord,
        stage: StageDefinition,
        *,
        input_hash: str,
        reason: str,
    ) -> TransitionRecord:
        previous_state = record.state
        details = {
            "reason": reason,
            "last_successful_state": (
                record.last_successful_state.value
            ),
        }
        transition = TransitionRecord.create(
            sequence=len(record.transitions) + 1,
            stage_code=stage.code,
            stage_name=stage.name,
            from_state=previous_state,
            to_state=CustomerState.FAILED,
            outcome="FAIL",
            input_hash=input_hash,
            previous_hash=record.final_hash,
            details=details,
        )
        record.transitions.append(transition)
        record.state = CustomerState.FAILED
        record.failed_stage = stage.code
        record.failure_reason = reason
        return transition

    def verify(self, record: CustomerRecord) -> bool:
        """Verify sequence, hash linkage, and terminal aggregate state."""

        expected_state = CustomerState.PENDING.value
        last_successful_state = CustomerState.PENDING.value
        previous_hash = ""
        reconstructed_artifacts: dict[
            str,
            dict[str, object],
        ] = {}

        for expected_sequence, transition in enumerate(
            record.transitions,
            start=1,
        ):
            if expected_sequence > len(CUSTOMER_PIPELINE_STAGES):
                return False
            stage = CUSTOMER_PIPELINE_STAGES[
                expected_sequence - 1
            ]
            if transition.sequence != expected_sequence:
                return False
            if transition.stage_code != stage.code:
                return False
            if transition.stage_name != stage.name:
                return False
            if transition.from_state != expected_state:
                return False
            if transition.previous_hash != previous_hash:
                return False
            expected_input_hash = canonical_hash(
                {
                    "request": record.request.to_dict(),
                    "state": expected_state,
                    "last_successful_state": (
                        last_successful_state
                    ),
                    "artifacts": reconstructed_artifacts,
                }
            )
            if transition.input_hash != expected_input_hash:
                return False
            if not transition.verify_hash():
                return False

            previous_hash = transition.transition_hash
            expected_state = transition.to_state

            if transition.outcome == "FAIL":
                if transition.to_state != CustomerState.FAILED.value:
                    return False
                if expected_sequence != len(record.transitions):
                    return False
                if stage.code in record.artifacts:
                    return False
                if transition.details.get(
                    "last_successful_state"
                ) != last_successful_state:
                    return False
            elif transition.outcome == "PASS":
                if transition.to_state != stage.exit_state.value:
                    return False
                if record.artifacts.get(stage.code) != (
                    transition.details
                ):
                    return False
                reconstructed_artifacts[stage.code] = (
                    transition.details
                )
                last_successful_state = transition.to_state
            else:
                return False

        return (
            record.state.value == expected_state
            and record.last_successful_state.value
            == last_successful_state
            and record.artifacts == reconstructed_artifacts
        )
