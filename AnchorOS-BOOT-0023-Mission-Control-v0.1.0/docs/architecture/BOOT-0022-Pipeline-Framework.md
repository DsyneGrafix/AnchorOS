# BOOT-0022 — Pipeline Framework Architecture

## Purpose
Extract the smallest domain-neutral execution machinery shared by Boot and Customer Onboarding.

## Position
Applications → Domain Pipelines → Pipeline Framework → Platform Services → Kernel Infrastructure.

## Execution lifecycle
Validate definition; normalize input; validate stage entry; invoke one handler; validate completion; record a hash-linked transition; stop immediately on failure; return a structured result.

## Transition model
Each stage attempt records identity, sequence, states, outcome, reason, input/output hashes, previous hash, and transition hash. Hashes detect integrity changes; they are not signatures or nonrepudiation.

## Chain verification versus replay
Chain verification tests whether stored evidence remains internally intact without invoking handlers. Replay invokes handlers again and determines whether execution reproduces the stored result.

## Extension
Create immutable `PipelineStage` objects, assemble a `PipelineDefinition`, and execute it with `PipelineRunner`. Optional hooks and adapters are supplied by composition roots.

## Migrations
`core.boot_pipeline.BootPipeline` remains the public import and preserves eight names, order, output, and PASS/FAIL behavior while using the common runner. Customer Onboarding preserves CP-001–CP-009 and its existing domain evidence while delegating ordered fail-closed iteration to the common runner adapter.

## Limitations
No database, parallel execution, DAGs, distributed orchestration, workers, compensation, rollback, human approval queue, or graphical builder.

## Future considerations
Persistent repositories, metrics adapters, additional lifecycle pipelines, and Mission Control visualization may be added without changing domain ownership.
