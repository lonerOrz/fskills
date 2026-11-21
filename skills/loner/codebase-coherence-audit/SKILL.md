---
name: codebase-coherence-engineering
description: Explore, audit, improve, and independently verify a large codebase by tracing runtime execution from entry points, auditing cohesive implementation units, mapping structural dependencies, and coordinating subagents through iterative verify-review loops. Use when the user requests a full-project audit, architectural evolution, maintainability improvement, multi-module refactoring, or an end-to-end coherence review.
---

# Codebase Coherence Engineering

## Mission

Improve the codebase as a coherent, correct, understandable, and evolvable system.

Follow actual application behavior, understand the structures that support it, and improve the smallest meaningful implementation units without losing sight of the whole system.

Optimize for long-term changeability rather than code volume, superficial consistency, or short-term implementation speed.

The primary agent owns the overall result.

## 1. Multi-Agent Coordination

Use subagents when a task has independent read-only investigation or file-isolated implementation that benefits from parallel context. The primary agent acts as orchestrator and integrator.

Delegate independent work with explicit scope, context, constraints, and expected deliverables.

| Responsibility       | Scope                                                                                          |
| -------------------- | ---------------------------------------------------------------------------------------------- |
| Flow Explorer        | Entry points, execution paths, cohesive implementation units                                   |
| Structure Explorer   | Module/package/crate ownership, dependency relationships, interfaces, architectural boundaries |
| Implementer          | One clearly scoped implementation change                                                       |
| Independent Reviewer | Fresh-context review of completed changes: correctness and architectural coherence             |
| Verifier             | Independent execution of relevant validation; reproducible evidence                            |

These are responsibilities, not mandatory permanent agents. Combine or omit them according to task complexity.

### Delegation Rules

- Parallelize independent exploration and read-only analysis.
- Parallelize implementation only when ownership and file boundaries are genuinely independent.
- Assign one owner per shared interface, integration point, or final decision.
- Each implementation file set has one owner. Parallel modification of the same file set requires explicit coordination and a named integrator.
- Reviewer inputs must include the actual requirements, relevant context, and resulting changes. The implementer's self-assessment is supporting evidence, not the basis for approval.
- Treat subagent findings as evidence to evaluate, not unquestionable truth.
- If independent agents or collaboration tools are unavailable, state the limitation instead of pretending delegation occurred.

Prefer a small number of focused agents over uncontrolled agent proliferation.

## 2. Build Two Complementary System Maps

### Runtime Map

Start at `main()` and all other actual application entry points. Follow real execution paths through initialization, dispatch, branching, state changes, external interactions, asynchronous work, and termination. Identify meaningful execution branches and their relationships.

### Structural Map

Inspect how the system is organized and connected: responsibility ownership, module boundaries, public interfaces, dependency directions, shared abstractions, and cross-module contracts.

For languages with explicit package or crate systems, inspect both declared dependencies and actual source-level relationships. For Rust, include workspace membership, Cargo dependencies, feature relationships, public re-exports, and cross-crate type and trait usage.

A valid dependency graph and a coherent architecture are different properties. Reconcile the runtime map and structural map throughout the audit.

## 3. Choose Audit Units

The smallest audit unit is a cohesive implementation responsibility, not an arbitrary file, line, or repository component. A unit may be:

- A function or method.
- A type and the operations that maintain its invariants.
- A data structure and its ownership/lifecycle rules.
- A tightly related group of functions and types that cannot be correctly understood in isolation.

Choose a unit whose invariants fit in one review. Expand context whenever a change would affect callers, state ownership, or shared contracts.

Split a unit into separate tasks only when each resulting task has its own invariants and can be verified independently.

### Expand Context Around Each Unit

Understanding extends beyond the selected unit. Inspect the relationships that determine its actual role:

- Callers and callees.
- Inputs, outputs, and state ownership.
- Related types, interfaces, and invariants.
- Shared components and neighboring responsibilities.
- Module and package/crate boundaries.
- Effects on relevant execution branches.

