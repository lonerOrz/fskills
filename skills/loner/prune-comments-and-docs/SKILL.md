---
name: prune-comments-and-docs
description: Review and prune code comments, doc comments, lint reasons, prose documentation, and program messages. Use when asked to delete, review, or improve these texts, when the user says 清理注释 / 文档太啰嗦 / 删掉冗余注释 / 注释太多, or when a change introduces narration that duplicates the code. Excluded when the user wants new documentation written, a style-guide review, or a code review of logic and naming.
---

# Prune Comments and Docs

## Goal

Delete by default. Keep an optional comment only when all three hold:

1. It states a trap, invariant, ordering or ownership constraint, or external contract that reading the code will not show.
2. It applies directly to the code it sits on.
3. It appears once.

Delete everything else, including module docs and overviews that fail this bar. Do not add new explanatory comments or invent details to pad existing ones.

Assume code readers know the language, libraries, and standard concepts; treat project-specific rules as new information. For private code and inline code literals, assume readers also read the body.

## Scope

- Review the named files, or the current change if no files are named.
- Read the callers, callees, and tests needed to determine each text's role.
- Edit only comments, documentation, lint reasons, and message text. Program logic, names, and types stay unchanged.
- Leave generated and vendored files, tool directives, and license and attribution notices unchanged. Review explanations attached to directives.
- Keep required items present and valid: safety comments, lint reasons, doctests, required API docs. Edit their prose when needed.
- Rewrite program messages freely. When a message carries no information, keep the text and recommend removal in the report.

## Editing rules

- **Verify before stating.** Check claims against code, callers, tests, and external requirements. State verified intent; describe possible outcomes as possibilities.
- **Text vs code.** When they disagree, check intended behavior first. If intent is unclear, leave the text and report it. If the text's necessity is unclear, delete it.
- **Delete narration.** Remove step-by-step narration, inferable consequences, and text that repeats names, types, code, test labels, or assertions.
- **Relocate before deleting.** Delete notes left out of place after code changed or describing code elsewhere. Move a displaced constraint to its real site only when that site needs it.
- **Delete weak points entirely.** A half-sentence that retains a weak point is not a valid edit. Keep conditions and exceptions needed for accuracy. Limit any module doc or overview to three lines; put cross-cutting policy in reference documentation.
- **Plain technical prose.** Use consistent technical terms and ordinary punctuation. Name standard concepts when useful (name the algorithm; leave its steps in the code). Remove filler, praise for the design, and storytelling or metaphors that add vocabulary without information.
- **Prefer structural fixes.** Suggest a clearer name, type, assertion, or test when that removes the need for a comment.
- **Define behavior positively.** Replace `X is not Y` with a direct statement of what X does. The patterns `subject, not negative`, `abc instead of negative`, and `abc is not negative` imply the opposite behavior and mislead readers; rewrite the sentence straight.

## Text-specific requirements

- **External docs.** Docs and guides for external callers must be usable without inspecting the implementation; put caller requirements and guarantees there. Internal items in private modules follow the private-code rules.
- **Tests.** A test can verify behavior without explaining why. Keep needed rationale and labels identifying test setup conditions.
- **Safety comments.** State only the concrete invariant preventing UB. Omit adjacent checks, behavior narration, and standard language or library mechanics. Point to a single module or type invariant when one covers the block. Report safe functions whose safety comments rely on unchecked caller assumptions.
- **Lint reasons.** Address the suppressed lint directly: why it does not apply, or why the trade-off is acceptable.
- **Reference docs.** Describe current behavior and limitations. Put past edits in history, decision, or plan documents; put planned work in TODOs or issues. Keep documents meant to record history, decisions, or plans. Move needed facts out of session logs before deleting them.
- **Program messages.** Before changing wording, check whether tests, scripts, or tools depend on it. Preserve formatting arguments and error-handling behavior. Include only facts missing from the rest of the error chain or log line. In panic and `.expect()` messages, state which assumption failed. Follow the project's message style.

