import copy
import unittest

from core.boot_pipeline import BootPipeline
from core.pipeline import (
    DuplicateStageIdentifier,
    InvalidStageOrder,
    PipelineChainVerifier,
    PipelineDefinition,
    PipelineLifecycleHooks,
    PipelineReplayVerifier,
    PipelineRunner,
    PipelineStage,
    StageOutcome,
)


def stage(stage_id, position, state, handler=None, entry=None, complete=None):
    return PipelineStage(stage_id, stage_id, position, state, handler or (lambda c: {"stage": stage_id}), entry, complete)


def definition(stages=None, version="1.0"):
    return PipelineDefinition("TEST", "Test Pipeline", version, tuple(stages or [stage("S1", 1, "Done")]), "Pending", "Done", "Failed")


class Hooks(PipelineLifecycleHooks):
    def __init__(self): self.calls=[]
    def before_pipeline(self,c): self.calls.append("before_pipeline")
    def before_stage(self,c,s): self.calls.append(f"before:{s.stage_id}")
    def after_stage(self,c,s,t): self.calls.append(f"after:{s.stage_id}")
    def on_failure(self,c,s,t): self.calls.append(f"failure:{s.stage_id}")
    def on_halt(self,c,r): self.calls.append("halt")
    def after_pipeline(self,c,r): self.calls.append("after_pipeline")


class Sink:
    def __init__(self): self.records=[]
    def record_pipeline_transition(self, transition): self.records.append(transition)


class Publisher:
    def __init__(self): self.events=[]
    def publish_pipeline_event(self, event_type, payload): self.events.append((event_type,payload))


