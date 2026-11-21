---
name: logic-gap-hunter
description: >
  Enumerate latent logic gaps and unconsidered execution paths in existing code
  through structured dimension coverage and counterexample construction, rather
  than asserting the presence or absence of defects. Use when the user asks to
  surface blind spots, find implementation bugs they may have missed, exhaustively
  probe edge conditions, or identify implicit assumptions that could break.
  Triggers: 逻辑漏洞, 没考虑到, 穷举可能性, 怕漏, 隐含假设, blind spot, missed bug,
  exhaustive check, unconsidered path. Excluded when the defect is already known
  and a fix is requested, when a full security audit is required (use
  SAST/dependency scanning), or for style or convention review.
metadata:
  pattern: reviewer
  mode: enumeration-first
  output: structured-findings-with-coverage-disclosure
---

# Logic Gap Hunter

## Positioning

Answer three narrower questions, not "is there a bug":

1. Which **audit dimensions** have not been covered?
2. Which **implicit assumptions**, if violated, produce observable failure?
3. What **concrete counterexamples** can be constructed against those assumptions?

Exhaustive verification is not achievable within a single LLM pass. The skill's role is **enumerator and counterexample generator**: convert unstructured "gut-feel bug hunting" into a structured candidate set that the user or deterministic tooling then converges.

## Workflow

### Phase 1 — Establish dimension coverage

Read `references/audit-dimensions.md`. For each dimension, mark one of:

- `applicable` — maps to specific lines or functions; record the line range.
- `not-applicable` — state why this dimension cannot apply in the current context.

The sole output of this phase is a coverage map: what will be examined, and what will not. Defect judgment is deferred to Phase 3.

### Phase 2 — Extract implicit assumptions

Read `references/assumption-checklist.md`. Enumerate every assumption the code depends on across caller contract, configuration, concurrency/timing, and external dependency. For each assumption, record **the consequence if it does not hold**. This phase records assumptions and consequences only; remedies belong to Phase 4.

### Phase 3 — Construct counterexamples

For dimensions marked `applicable` whose assumptions are marked fragile, construct concrete counterexamples. Each counterexample must contain:

1. **Trigger sequence** — call order, input, or timing that reaches the suspect path.
2. **Expected behavior** — what the code intends to do.
3. **Actual behavior** — what the code would do under that trigger.
4. **Location** — file and line range.
5. **Reachability** — whether a caller or entry point can actually reach the path; if not, mark `theoretical-only` and keep it out of the primary candidate list.

If no reachable counterexample can be constructed for a dimension, write `no reachable counterexample identified in this context`.

### Phase 4 — Emit structured report

Read `references/output-format.md` and `assets/finding-template.md`. The report must partition findings into:

- **Reachable candidates** — counterexample has a plausible entry path.
- **Assumption-dependent candidates** — valid only if a stated assumption fails.
- **Covered dimensions with no finding** — records coverage, so the user knows what was examined and what was left uncovered.

## Constraints

- **Scope one unit per invocation.** Audit one function, module, or call chain at a time. Whole-repository passes collapse the dimension map into generic commentary.
- **Every finding carries a location.** File and line range are required for verifiability; a finding without them is noise.
- **Run Phase 1 first.** The coverage map is the foundation; skipping it returns the process to unstructured guesswork and raises the false-negative rate.
- **Disclose coverage explicitly.** The report states which dimensions were covered and which were not. Silence on coverage reads as a completeness claim.
- **Separate reachability from presence.** A theoretical path no entry point reaches is labeled `theoretical-only` and kept out of the primary candidate list.
- **Fix terminology.** Use `counterexample`, `implicit assumption`, `reachability`, `coverage` in every report. Synonym rotation reduces model adherence to these constraints.

## Relationship to a standard code-review skill

| Aspect    | This skill                                                           | Standard code-review skill                       |
| --------- | -------------------------------------------------------------------- | ------------------------------------------------ |
| Objective | Enumerate blind spots, expose assumptions, construct counterexamples | Check against a known defect taxonomy            |
| Output    | Candidate counterexamples + coverage disclosure                      | Findings + severity + remediation                |
| Use case  | User fears what they have not considered                             | User needs a standard pass over known categories |
