"""Optional bounded lifecycle hooks."""
class PipelineLifecycleHooks:
    def before_pipeline(self, context): pass
    def after_pipeline(self, context, result): pass
    def before_stage(self, context, stage): pass
    def after_stage(self, context, stage, transition): pass
    def on_failure(self, context, stage, transition): pass
    def on_halt(self, context, result): pass