class PipelineFrameworkTests(unittest.TestCase):
    def test_valid_definition(self):
        self.assertEqual(definition().pipeline_id, "TEST")

    def test_duplicate_stage_ids_rejected(self):
        with self.assertRaises(DuplicateStageIdentifier):
            definition([stage("S",1,"A"), stage("S",2,"Done")])

    def test_invalid_stage_order_rejected(self):
        with self.assertRaises(InvalidStageOrder):
            definition([stage("S1",2,"Done")])

    def test_stages_execute_in_order(self):
        seen=[]
        stages=[stage("S1",1,"A",lambda c: seen.append("S1") or {}), stage("S2",2,"Done",lambda c: seen.append("S2") or {})]
        result=PipelineRunner().run(definition(stages), {"x":1}, pipeline_run_id="run")
        self.assertEqual(seen,["S1","S2"]); self.assertTrue(result.success)

    def test_failure_halts_later_stages(self):
        seen=[]
        def fail(c): seen.append("S1"); raise RuntimeError("forced")
        stages=[stage("S1",1,"A",fail), stage("S2",2,"Done",lambda c: seen.append("S2") or {})]
        result=PipelineRunner().run(definition(stages), {}, pipeline_run_id="run")
        self.assertEqual(seen,["S1"]); self.assertFalse(result.success); self.assertEqual(result.terminal_state,"Failed")

    def test_entry_validation_fails_closed(self):
        result=PipelineRunner().run(definition([stage("S1",1,"Done",entry=lambda c: False)]), {}, pipeline_run_id="run")
        self.assertFalse(result.success); self.assertEqual(result.transitions[0].reason_code,"PipelineEntryRejected")

    def test_completion_validation_fails_closed(self):
        result=PipelineRunner().run(definition([stage("S1",1,"Done",complete=lambda c: False)]), {}, pipeline_run_id="run")
        self.assertFalse(result.success); self.assertEqual(result.transitions[0].reason_code,"StageValidationFailed")

    def test_outputs_are_deterministic(self):
        d=definition([stage("S1",1,"Done",lambda c: {"b":2,"a":1})])
        a=PipelineRunner().run(d,{"z":3,"a":1},pipeline_run_id="run")
        b=PipelineRunner().run(d,{"a":1,"z":3},pipeline_run_id="run")
        self.assertEqual(a.final_evidence_hash,b.final_evidence_hash)

    def test_chain_verifies(self):
        result=PipelineRunner().run(definition(),{},pipeline_run_id="run")
        self.assertTrue(PipelineChainVerifier().verify(result))

    def test_transition_modification_detected(self):
        result=PipelineRunner().run(definition(),{},pipeline_run_id="run"); bad=copy.deepcopy(result)
        bad.transitions[0].output["stage"]="changed"
        self.assertFalse(PipelineChainVerifier().verify(bad))

    def test_transition_removal_detected(self):
        d=definition([stage("S1",1,"A"),stage("S2",2,"Done")]); bad=PipelineRunner().run(d,{},pipeline_run_id="run")
        bad.transitions.pop(0)
        self.assertFalse(PipelineChainVerifier().verify(bad))

    def test_transition_insertion_detected(self):
        result=PipelineRunner().run(definition(),{},pipeline_run_id="run"); bad=copy.deepcopy(result)
        bad.transitions.append(copy.deepcopy(bad.transitions[0]))
        self.assertFalse(PipelineChainVerifier().verify(bad))

    def test_transition_reorder_detected(self):
        d=definition([stage("S1",1,"A"),stage("S2",2,"Done")]); bad=PipelineRunner().run(d,{},pipeline_run_id="run")
        bad.transitions.reverse()
        self.assertFalse(PipelineChainVerifier().verify(bad))

    def test_final_hash_tamper_detected(self):
        result=PipelineRunner().run(definition(),{},pipeline_run_id="run")
        result.transitions[-1].transition_hash="0"*64
        self.assertFalse(PipelineChainVerifier().verify(result))

    def test_replay_succeeds(self):
        d=definition(); result=PipelineRunner().run(d,{"x":1},pipeline_run_id="run")
        self.assertTrue(PipelineReplayVerifier().replay(d,result).verified)

    def test_replay_fails_for_altered_input(self):
        d=definition(); result=PipelineRunner().run(d,{"x":1},pipeline_run_id="run")
        result.normalized_input={"x":2}
        self.assertFalse(PipelineReplayVerifier().replay(d,result).verified)

    def test_replay_fails_for_altered_output(self):
        d=definition(); result=PipelineRunner().run(d,{},pipeline_run_id="run")
        result.transitions[0].output["stage"]="bad"
        self.assertFalse(PipelineReplayVerifier().replay(d,result).verified)

    def test_replay_fails_for_version_change(self):
        d=definition(); result=PipelineRunner().run(d,{},pipeline_run_id="run")
        self.assertFalse(PipelineReplayVerifier().replay(definition(version="2.0"),result).verified)

    def test_hooks_order(self):
        hooks=Hooks(); PipelineRunner(hooks=hooks).run(definition(),{},pipeline_run_id="run")
        self.assertEqual(hooks.calls,["before_pipeline","before:S1","after:S1","after_pipeline"])

    def test_hook_failure_fails_closed(self):
        class Bad(Hooks):
            def before_stage(self,c,s): raise RuntimeError("hook")
        result=PipelineRunner(hooks=Bad()).run(definition(),{},pipeline_run_id="run")
        self.assertFalse(result.success)

    def test_adapters_receive_records(self):
        sink=Sink(); pub=Publisher(); PipelineRunner(audit_sink=sink,event_publisher=pub).run(definition(),{},pipeline_run_id="run")
        self.assertEqual(len(sink.records),1); self.assertEqual(len(pub.events),1)

    def test_framework_runs_without_adapters(self):
        self.assertTrue(PipelineRunner().run(definition(),{},pipeline_run_id="run").success)

    def test_boot_pipeline_uses_framework_and_passes(self):
        boot=BootPipeline(); boot.execute()
        self.assertEqual(len(boot.results),8); self.assertTrue(boot.summary()); self.assertTrue(boot.verify_evidence()); self.assertTrue(boot.replay().verified)


if __name__ == "__main__": unittest.main()
