"""Deterministic replay verification."""
from .result import PipelineReplayResult
from .verification import PipelineChainVerifier

class PipelineReplayVerifier:
    def __init__(self, runner=None): self.runner = runner or __import__('core.pipeline.runner', fromlist=['PipelineRunner']).PipelineRunner()
    def replay(self, definition, expected, *, domain_context=None):
        actual = self.runner.run(definition, expected.normalized_input, pipeline_run_id=expected.pipeline_run_id, domain_context=domain_context)
        chain_ok = PipelineChainVerifier().verify(expected) and PipelineChainVerifier().verify(actual)
        verified = chain_ok and expected.pipeline_id == actual.pipeline_id and expected.pipeline_version == actual.pipeline_version and expected.normalized_input == actual.normalized_input and expected.terminal_state == actual.terminal_state and expected.final_evidence_hash == actual.final_evidence_hash and len(expected.transitions) == len(actual.transitions)
        return PipelineReplayResult(verified, expected.pipeline_id, expected.pipeline_run_id, expected.final_evidence_hash, actual.final_evidence_hash, len(expected.transitions), len(actual.transitions), "REPLAY_VERIFIED" if verified else "REPLAY_MISMATCH", "Deterministic replay matched stored evidence." if verified else "Deterministic replay did not match stored evidence.")
