---
name: architecture-complexity-audit
description: Use when a user asks for a deep codebase review or redesign because complexity is growing, responsibilities are unclear, related logic is scattered, or state and settings may be duplicated. Find root causes and recommend the simplest coherent design that meets the real requirements, with a reviewed refactoring plan.
---

# Architecture Complexity Audit

## Purpose

Find a clear, simple design that meets the system's real needs without unnecessary complexity.

Treat code as a resource. So are data, state, settings, rules, interfaces, dependencies, computation, memory, developer attention, and future maintenance. The goal is not to minimize code at any cost. The goal is to make the whole system easier to understand and change while preserving correct behavior and necessary flexibility.

Use this question to guide the work:

**What is the smallest coherent set of concepts, rules, and stored facts that can express the real requirements and produce the right behavior?**

Do not assume the user's proposed solution is correct. Treat it as an idea to test. Do not limit the audit to examples the user has already noticed.

By default, review and propose a plan only. Do not change code unless the user asks for implementation.

## Working Principles

Apply these principles together; do not follow them mechanically.

1. **Understand before changing.** Learn what the system must do and how it works before judging its design.
2. **Reduce separate decisions.** Avoid making people choose, store, update, or remember the same fact in multiple places.
3. **Derive what can be derived.** When a value can be safely and reliably calculated from more basic information, prefer that over a second setting or copy of the value. Keep explicit settings when they express real user intent or a real system constraint.
4. **Unify what means the same thing.** If several parts follow the same rule for the same reason, look for one shared model or mechanism. If their meanings or constraints differ, keep those differences clear.
5. **Give each decision a clear owner.** State, rules, and behavior should have a clear place where they are defined and changed.
6. **Make rules hard to break.** Use types, interfaces, constructors, and encapsulation when they prevent invalid states or hidden assumptions at reasonable cost.
7. **Fix causes, not symptoms.** Prefer removing the reason complexity keeps appearing over patching each place where it shows up.
8. **Count the cost of abstraction.** A new type, trait, layer, manager, or setting is useful only when its benefit exceeds the extra concepts and work it adds.
9. **Optimize the whole system.** A change is not an improvement if it merely moves complexity to another module, caller, runtime phase, or future maintainer.
10. **Keep real requirements.** Correctness, security, performance, accessibility, protocol rules, compatibility, and meaningful user control are not waste to be removed.

## Two Review Roles

### Agent A — Auditor

Build a reliable picture of the system, find likely root causes, and propose ways to improve it. Look beyond familiar code smells and beyond the user's examples.

For each important finding, explain:

- **Evidence:** where the relevant behavior or design appears in the code.
- **Cause:** why the problem exists, not just what looks wrong.
- **Effect:** how it affects correctness, change effort, resource use, or understanding.
- **Options:** plausible ways to address it, including leaving it as it is when appropriate.
- **Cost and risk:** what each option adds, removes, or could break.
- **Confidence:** what is known and what still needs checking.

### Agent B — Reviewer

Review the code and Agent A's claims with an independent and skeptical view. Do not merely summarize the audit or assume that its findings are right.

Ask:

- Is the problem real, and does the evidence support the claim?
- Is the suggested change aimed at the cause?
- Are apparently similar parts actually different in meaning or constraint?
- Does the proposal combine things that should stay separate?
- Does it split things that could share one clear rule?
- Does it add more concepts or move work elsewhere instead of reducing total complexity?
- Is there a simpler option with nearly the same benefit?
- Could it break behavior, ownership, lifecycle, performance, security, or compatibility?

The reviewer may reject a finding or recommend a different solution. Record material disagreements and how they were resolved.

### Use of Multiple Agents

If the tools support separate agents, give the auditor and reviewer distinct tasks and have the reviewer inspect the source rather than relying only on the audit report. Otherwise, complete the audit first, then perform a separate review pass from the skeptical reviewer's point of view. Never claim that independent agents were used if they were not.

For important disagreements, allow a focused rebuttal and revision. Stop when the evidence and trade-offs are clear enough to decide. State any uncertainty that remains.

## Workflow

### 1. Understand the system

Inspect enough of the repository to understand the main behavior and its boundaries. Follow important paths from input or request, through decisions and state changes, to output and cleanup. Check relevant callers, tests, and dependencies when available.

Identify:

- What the system must do and what constraints it must keep.
- Its main concepts and the relationships between them.
- Where information comes from and where it flows.
- Who owns state and resources, and who may change them.
- Where decisions are made and where rules are enforced.
- How creation, updates, failures, and cleanup work.

Do not assume that a module name or comment proves what the code actually does. Use the implementation and call paths as evidence. If some source is missing, state the limit rather than guessing.

### 2. Find sources of unnecessary complexity

Search the whole system, not just individual files. Use questions such as:

