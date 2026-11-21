---
name: handoff
description: Write a self-contained handoff document so another agent or LLM session can resume this work without access to this conversation. Use when the user asks for a handoff, session continuation, 交接, 写给下一个会话, or explicitly requests a handoff from this session. Excluded when the user wants a human-readable summary, a changelog, or a commit message.
---

# Handoff

Write a handoff document for another agent or LLM session that will resume this work with no access to this conversation.

The handoff succeeds only if a competent agent holding this file and the repository can reach the correct next action without asking this session anything and without re-deriving a settled decision.

## Document boundary

The deliverable is the document below, nothing before or after it. First character is the `#` of `## Goal`; last character is the final character of the last line of the last section.

## Writing rules

- **Precise over abstract.** Every claim carries a file path, symbol name, executed command, observed result, or error message. "Almost done" and "needs polish" are not states.
- **Imperative for the successor.** Each `Next Steps` item begins with a verb (`Fix`, `Run`, `Add`, `Verify`). Each `Done` item states a fact. The document contains no `I`, `my`, `we`, or `our`.
- **User task only.** `Progress` and `Next Steps` describe the user's task. Writing this handoff is not a user task and does not appear in either section.
- **Decisions carry rationale.** Each `Key Decisions` entry states the decision and the evidence or constraint that settled it. A preference without rationale is not a decision.
- **Reference, do not duplicate.** Point to files, PRs, issues, and commits by path or identifier. Inline copies drift from the source of truth.

## Structure

Seven sections, fixed order. A section with no content holds `_None._` and keeps its heading; deleting the heading erases the distinction between "nothing here" and "not checked".

## Goal

What the user is trying to accomplish, one or two sentences.

## Constraints & Preferences

- Constraints, preferences, or prohibitions stated by the user; otherwise `_None._`.

## Progress

### Done

- [x] Completed work with artifacts (files, commands, results).

### In Progress

- [ ] Current work, the state reached, and the next action.

### Pending

- [ ] Tasks mentioned but not started.

## Key Decisions

- **Decision**: rationale, with the evidence that settled it.

## Critical Context

- File paths, symbol names, error messages, code snippets, repository state. Everything the successor needs to execute Next Steps.

## Next Steps

1. Imperative sentence, directly executable.

## Self-check

Run every item before emitting. Any failure means revise and re-check.

| Check               | Pass condition                                                                       |
| ------------------- | ------------------------------------------------------------------------------------ |
| Boundary            | First character `#`, last character is the document's final character                |
| Locatable           | Every path and symbol name can be found in the repository                            |
| Reproducible        | Every command is executable and carries its output or exit code                      |
| No first person     | `\bI\b`, `\bmy\b`, `\bwe\b`, `\bour\b` return no matches                             |
| No mechanism leak   | `Progress` and `Next Steps` contain no handoff, summary, or context-document wording |
| Empty sections      | Empty sections read `_None._` and keep their heading                                 |
| Decisions justified | Every entry has both the decision and its rationale                                  |

## Edge cases

- **Nothing to hand off.** Write `_None._` in all three `Progress` subsections. `Next Steps` holds the first action implied by `Goal`.
- **Goal not explicit.** Quote the user's most recent substantive request in `Goal`. Mark `Constraints & Preferences` as `Goal pending user confirmation`.
- **Failed attempts exist.** Record them in `Done` marked `failed`, or in `Critical Context` with the original error message. `Pending` holds only unstarted work.
