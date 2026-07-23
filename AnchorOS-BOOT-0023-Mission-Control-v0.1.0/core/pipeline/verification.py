"""Independent stored evidence-chain verification."""
from .hashing import canonical_hash

class PipelineChainVerifier:
    def verify(self, result) -> bool:
        previous = ""
        if not result.transitions:
            return False
        for sequence, transition in enumerate(result.transitions, 1):
            if transition.sequence != sequence or transition.previous_hash != previous:
                return False
            expected_id = f"{result.pipeline_run_id}:{sequence:04d}"
            if transition.transition_id != expected_id:
                return False
            if transition.pipeline_id != result.pipeline_id or transition.pipeline_run_id != result.pipeline_run_id:
                return False
            if transition.stage_output_hash != canonical_hash(transition.output):
                return False
            if not transition.verify_hash():
                return False
            previous = transition.transition_hash
        return previous == result.final_evidence_hash and result.terminal_state == result.transitions[-1].resulting_state