- Is the same fact, rule, or concept represented in more than one place?
- Does a value need to be set manually even though the system already has enough information to calculate it?
- Must several places be changed together to keep one idea consistent?
- Does a component make decisions that belong to another component?
- Must a feature expose its internal details to unrelated parts of the system?
- Are some states or settings meaningless for certain kinds of object?
- Are important rules implicit, repeated, or easy to bypass?
- Does a common abstraction hide meaningful differences?
- Do different abstractions repeat the same underlying mechanism?
- Is complexity caused by a missing concept, a poor boundary, a real external constraint, or the abstraction itself?
- Would a change make the system simpler overall, or merely make one part look simpler?

These are prompts for investigation, not assumptions that every problem exists. Repeated code is not automatically waste, and different code is not automatically a problem.

### 3. Explain the root cause

Connect each important finding to the way the system is modeled. Explain how the current design creates the observed cost or risk. Separate direct evidence from inference and personal preference.

Use these labels when helpful:

- **Confirmed:** supported by direct code evidence or a reproduced result.
- **Likely:** a strong concern, but not fully proven.
- **Opportunity:** a possible improvement, not a defect.
- **Rejected:** considered and not recommended, with a reason.
- **Needs checking:** depends on missing code, external behavior, or a test that has not been run.

### 4. Compare possible changes

For important decisions, consider the useful range of options. This may include keeping the design and fixing a local issue, improving the current model, joining parts under a shared rule, separating concepts that were mixed together, deriving values instead of storing them, or choosing another design that better fits the evidence.

Do not force a fixed number of options when the problem is small. Do not compare options that are only different in name.

Judge options by their effect on the whole system:

- Correctness and preservation of required behavior.
- Number of concepts, rules, settings, and states that must be maintained independently.
- Clarity of ownership and responsibility.
- Reuse and ease of future change.
- Ease of testing and debugging.
- Resource and runtime cost.
- Compatibility and migration effort.
- New complexity introduced by the solution.

Choose the simplest option that satisfies the real requirements. If the more abstract design does not deliver enough benefit, prefer the simpler one. If the local fix leaves a repeated root cause in place, explain why a wider change is justified.

### 5. Challenge and review the recommendation

Before deciding, have the reviewer test the leading proposal against counterexamples and likely future changes. Look for hidden costs, false assumptions, accidental loss of user control, and real differences that must remain visible.

Revise the proposal when the criticism is supported. The goal is not for both roles to agree on everything; the goal is a decision supported by evidence and clear trade-offs.

### 6. Describe the target design

For each accepted major change, explain the intended result in terms of concepts and responsibilities, not just file moves.

Make clear:

- What each important part represents and owns.
- Which information is the source of truth.
- Which values are explicit, derived, cached, or runtime-only.
- Where each rule is defined and enforced.
- How the parts communicate.
- Which differences are shared through a common rule and which remain separate.
- Which behaviors and constraints must not change.

Use diagrams, tables, or type/interface sketches only when they make the design easier to understand. Do not create abstractions or prescribe design patterns just to make the plan look complete.

### 7. Plan a safe migration

Order the work by cause, dependency, and risk, not simply by file order. For each major step, identify the affected parts, intended change, prerequisites, required checks, and conditions for success.

Preserve existing behavior unless a behavior change is explicitly part of the goal. Include tests for important rules and lifecycle paths. If implementation is requested, make changes in reviewable stages and run available checks. Report only tests and commands that were actually run, with their observed results.

## Output

Adjust the level of detail to the size and risk of the task. For a deep review, provide:

1. **Main conclusion:** the largest sources of unnecessary complexity and the recommended direction.
2. **Current system model:** the key concepts, relationships, ownership, and important flows.
3. **Reviewed findings:** evidence, root cause, effect, confidence, and proposed response.
4. **What to unify, derive, separate, or keep:** explain which changes reduce independent decisions and which differences are necessary.
5. **Options and trade-offs:** why the recommendation is better than realistic alternatives.
6. **Target design:** responsibilities, sources of truth, boundaries, and examples where useful.
7. **Migration plan:** ordered changes, affected code, tests, and acceptance conditions.
8. **Risks and unknowns:** missing evidence, assumptions, compatibility issues, and what must be verified.

Do not fill sections with guesses just to follow the format. Keep the report as short as the task allows while including enough detail to support major decisions.

## Completion Standard

The work is complete when:

- The important parts of the system and their relationships are understood.
- Major claims are grounded in evidence and have been challenged by review.
- The proposed design reduces unnecessary independent facts, rules, state, or coordination without hiding real differences.
- The choice and its costs are clear compared with simpler alternatives.
- The migration can be carried out and checked in a sensible order.
- Unknowns are stated openly rather than turned into facts.
