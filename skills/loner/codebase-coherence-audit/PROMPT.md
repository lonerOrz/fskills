# Full Codebase Coherence Audit

Use the `codebase-coherence-engineering` skill to perform a comprehensive, autonomous audit and improvement of this repository.

This is an execution task, not a request for recommendations or a report-only assessment.

## Objectives

Understand and progressively improve the complete system, from runtime behavior and individual implementation responsibilities to cross-module dependencies and global architecture.

## Initial Exploration

Start by inspecting repository instructions, working-tree changes, project entry points, and existing verification mechanisms.

Delegate independent read-only exploration to subagents:

1. Map application entry points, execution paths, and meaningful branches.
2. Map structural dependencies, module ownership, public interfaces, and package/crate relationships.
3. Identify existing verification mechanisms and establish the relevant baseline.

Reconcile their findings into one coherent understanding of the repository.

## Execution

Follow actual application execution from `main()` and other relevant entry points.

Process meaningful execution branches systematically. Within each branch, identify and audit cohesive implementation units, expanding the context whenever required to understand their responsibilities and relationships.

For each meaningful change, complete the iterative engineering loop:

**Understand → Improve → Verify → Independently Review → Refine.**

Use subagents to distribute independent investigation, implementation, and review. Keep one clear owner for integration and avoid conflicting modifications.

Do not advance past unresolved blocking findings.

## Architectural Evolution

After the execution-flow audit, synthesize the findings across the entire repository.

Pay particular attention to structural dependencies, cross-module contracts, package/crate boundaries, duplicated responsibilities, ownership, and architectural consistency.

Implement justified system-wide improvements incrementally. Revisit affected execution paths and repeat independent review and verification.

## Completion

Do not stop after generating an audit plan.

Continue implementing and validating improvements autonomously, maintaining concise progress checkpoints.

Finish with a complete independent review of the resulting changes and system-wide verification.

Report actual improvements, affected areas, review findings, verification evidence, and unresolved risks.

Prioritize architectural coherence and future changeability over maximizing the amount of code changed.