## Verification and report

Run checks relevant to the edits, including doctests and documentation checks where applicable. Report checks you could not run.

Keep the report brief:

- State what you reviewed and the check results.
- List every surviving doc block longer than three lines with its reason.
- List every changed program message.
- List every deleted file.
- Report unresolved intent, unchecked safety assumptions, and suggestions outside scope.
- List only edits that change meaning, structure, or the surviving doc inventory; routine wording edits need not appear.

## Examples

### Module essay → one invariant

Before:

```rust
//! Decode worker: the app's demand service over a store of previews.
//!
//! Two inputs decide what the thread does: the app's wants, the
//! artifacts its presentation is missing right now, and the plan, the
//! order in which pages are worth producing into the store ahead of
//! time. Wants are served first, from the store when the plan already
//! warmed them and otherwise by decoding and minting on the spot. The
//! plan alone never delivers anything; it only fills the store.
//!
//! Nothing decoded survives here: the preview store is the only cache.
```

After:

```rust
//! Decoded artifacts live only in the preview store.
```

Paragraphs one and two restate types and reference docs; only the cache-ownership invariant stays.

### Narration vs local reason

Before:

```rust
pub fn sync(&mut self) -> Result<()> {
    // Fetch the remote manifest.
    let remote = self.fetch_manifest()?;
    // Compare it with the local state.
    let diff = self.local.diff(&remote);
    // Apply even an empty diff because `apply` refreshes the lock file.
    self.apply(diff)?;
    Ok(())
}
```

After:

```rust
pub fn sync(&mut self) -> Result<()> {
    let remote = self.fetch_manifest()?;
    let diff = self.local.diff(&remote);
    // Apply even an empty diff because `apply` refreshes the lock file.
    self.apply(diff)?;
    Ok(())
}
```

The calls show the sequence. The retained comment explains why an empty diff is still applied; it stays as written.

### Public behavior stated positively

Before:

```rust
/// Replaces the active configuration.
/// Each request holds a reference to the configuration it started with.
/// Replacing the active configuration leaves those references unchanged.
/// New requests use the replacement.
pub fn reload(&self, config: Config) { ... }
```

After:

```rust
/// New requests use `config`; in-flight requests keep their configuration.
pub fn reload(&self, config: Config) { ... }
```

State the timing rule directly; ownership mechanics stay in the implementation.

### Constraint beside its owner

Before:

```rust
/// Rendering resources.
/// The window owns the GL context, so it drops after pages and egui.
struct Gl {
    pages: PageTextures,
    egui: egui_glow::EguiGlow,
    window: Window,
}

impl Drop for Gl {
    fn drop(&mut self) {
        // The drop body runs before the fields drop.
        // egui's GL objects are destroyed here while the context is alive.
        self.egui.destroy();
    }
}
```

After:

```rust
struct Gl {
    pages: PageTextures,
    egui: egui_glow::EguiGlow,
    // Must drop last: owns the GL context used by the fields above.
    window: Window,
}

impl Drop for Gl {
    fn drop(&mut self) {
        self.egui.destroy();
    }
}
```

The lifetime requirement sits beside `window`. The wrapper caption and the drop-order narration are gone.

### Uncertain intent stays and is reported

```rust
/// Blocks until the worker has stopped.
pub fn shutdown(&self) {
    self.stop.store(true, Ordering::Release);
}
```

If intended behavior remains unclear, leave the comment and report:

> `shutdown` promises to wait for the worker, but the implementation only sets a flag. Confirm whether it must wait before changing the contract.

### Safety comment → invariant + owner

Before:

```rust
// SAFETY: Caller ensures the GL context is current on the render thread,
// `shader` was just created on it, and this frees the temporary handle.
unsafe { gl.delete_shader(shader); }
```

After:

```rust
// SAFETY: Context is current (`Window`).
unsafe { gl.delete_shader(shader); }
```

Drop the local restatement and behavior narration; point to the invariant's owner.
