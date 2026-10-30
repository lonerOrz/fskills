---
name: codebase-coherence-engineering
description: >
  Systematically explore, audit, improve, and independently verify large codebases.
  Use for full-project audits, architectural evolution, maintainability improvements,
  and complex multi-module refactoring. Follows runtime execution from entry points,
  audits cohesive implementation units, analyzes structural dependencies, and uses
  coordinated subagents with iterative verification loops.
---

# Codebase Coherence Engineering

## Mission

Improve the codebase as a coherent, correct, understandable, and evolvable system.

Follow actual application behavior, understand the structures that support it, and improve the smallest meaningful implementation units without losing sight of the whole system.

Optimize for long-term changeability rather than code volume, superficial consistency, or short-term implementation speed.

The primary agent owns the overall result.

## 1. Multi-Agent Coordination

Use subagents when delegation materially improves exploration, implementation, or verification.

The primary agent acts as the orchestrator and integrator.

Delegate independent work with explicit scope, context, constraints, and expected deliverables.

Use these responsibilities as needed:

- **Flow Explorer:** Discovers entry points, traces execution paths, and identifies cohesive implementation units.
- **Structure Explorer:** Maps module/package/crate ownership, dependency relationships, interfaces, and architectural boundaries.
- **Implementer:** Owns a clearly scoped implementation change.
- **Independent Reviewer:** Examines completed changes from a fresh context and challenges their correctness and architectural coherence.
- **Verifier:** Independently executes relevant validation and reports reproducible evidence.

These are responsibilities, not mandatory permanent agents. Combine or omit them according to task complexity.

### Delegation Rules

- Parallelize independent exploration and read-only analysis.
- Parallelize implementation only when ownership and file boundaries are genuinely independent.
- Assign one clear owner for shared interfaces, integration, and final decisions.
- Never allow competing agents to modify the same implementation concurrently without explicit coordination.
- Give reviewers the actual requirements, relevant context, and resulting changes; do not rely solely on the implementer's self-assessment.
- Treat subagent findings as evidence to evaluate, not unquestionable truth.
- If independent agents or collaboration tools are unavailable, state the limitation instead of pretending delegation occurred.

Prefer a small number of focused agents over uncontrolled agent proliferation.

## 2. Build Two Complementary System Maps

Understand the system through both its behavior and its structure.

### Runtime Map

Start at `main()` and all other actual application entry points.

Follow real execution paths through initialization, dispatch, branching, state changes, external interactions, asynchronous work, and termination.

Identify meaningful execution branches and their relationships.

### Structural Map

Independently inspect how the system is organized and connected.

Understand responsibility ownership, module boundaries, public interfaces, dependency directions, shared abstractions, and cross-module contracts.

For languages with explicit package or crate systems, understand both declared dependencies and actual source-level relationships. In Rust, include workspace membership, Cargo dependencies, feature relationships, public re-exports, and cross-crate type and trait usage.

Do not confuse a valid dependency graph with a coherent architecture.

Reconcile the runtime map and structural map throughout the audit.

## 3. Choose the Right Audit Unit

The smallest audit unit is a cohesive implementation responsibility, not an arbitrary file, line, or repository component.

It may be:

- A function or method.
- A type and the operations that maintain its invariants.
- A data structure and its ownership/lifecycle rules.
- A tightly related group of functions and types that cannot be correctly understood in isolation.

Choose a unit small enough to understand, modify, and verify meaningfully, but large enough to preserve its responsibilities and invariants.

Do not mechanically split every function or field into separate tasks.

### Expand Context Around Each Unit

Although implementation proceeds at a small scale, understanding must extend beyond the selected unit.

Inspect the relationships needed to determine its actual role:

- Callers and callees.
- Inputs, outputs, and state ownership.
- Related types, interfaces, and invariants.
- Shared components and neighboring responsibilities.
- Module and package/crate boundaries.
- Effects on relevant execution branches.

Expand or contract the investigation according to the evidence.

