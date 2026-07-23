"""Hash-linked transition evidence."""
from dataclasses import dataclass
from typing import Any
from .hashing import canonical_hash, normalize

@dataclass(slots=True)
class PipelineTransition:
    transition_id: str
    sequence: int
    pipeline_id: str
    pipeline_run_id: str
    stage_id: str
    stage_name: str
    prior_state: str
    resulting_state: str
    outcome: str
    reason_code: str
    normalized_input_hash: str
    stage_output_hash: str
    previous_hash: str
    transition_hash: str
    output: Any

    @classmethod
    def create(cls, **kwargs):
        output = normalize(kwargs.pop("output"))
        content = {**kwargs, "output": output}
        transition_hash = canonical_hash(content)
        return cls(**kwargs, transition_hash=transition_hash, output=output)

    def content(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id, "sequence": self.sequence,
            "pipeline_id": self.pipeline_id, "pipeline_run_id": self.pipeline_run_id,
            "stage_id": self.stage_id, "stage_name": self.stage_name,
            "prior_state": self.prior_state, "resulting_state": self.resulting_state,
            "outcome": self.outcome, "reason_code": self.reason_code,
            "normalized_input_hash": self.normalized_input_hash,
            "stage_output_hash": self.stage_output_hash, "previous_hash": self.previous_hash,
            "output": self.output,
        }

    def verify_hash(self) -> bool:
        return self.transition_hash == canonical_hash(self.content())

    def to_dict(self) -> dict[str, Any]:
        return {**self.content(), "transition_hash": self.transition_hash}
