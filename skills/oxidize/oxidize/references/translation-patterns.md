# Translation patterns: source idioms → idiomatic Rust

How to translate concepts, not syntax. During a parity port a faithful-but-ugly version is fine; this is
what to converge on when you idiomatize (Phase 7). Reach for these when a construct in the source has no
one-to-one Rust equivalent.

Contents:
- Errors and exceptions
- Null and absence
- Classes, objects, and inheritance
- Dynamic typing
- Ownership: translating a GC'd memory model
- Mutation and aliasing
- Concurrency and parallelism
- Iteration and collections
- Strings
- Modules and visibility

## Errors and exceptions

Source languages throw exceptions that propagate implicitly. Rust makes errors values: functions that can
fail return `Result<T, E>`, and `?` propagates. This is the single biggest structural change in most ports.

- **Library code:** define a concrete error enum with `thiserror`. Callers can match on variants.
  ```rust
  #[derive(thiserror::Error, Debug)]
  pub enum ParseError {
      #[error("unexpected end of input")]
      UnexpectedEof,
      #[error("invalid token at byte {0}")]
      InvalidToken(usize),
  }
  ```
- **Application code:** use `anyhow::Result<T>` and `.context("...")` to add context as errors bubble up.
  You don't need a bespoke enum for a binary that just reports and exits.
- **Translating `try/finally`:** there's no `finally`. Cleanup runs in `Drop` (RAII) — put the resource in
  a type whose `Drop` impl releases it, and it's freed on every exit path including early `?` returns.
- **Translating `catch` that swallows:** `.ok()` turns a `Result` into an `Option`, `.unwrap_or(default)`
  supplies a fallback, `if let Ok(v) = ...` handles the happy path. Don't reach for `.unwrap()`/`.expect()`
  in ported production paths — a panic is not the same as the exception the old code caught.
- **Panics ≠ exceptions.** Panics are for unrecoverable bugs, not control flow. If the source used
  exceptions for expected conditions (missing key, bad input), those become `Result`/`Option`, not panics.

## Null and absence

`null`/`nil`/`None`/`undefined` become `Option<T>`. The compiler forces you to handle the `None` case, which
eliminates a whole class of null-dereference bugs — this is often *why* a team is migrating, so lean in.

- `x?.y?.z` (optional chaining) → `x.and_then(|x| x.y).and_then(|y| y.z)` or the `?` operator inside a
  function returning `Option`.
- `x ?? default` → `x.unwrap_or(default)` / `x.unwrap_or_else(|| expensive())` / `x.unwrap_or_default()`.
- A field that "might not be set" → `Option<T>` field, not a sentinel value like `-1` or `""`.

## Classes, objects, and inheritance

Rust has no classes and no inheritance. Translate:

- **A class** → a `struct` holding the data + an `impl` block with methods. Constructors become associated
  functions, conventionally `new` (or a builder for many fields — see below).
- **An interface / abstract base with methods** → a `trait`.
- **Inheritance for shared behavior** → **composition + traits.** Put shared data in a field and shared
  behavior in a trait with default methods. "Favor composition over inheritance" isn't advice in Rust;
  it's the only option, and it's usually the better design anyway.
- **Polymorphism / virtual dispatch** → either generics (`fn f<T: Shape>(s: &T)`, static dispatch, zero
  cost) or trait objects (`fn f(s: &dyn Shape)`, dynamic dispatch, one vtable indirection). Use generics
  by default; use `dyn` when you need a heterogeneous collection (`Vec<Box<dyn Shape>>`).
- **A closed set of subtypes** (a sealed hierarchy, a variant/union) → an **enum**, which is often a better
  fit than a trait: `enum Shape { Circle { r: f64 }, Rect { w: f64, h: f64 } }` with methods that `match`.
  Enums shine when you own all the variants; traits shine when callers add new ones.
- **Many-optional-field constructors / named args** → the **builder pattern**:
  `Config::builder().host("x").port(8080).build()`.

## Dynamic typing

Where the source passed around dynamically-typed values:
- **Known-but-varying shape** → an `enum` capturing the possibilities.
- **Truly dynamic JSON-ish data** → `serde_json::Value`, and deserialize into a concrete `#[derive(Deserialize)]`
  struct at the boundary. Push the "make it typed" step to the edge of the system and keep the core typed.
- **Heterogeneous collection** → `Vec<Box<dyn Trait>>` or an enum of the element types.
- Avoid reaching for `Any`/reflection as a first move — it's rarely needed and usually signals the design
  hasn't been translated, only transliterated.

## Ownership: translating a GC'd memory model

In a GC'd language, everything is a shared reference and the runtime cleans up. Rust makes ownership
explicit. The naive translation — wrap everything in `Rc`/`Arc` to mimic shared references — works but is
un-idiomatic and slow. Prefer this ladder, in order:

