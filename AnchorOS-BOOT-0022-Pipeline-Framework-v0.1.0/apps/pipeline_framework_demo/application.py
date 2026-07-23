from copy import deepcopy
from core.pipeline import PipelineChainVerifier, PipelineDefinition, PipelineReplayVerifier, PipelineRunner, PipelineStage


def build(fail=False):
    def prepare(c): return {"prepared": True}
    def validate(c):
        if fail: raise RuntimeError("Forced validation failure")
        return {"validated": True}
    def complete(c): return {"completed": True}
    return PipelineDefinition("DEMO", "Pipeline Framework Demo", "0.1.0", (
        PipelineStage("DEMO-001","Prepare",1,"Prepared",prepare),
        PipelineStage("DEMO-002","Validate",2,"Validated",validate),
        PipelineStage("DEMO-003","Complete",3,"Operational",complete),
    ), "Pending", "Operational", "Failed")


def main():
    runner=PipelineRunner(); verifier=PipelineChainVerifier()
    result=runner.run(build(), {"example":"BOOT-0022"}, pipeline_run_id="DEMO:SUCCESS")
    print("Pipeline Framework Demo")
    for t in result.transitions: print(f"{t.sequence}. {t.stage_id} {t.outcome} {t.prior_state} -> {t.resulting_state} {t.transition_hash[:12]}")
    print(f"Evidence Chain: {'PASS' if verifier.verify(result) else 'FAIL'}")
    replay=PipelineReplayVerifier().replay(build(),result)
    print(f"Replay: {'PASS' if replay.verified else 'FAIL'}")
    tampered=deepcopy(result); tampered.transitions[0].output["prepared"]=False
    print(f"Tamper Detection: {'PASS' if not verifier.verify(tampered) else 'FAIL'}")
    failed=runner.run(build(fail=True), {"example":"failure"}, pipeline_run_id="DEMO:FAILURE")
    print(f"Forced Failure: {'PASS' if not failed.success and len(failed.transitions)==2 else 'FAIL'}")
    print(f"Later Stages Halted: {'PASS' if all(t.stage_id != 'DEMO-003' for t in failed.transitions) else 'FAIL'}")

if __name__ == "__main__": main()
