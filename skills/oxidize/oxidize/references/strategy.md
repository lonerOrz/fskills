# Migration strategy: seams, ordering, and rollout

Contents:
- Choosing a migration shape
- Finding seams (where to cut)
- Ordering the migration
- Rollout: shadow → canary → cutover
- Anti-strategies to avoid

## Choosing a migration shape

There is no single "port to Rust" move. Pick the shape that matches the system.

### 1. Incremental via FFI (in-process)
Port a module and call it from the host language across a foreign-function boundary. The app stays one
process; you swap the internals of one hot function.

- **Use when:** there's a clear performance-critical function inside a larger app you don't want to
  rewrite — a serializer in a Python service, a parser in a Node tool, a physics step in a C++ engine.
- **Cost:** you pay marshalling cost at the boundary, so the ported unit must be coarse enough that the
  work done inside dwarfs the crossing cost. Porting a function called in a tight inner loop with tiny
  payloads can be *slower* due to boundary overhead.
- **See** `interop.md` for the per-language mechanics.

### 2. Strangler service (out-of-process)
Stand up a Rust service beside the existing one and route a growing slice of responsibility to it, until
the old service is strangled and removed. Named after Martin Fowler's strangler-fig pattern.

- **Use when:** the system is a network service with clean request/response boundaries, or a set of
  microservices where one can be replaced wholesale.
- **Cost:** you add a network hop and a deployment. But you get full process isolation, independent
  scaling, and the easiest possible rollback (route traffic back).

### 3. wasm boundary
Compile Rust to WebAssembly and call it from JS, Python, or the browser. A sandboxed, portable version
of the FFI approach.

- **Use when:** the logic must run in multiple runtimes (browser + server), or you want a sandbox and are
  willing to trade some throughput for portability and safety.
- **Cost:** wasm can't freely do I/O or threads (WASI and threads help but add complexity); data crossing
  the boundary is copied.

### 4. Full rewrite
Replace a whole component in one change.

- **Use only when:** the component is small, self-contained, well-specified, and has a cheap-to-define
  boundary — a CLI tool, a single well-tested library, a stateless transformer. If you can't hold the
  whole thing in a reviewable diff and prove it with a differential harness, it's too big for a rewrite;
  make it incremental.

## Finding seams (where to cut)

A seam is a place where you can replace one implementation with another without touching the rest of the
system. Good seams share three traits: a **narrow interface** (few functions, simple types crossing),
**explicit data flow** (inputs and outputs are values, not hidden global state), and **testability** (you
can call it in isolation with known inputs).

To find seams:
- Look for existing module/package/library boundaries — someone already drew the line.
- Look for pure functions and stateless transformers — the easiest possible ports.
- Follow the data: a stage in a pipeline (parse → transform → serialize) is a natural seam.
- Beware shared mutable global state, callbacks that reach back into the host, and objects with long
  reference-heavy lifetimes threaded through everything. These aren't seams; they're the reason the
  migration is hard. Sometimes the first real task is *refactoring the old code* to create a seam before
  any Rust is written.

## Ordering the migration

Two defensible orders, pick per goal:

- **Leaf-first (lowest risk):** start with modules that have the fewest dependencies. You build the
  toolchain, CI, and interop pattern on something low-stakes, and each subsequent port reuses the paved
  road. Best when the team is new to Rust.
- **Hot-path-first (highest immediate value):** start with the single module responsible for the pain
  (the slow function, the memory hog, the crash source). You deliver the win early and prove the business
  case. Best when you need to justify the migration with results.

Either way: **one seam at a time**, each fully ported, verified, merged, and (ideally) rolled out before
starting the next. Parallel half-finished ports are how migrations stall.

## Rollout: shadow → canary → cutover

Never flip from old to new in one step in production. Stage it:

1. **Shadow (dark launch).** Run the new Rust implementation alongside the old for real traffic, compare
   their outputs, but **serve the old one's result.** Log every mismatch. This is differential testing in
   production — it catches the inputs your test corpus missed. Run it long enough to see the tail of real
   inputs.
2. **Canary.** Serve the new implementation to a small, growing fraction (1% → 5% → 25% …). Watch the
   success metric and error rates. Keep the old path warm.
3. **Cutover.** Serve 100% from the new implementation. Keep the old code and the flag in place.
4. **Remove.** Only after a soak period with the metric holding, delete the old implementation and the
   flag. Deleting the old code is the *last* step, not the first — it's your rollback until you're sure.

Gate each transition behind a **feature flag or config toggle** so rollback is instant and doesn't
require a redeploy. Wire the success metric (from Phase 0) into a dashboard/alert before you canary.

## Anti-strategies to avoid

- **The big-bang rewrite that never ships.** Six months of "almost done" with the old system frozen. The
  business changes underneath you, the two systems diverge, and it gets cancelled. Incremental avoids
  this by construction.
- **Rewriting to fix design, not language.** If the real problem is a bad design, a rewrite in the same
  design in Rust inherits the bad design plus a learning curve. Fix the design intent deliberately, and
  do it as separate, tested changes — don't smuggle it into "the port."
- **Porting the tests too literally.** The old tests encode the old language's assumptions. Keep them as
  a behavioral oracle (differential testing), but write new Rust tests that assert on behavior, not on
  the old implementation's internals.
- **Boiling the ocean of dependencies.** You don't have to replace every third-party lib with a crate on
  day one — wrap the existing native library via FFI and replace it later if it's worth it.
