# Full Codebase Coherence Audit

Use the `codebase-coherence-engineering` skill to perform a comprehensive, autonomous audit and improvement of this repository.

This is an execution task. The deliverable is a verified set of implemented improvements, not a plan or a report-only assessment.

## Objectives

Understand and progressively improve the complete system, from runtime behavior and individual implementation responsibilities to cross-module dependencies and global architecture.

## Initial Exploration

Inspect repository instructions, working-tree changes, project entry points, and existing verification mechanisms.

Delegate independent read-only exploration to subagents:

1. Map application entry points, execution paths, and meaningful branches.
2. Map structural dependencies, module ownership, public interfaces, and package/crate relationships.
3. Identify existing verification mechanisms and establish a baseline.

Reconcile the findings into one coherent understanding of the repository.

## Execution

Follow actual application execution from `main()` and other relevant entry points. Process meaningful execution branches systematically. Within each branch, identify and audit cohesive implementation units, expanding context whenever required to understand their responsibilities and relationships.

For each meaningful change, cover all six engineering activities defined in the skill: **Understand, Evaluate, Improve, Verify, Independently Review, Refine**. Activities may interleave, but none may be skipped.

Use subagents to distribute independent investigation, implementation, and review. Keep one clear owner for integration. Do not advance past unresolved blocking findings.

## Architectural Evolution

After the execution-flow audit, synthesize findings across the repository. Focus on structural dependencies, cross-module contracts, package/crate boundaries, duplicated responsibilities, ownership, and architectural consistency.

Implement justified system-wide improvements incrementally. Revisit affected execution paths and repeat independent review and verification.

## Completion

Continue implementing and validating improvements until the completion checklist in the skill is satisfied. Maintain concise progress checkpoints.

Finish with an independent review of the resulting changes and system-wide verification.

Report actual improvements, affected areas, review findings, verification evidence, and unresolved risks.

Prioritize architectural coherence and future changeability over the volume of code changed.