Expand or contract the investigation according to the evidence. A locally correct implementation is not sufficient if it makes the surrounding system less coherent.

## 4. The Engineering Loop

Each meaningful unit must cover six activities. Activities may interleave when dependencies require; none may be skipped.

1. **Understand** — actual responsibility, invariants, dependencies, role in the execution flow.
2. **Evaluate** — confirmed correctness, design, organization, reliability, or performance issue. Distinguish root causes from symptoms; a unit is changed only when the change addresses a confirmed issue.
3. **Improve** — smallest complete change that produces the justified improvement. Preserve established architecture and behavior unless there is a reason to evolve them.
4. **Verify** — validation appropriate to the changed behavior and its dependencies.
5. **Independently Review** — review of the implementation and its broader effects by a context other than the implementer.
6. **Refine** — resolve substantive findings; repeat relevant verification and review.

Accept the unit only when its intended behavior is supported by evidence and no unresolved blocking findings remain.

If progress stalls or the same issue repeatedly reappears, reassess the underlying assumptions or escalate the decision instead of looping indefinitely.

## 5. Branch-Level Verification

After completing the cohesive units within an execution branch, reassess the branch as a whole. Look for issues individual unit reviews may not reveal:

- Inconsistent responsibility boundaries.
- Fragmented state ownership.
- Repeated transformations or competing abstractions.
- Incompatible assumptions between components.
- Hidden coupling across execution stages.
- Unnecessary dependencies and duplicated behavior.

Verify the branch as an integrated behavior, not a collection of individually correct functions.

## 6. System-Level Evolution

After the in-scope execution branches have been understood and audited, synthesize findings from the runtime map, structural map, and completed branch audits.

Identify opportunities to improve:

- Responsibility and ownership boundaries.
- Dependency direction and package/crate relationships.
- Cross-module interfaces and contracts.
- Shared abstractions and canonical implementations.
- Data and state ownership.
- Lifecycle and error-handling consistency.
- Overall changeability and architectural complexity.

Consider interactions between components, not merely their individual quality. Introduce a shared abstraction only when two or more modules share the same invariants and the abstraction reduces change coupling; superficial similarity is not sufficient.

Prioritize architectural improvements by impact on system coherence and future changes. Implement meaningful improvements incrementally. Revisit every affected execution branch and repeat the engineering loop.

A speculative rewrite or an overlapping migration starts only after the current in-scope work has been verified and reviewed.

## 7. Verification and Independence

Verification must be proportional to impact. Use the project's established build, test, static-analysis, lint, formatting, architecture, and runtime validation mechanisms where relevant.

For significant changes, approval must come from a reviewer other than the implementer. Independent review and execution evidence should challenge the actual result, including cross-module and cross-package effects.

A review is not a substitute for executable verification, and a passing build is not a substitute for architectural review.

Verification evidence must come from executed commands. When a check fails, record the failure and its resolution before marking the change complete.

If an independent reviewer is unavailable, record the result as unverified independently.

## 8. Progress and Completion

Maintain a concise progress ledger for large audits. Track discovered entry points, execution branches, completed units, outstanding findings, verification evidence, and unresolved architectural decisions.

Use the project's existing tracking conventions. Create a new artifact only when no existing convention covers the need.

Resume from verified checkpoints rather than repeating completed work.

A full audit is complete only when:

- Relevant application entry points and execution branches have been covered.
- Cohesive units have been audited within their actual context.
- Structural dependencies and cross-module relationships have been assessed.
- Branch-level behavior has been verified.
- Global architecture has been evaluated and justified improvements have been completed.
- Significant changes have received independent review.
- Remaining limitations are explicitly recorded.

## Final Principle

**Start from behavior. Work at the level of cohesive responsibilities. Understand relationships beyond local boundaries. Use independent agents to challenge assumptions. Improve the architecture through evidence-driven iteration.**

The goal is not to make every component individually elegant. The goal is to make the entire system easier to understand, change, verify, and evolve.