1. **Move / own by value** when there's a single owner (the common case). Pass ownership when the callee
   keeps the value.
2. **Borrow (`&T` / `&mut T`)** when a function just needs to read or temporarily mutate. Most function
   parameters should be borrows. This is the biggest idiom shift from GC languages — you don't hand out
   copies, you lend references.
3. **`Rc<T>` / `Arc<T>`** only for genuine shared ownership (a value with several owners and no clear
   single one) — `Rc` for single-threaded, `Arc` across threads.
4. **`Rc<RefCell<T>>` / `Arc<Mutex<T>>`** when shared owners also need to mutate (interior mutability).
   This is the closest analog to "a normal object in a GC language," so it's tempting to reach for it
   first — resist, because it moves borrow errors to runtime and adds cost. Use it when the graph really
   is shared-and-mutable (e.g. a genuine graph/DAG, an observer registry).

**Self-referential structures** (a struct holding a reference into itself; doubly-linked lists; parent↔child
pointers) fight the borrow checker. Idiomatic Rust replaces pointer-chasing with **indices into a `Vec`**
(arena/slotmap pattern): store nodes in a `Vec`, refer to them by `usize`/generational index. Crates:
`slotmap`, `petgraph` for graphs. Don't port a linked list literally.

## Mutation and aliasing

Rust's rule: either many readers **or** one writer, never both at once. Code that freely aliased mutable
state in the source won't translate line-for-line.

- Restructure so mutation is localized: compute a new value and assign it, rather than mutating shared
  state from several places.
- When several parts must observe changes, use channels (message passing) or interior mutability
  deliberately, not by reflex.
- A function that took an object and mutated it → take `&mut T`. A function that produced a modified copy →
  take `&T` (or `T`) and return a new `T`.

## Concurrency and parallelism

This is often the payoff of the migration — real parallelism without a GIL, and data-race freedom checked
at compile time.

- **Threads sharing state** → `Arc<Mutex<T>>` for shared mutable state, or `Arc<T>` for shared immutable.
  The type system won't let you share non-`Sync` data across threads, so data races are caught at compile
  time.
- **Data parallelism** (parallel map/reduce over a collection) → `rayon`: often a one-line change,
  `.iter()` → `.par_iter()`. This is the highest-ROI concurrency win when porting CPU-bound loops.
- **Async I/O** (many concurrent connections) → `async`/`.await` on `tokio`. Note **function color**:
  `async` is contagious — an `async fn` can only be `.await`ed from another async context, so it spreads up
  the call stack. Decide the async/sync boundary deliberately; don't make everything async by reflex, and
  don't block the async runtime with CPU-bound work (offload with `spawn_blocking` or a `rayon` pool).
- **Producer/consumer** → channels (`std::sync::mpsc`, `crossbeam::channel`, or `tokio::sync::mpsc`).
- **The GIL is gone.** Logic that was serialized by a global lock in the source can now actually run in
  parallel — but that also means previously-safe-by-accident shared state now needs real synchronization,
  which Rust will force you to add.

## Iteration and collections

- Prefer **iterator chains** over index loops: `.iter().filter(..).map(..).collect()`. They're as fast as
  hand-written loops (often faster) and clearer.
- `list.append`/`push` → `Vec::push`; `dict`/`map` → `HashMap`/`BTreeMap`; `set` → `HashSet`/`BTreeSet`.
- Comprehensions → iterator chains ending in `.collect()`.
- Returning "a sequence" from a function → return `impl Iterator<Item = T>` to stay lazy, or `Vec<T>` if the
  caller needs it materialized.
- Watch for **eager vs lazy**: iterators are lazy and do nothing until consumed; a chain with no terminal
  `collect`/`for`/`sum` is a no-op. This surprises people porting from eager languages.

## Strings

- `String` is owned and growable; `&str` is a borrowed view. In function signatures, take `&str` (accepts
  both), return `String` when you produce new text.
- Rust strings are UTF-8 and **not** indexable by integer (`s[0]` doesn't compile) because a byte index
  isn't a character. Iterate `.chars()` for Unicode scalar values or `.bytes()` for raw bytes. Code that
  did `s[i]` in the source needs rethinking, not transliteration.
- `&[u8]`/`Vec<u8>` for binary data; convert with `str::from_utf8` (checked) at the boundary.

## Modules and visibility

- Files/packages → Rust modules (`mod`) and crates. A "package" usually maps to a crate; a "class file"
  usually maps to a module.
- Everything is **private by default**; add `pub` to export. This inverts some languages' defaults — expect
  to mark public API explicitly.
- Split a large ported unit into a crate with a clean `pub` surface and private internals; in a workspace,
  each cohesive component can be its own crate (see `production.md`).