A locally correct implementation is not sufficient if it makes the surrounding system less coherent.

## 4. The Engineering Loop

For each meaningful unit, use this feedback loop:

**Understand → Evaluate → Improve → Verify → Independently Review → Refine**

### Understand

Determine the unit's actual responsibility, invariants, dependencies, and role in the execution flow.

### Evaluate

Use engineering judgment to identify meaningful correctness, design, organization, reliability, or performance improvements.

Distinguish root causes from symptoms. Do not manufacture work merely because a unit can be rewritten.

### Improve

Implement the smallest complete change that produces a justified improvement.

Preserve established architecture and behavior unless there is a reason to evolve them.

### Verify

Run validation appropriate to the changed behavior and its dependencies.

### Independently Review

Obtain an independent review of the implementation and its broader effects.

### Refine

Resolve substantive findings and repeat relevant verification and review.

Accept the unit only when its intended behavior is supported by evidence and no unresolved blocking findings remain.

If progress stalls or the same issue repeatedly reappears, reassess the underlying assumptions or escalate the decision instead of looping indefinitely.

## 5. Branch-Level Synthesis

After completing the cohesive units within an execution branch, reassess the branch as a whole.

Look for issues that individual unit reviews may not reveal:

- Inconsistent responsibility boundaries.
- Fragmented state ownership.
- Repeated transformations or competing abstractions.
- Incompatible assumptions between components.
- Hidden coupling across execution stages.
- Unnecessary dependencies and duplicated behavior.

Determine whether local improvements collectively form a coherent implementation.

Verify the branch as an integrated behavior, not just a collection of individually correct functions.

## 6. Global Architecture Evolution

After the in-scope execution branches have been understood and audited, perform a system-wide architectural assessment.

Synthesize findings from the runtime map, structural map, and completed branch audits.

Identify opportunities to improve:

- Responsibility and ownership boundaries.
- Dependency direction and package/crate relationships.
- Cross-module interfaces and contracts.
- Shared abstractions and canonical implementations.
- Data and state ownership.
- Lifecycle and error-handling consistency.
- Overall changeability and architectural complexity.

Consider interactions between components, not merely their individual quality.

Distinguish genuine shared responsibilities from superficial similarities. Do not force unrelated modules into a common abstraction.

Prioritize architectural improvements by their impact on system coherence and future changes.

Implement meaningful improvements incrementally. Revisit every affected execution branch and repeat the engineering loop.

Do not introduce speculative rewrites or start overlapping migrations.

## 7. Verification and Independence

Verification must be proportional to impact.

Use the project's established build, test, static-analysis, lint, formatting, architecture, and runtime validation mechanisms where relevant.

For significant changes, the implementer must not be the sole source of approval.

Independent review and execution evidence should challenge the actual result, including cross-module and cross-package effects.

A review is not a substitute for executable verification, and a passing build is not a substitute for architectural review.

If an independent reviewer is unavailable, record the result as unverified independently.

Never disable checks, hide failures, or claim success without evidence.

## 8. Progress and Completion

Maintain a concise progress ledger for large audits.

Track discovered entry points, execution branches, completed units, outstanding findings, verification evidence, and unresolved architectural decisions.

Reuse existing project tracking conventions when available. Avoid producing redundant documentation or process artifacts.

Resume from verified checkpoints rather than repeating completed work.

A full audit is complete only when:

- Relevant application entry points and execution branches have been covered.
- Meaningful cohesive units have been audited within their actual context.
- Structural dependencies and cross-module relationships have been assessed.
- Branch-level behavior has been verified.
- Global architecture has been evaluated and justified improvements have been completed.
- Significant changes have received independent review.
- Remaining limitations are explicitly recorded.

## Final Principle

**Start from behavior. Work at the level of cohesive responsibilities. Understand relationships beyond local boundaries. Use independent agents to challenge assumptions. Improve the architecture through evidence-driven iteration.**

The goal is not to make every component individually elegant.

The goal is to make the entire system easier to understand, change, verify, and evolve.
