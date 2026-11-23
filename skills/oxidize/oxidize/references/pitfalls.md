# Pitfalls: the migration anti-patterns and how to escape them

The failure modes that turn a Rust migration into a slog or a regression. Most come from translating the
source language *literally* instead of translating its *intent*. When you hit friction, check here before
forcing it.

Contents:
- Fighting the borrow checker by cloning everything
- Translating inheritance literally
- Reaching for `unsafe` to make the compiler stop complaining
- Self-referential structures
- `Arc<Mutex<...>>` everywhere
- Async everything (function-color spread)
- Panics as control flow
- Stringly-typed ports
- The debug-build "Rust is slow" trap
- Rewriting behavior during a parity port

## Fighting the borrow checker by cloning everything

**Symptom:** every borrow error gets "fixed" with `.clone()` or `.to_owned()` until it compiles. The result
works but allocates constantly and is often *slower* than the source language — undermining the whole
reason for the migration.

**Why it happens:** GC-language habits assume free sharing; the borrow checker refuses, and clone makes the
error go away.

**Escape:** treat a borrow error as a design question — "who owns this, and who's just looking?" Usually the
answer is "pass a borrow (`&T`)" not "clone it." Restructure so there's one clear owner and everyone else
borrows. Reserve `.clone()` for when you genuinely need a second independent copy. If clippy flags
`redundant_clone`, listen. During Phase 4 parity porting a few defensive clones are acceptable to get green
tests; hunt them down in Phase 7.

## Translating inheritance literally

**Symptom:** trying to recreate a class hierarchy with traits and ending up in a tangle of trait objects,
supertraits, and downcasting — reinventing OOP badly.

**Escape:** Rust isn't OOP; stop porting the hierarchy and port the *intent*. Shared behavior → trait with
default methods. Shared data → a common field (composition). A fixed set of variants → an `enum` with a
`match`, which is usually cleaner than a trait hierarchy. Only use `dyn Trait` when callers genuinely need
an open, heterogeneous set. See `translation-patterns.md` → "Classes, objects, and inheritance."

## Reaching for `unsafe` to make the compiler stop complaining

**Symptom:** `unsafe`, raw pointers, `transmute`, or `static mut` used to bypass a borrow-check or type
error the porter didn't want to solve.

**Why it's dangerous:** `unsafe` doesn't turn off the rules — it moves responsibility for them from the
compiler to you, and a mistake is undefined behavior (memory corruption, not a clean panic). You've traded
the memory-safety guarantee that was likely a *reason for the migration*.

**Escape:** almost everything a port needs is expressible in safe Rust. If you think you need `unsafe`,
you're probably missing an idiom — arena/index pattern instead of self-references, `Rc<RefCell>` for a
shared-mutable graph, a channel instead of shared globals. Legitimate `unsafe` (raw FFI, a genuinely
unrepresentable data structure, a proven-necessary optimization) belongs isolated in the `bindings` crate
with a `// SAFETY:` comment justifying each block — never scattered through `core`.

## Self-referential structures

**Symptom:** trying to port a doubly-linked list, a tree with parent pointers, or a graph with cross-links,
and drowning in lifetime errors or `Rc<RefCell<>>` soup.

**Escape:** don't store references *into* your own structure. Store nodes in a `Vec` (an arena) and refer to
them by index (`usize` or a generational index from `slotmap`). For graphs, use `petgraph`. This is faster
(contiguous memory), simpler, and sidesteps the borrow checker entirely. See `translation-patterns.md` →
"Ownership."

## `Arc<Mutex<...>>` everywhere

**Symptom:** wrapping most state in `Arc<Mutex<T>>` by reflex because "the object might be shared," creating
lock contention and the possibility of deadlocks — mimicking the GC model instead of designing ownership.

**Escape:** most values have a single owner; pass ownership or borrow. Use `Arc<Mutex>` only for state that
is *genuinely* shared and mutated across threads. Consider message passing (channels) as an alternative to
shared locked state — often it's both faster and simpler. For read-mostly shared data, `Arc<T>` (immutable)
or `arc-swap`/`RwLock`.

## Async everything (function-color spread)

**Symptom:** making every function `async` because one deep function does I/O, then wrestling with a runtime
even for pure CPU code, and blocking the runtime with heavy computation.

**Escape:** `async` is contagious and has a cost; use it only where you have real I/O concurrency to exploit
(many simultaneous connections/requests). Keep CPU-bound logic as plain sync functions and call them from
async via `spawn_blocking` or a `rayon` pool. Draw the async boundary deliberately at the I/O edge; don't
let it creep into the pure core. See `translation-patterns.md` → "Concurrency."

## Panics as control flow

**Symptom:** `.unwrap()`/`.expect()`/`panic!` used where the source used exceptions for *expected*
conditions (missing key, bad input, not-found). In a service, a panic can take down a request handler or the
process.

**Escape:** expected failure → `Result`/`Option` and `?`. Reserve panics for genuine bugs/invariant
violations. Audit ported code for `unwrap` on anything that depends on input. In a server, also set a
panic-catch boundary per request so one bad request can't crash the worker.

## Stringly-typed ports

**Symptom:** passing `String`s and `HashMap<String, String>` around because the source was dynamically
typed, then indexing strings by integer (which doesn't compile) or comparing magic string values.

**Escape:** introduce types at the boundary — parse the dynamic data into structs/enums once, then work with
typed values. Use `enum`s for closed sets of "kinds" instead of string tags. Remember Rust strings are UTF-8
and not integer-indexable; iterate `.chars()`/`.bytes()`. See `translation-patterns.md` → "Strings" and
"Dynamic typing."

## The debug-build "Rust is slow" trap

**Symptom:** benchmarking a debug build, concluding the Rust port is barely faster (or slower) than the
source, and losing faith in the migration.

**Escape:** always measure `--release`. Debug builds disable optimizations and can be 10–100× slower.
Confirm release-profile settings, use `black_box` in benchmarks so work isn't optimized away, and account
for FFI boundary overhead if you're calling across a binding (a too-chatty boundary can erase the win — make
it coarse). See `verification.md` → "Benchmarking" and `interop.md`.

## Rewriting behavior during a parity port

**Symptom:** "while I'm in here" improvements — fixing a bug, changing an edge case, tidying an output
format — folded into the translation. Now the differential harness fails and you can't tell whether it's a
port error or an intended change.

**Escape:** during Phase 4, port for *exact* parity, oracle-bugs included. Keep the differential harness
green. Land behavior changes as **separate, deliberate commits after** parity is established and signed off,
so each change is reviewable in isolation. This is discipline, not pedantry — it's what lets you trust the
cutover.
