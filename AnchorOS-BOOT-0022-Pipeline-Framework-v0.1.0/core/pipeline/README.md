# AnchorOS Pipeline Framework v0.1

The Pipeline Framework standardizes deterministic pipeline execution. It does not replace domain pipelines or Platform Services.

It owns immutable definitions, ordered stages, bounded contexts, fail-closed execution, hash-linked transitions, independent chain verification, deterministic replay, optional lifecycle hooks, and narrow integration ports. Domain pipelines continue to own their input, state meanings, handlers, validation, and operational outcome.

Version 0.1 is intentionally limited to ordered, single-process, in-memory execution. It is not BPMN, a DAG engine, a scheduler, a task queue, or a distributed workflow system.
