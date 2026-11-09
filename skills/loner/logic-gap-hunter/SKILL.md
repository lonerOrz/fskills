---
name: logic-gap-hunter
description: >
  Enumerate latent logic gaps and unconsidered execution paths in existing code
  through structured dimension coverage and counterexample construction, rather
  than asserting the presence or absence of defects. Use when the user asks to
  surface blind spots, find implementation bugs they may have missed, exhaustively
  probe edge conditions, or identify implicit assumptions that could break.
  Triggers: 逻辑漏洞, 没考虑到, 穷举可能性, 怕漏, 隐含假设, blind spot, missed bug,
  exhaustive check, unconsidered path. DO NOT use when the defect is already
  known and a fix is being requested, when a full security audit is required
  (use SAST/dependency scanning), or for style or convention review.
metadata:
  pattern: reviewer
  mode: enumeration-first
  output: structured-findings-with-coverage-disclosure
---

# Logic Gap Hunter

## Positioning

Do **not** answer "is there a bug." Answer three narrower questions:

1. Which **audit dimensions** have not been covered?
2. Which **implicit assumptions**, if violated, produce observable failure?
3. What **concrete counterexamples** can be constructed against those assumptions?

LLM cannot achieve exhaustive verification. It can function as an **enumerator and counterexample generator**, converting unstructured "gut-feel bug hunting" into a structured candidate set that the user or deterministic tooling then converges.

## Workflow

### Phase 1 — Establish dimension coverage

Read `references/audit-dimensions.md`. For each dimension, mark one of:

- `applicable` — maps to specific lines or functions; record the line range.
- `not-applicable` — state why this dimension cannot apply in the current context.

Do **not** make any defect judgment in this phase. The sole output is a coverage map: what will be examined, and what will not.

### Phase 2 — Extract implicit assumptions

Read `references/assumption-checklist.md`. Enumerate every assumption the code depends on across caller contract, configuration, concurrency/timing, and external dependency. For each assumption, record **the consequence if it does not hold**. Do not propose remedies in this phase; only state the consequence.

### Phase 3 — Construct counterexamples

For dimensions marked `applicable` whose assumptions are marked fragile, construct concrete counterexamples. Each counterexample must contain:

1. **Trigger sequence** — call order, input, or timing that reaches the suspect path.
2. **Expected behavior** — what the code intends to do.
3. **Actual behavior** — what the code would do under that trigger.
4. **Location** — file and line range.
5. **Reachability** — whether a caller or entry point can actually reach the path; if not, mark `theoretical-only` and do not inflate severity.

If no reachable counterexample can be constructed for a dimension, write `no reachable counterexample identified in this context`. Do not manufacture findings.

### Phase 4 — Emit structured report

Read `references/output-format.md` and `assets/finding-template.md`. The report must partition findings into:

- **Reachable candidates** — counterexample has a plausible entry path.
- **Assumption-dependent candidates** — valid only if a stated assumption fails.
- **Covered dimensions with no finding** — records coverage, so the user knows what was examined and what was left uncovered.

## Gotchas

- **Do not audit an entire repository in one pass.** Unbounded surface area collapses the dimension map into generic commentary. Scope to one function, module, or call chain per invocation.
- **Do not emit a finding without a location.** A finding without file and line range is unverifiable and therefore equivalent to noise.
- **Do not skip Phase 1.** Skipping the coverage map returns the process to unstructured guesswork and increases false-negative rate.
- **Do not claim exhaustiveness.** The output must state which dimensions were covered and which were not; silence on coverage is a false completeness claim.
- **Do not conflate reachability with presence.** A theoretical path that no entry point reaches is not a defect; label it `theoretical-only` and keep it out of the primary candidate list.
- **Do not rotate terminology.** Use `counterexample`, `implicit assumption`, `reachability`, `coverage` consistently; synonym rotation degrades model adherence.

## Relationship to a standard code-review skill

| Aspect | This skill | Standard code-review skill |
|---|---|---|
| Objective | Enumerate blind spots, expose assumptions, construct counterexamples | Check against a known defect taxonomy |
| Output | Candidate counterexamples + coverage disclosure | Findings + severity + remediation |
| Use case | User fears what they have not considered | User needs a standard pass over known categories |
