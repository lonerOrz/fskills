# Verification: proving the Rust behaves like the original

The old implementation is your **oracle** — the source of truth for correct behavior, bugs included (a
migration that "fixes" a bug silently is a migration that changed behavior you didn't sign off on).
Everything here is about proving the new code matches the oracle, and catching the cases your imagination
misses.

Set this up in **Phase 3, before porting logic.** It's the discipline that makes a migration trustworthy.

Contents:
- Differential / golden testing (the primary tool)
- Property-based testing
- Snapshot testing
- Fuzzing
- Benchmarking (proving the win)
- What to test at each phase

## Differential / golden testing (do this first)

Run the old and new implementations on the **same corpus of inputs** and assert their outputs match. This
catches behavior differences you'd never think to write a unit test for.

Two forms:
- **Live differential:** invoke both implementations and diff, per input. Best while both exist.
- **Golden/snapshot:** record the old implementation's outputs once into fixture files, then assert the new
  implementation reproduces them. Best once the old one is going away.

`scripts/parity_check.py` (bundled) is a ready-to-use harness: point it at the old command and the new
command and a directory of input files; it runs both over every input and reports mismatches with a diff.
Use it as-is for CLI-shaped units, or adapt the `run_old`/`run_new` functions for library calls.

**Build the corpus from reality, not just your head:**
- Real production inputs (sampled logs, recorded requests) — these contain the weird cases.
- Edge cases: empty, huge, malformed, boundary numeric values, non-ASCII/Unicode, nested/degenerate
  structures.
- Every input that ever triggered a bug in the old system (regression corpus).

**Normalize before comparing** where non-determinism is expected and acceptable: map/dict ordering,
timestamps, floating-point (compare within an epsilon, decide the tolerance deliberately), and any RNG
(seed both sides identically). Decide up front which differences are *acceptable* (e.g. key order in JSON)
vs. *bugs* (a different numeric result) and encode that in the comparator.

The **production shadow** (see `strategy.md`) is differential testing run against live traffic — the
ultimate corpus. Log every mismatch and triage before cutover.

## Property-based testing (proptest)

For logic where you can state an invariant but can't enumerate inputs, use `proptest` (or `quickcheck`) to
generate thousands of random inputs and check the property, shrinking any failure to a minimal case.

```rust
use proptest::prelude::*;

proptest! {
    // The classic migration property: new must equal old for all inputs.
    #[test]
    fn matches_reference(input in any::<Vec<i64>>()) {
        prop_assert_eq!(new_impl(&input), reference_impl(&input));
    }

    // Or invariants that must hold regardless of the oracle:
    #[test]
    fn roundtrips(x in any::<MyType>()) {
        prop_assert_eq!(decode(&encode(&x)), x);
    }
}
```
"New equals reference for all generated inputs" is the most powerful test you can write during a migration —
it turns the old code into an automatic, exhaustive-ish checker.

## Snapshot testing (insta)

For functions producing large structured output (rendered text, serialized structures, ASTs), `insta`
records the output and flags any change. Review diffs with `cargo insta review`.

```rust
#[test]
fn renders_report() {
    insta::assert_yaml_snapshot!(build_report(&sample_input()));
}
```
Great for locking in "the output looks exactly like this" without hand-writing giant expected strings. Seed
the initial snapshots from the *old* implementation's output so the snapshot encodes parity.

## Fuzzing (cargo-fuzz)

For anything parsing untrusted or complex input (parsers, decoders, deserializers, protocol handlers), fuzz
it. `cargo-fuzz` (libFuzzer) generates inputs to find panics, and — powerfully for migration — you can make
the fuzz target a **differential fuzzer** that asserts old == new and let it hunt for divergences.

```rust
#![no_main]
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    // Neither should panic, and they must agree.
    if let (Ok(a), Ok(b)) = (reference_parse(data), new_parse(data)) {
        assert_eq!(a, b);
    }
});
```
Run `cargo fuzz run <target>`. Fuzzing finds the inputs your corpus and your imagination both missed.

## Benchmarking (proving the win)

If the goal was performance, you must **measure it**, not assume it. Use `criterion` for statistically
sound benchmarks with regression detection.

```rust
use criterion::{criterion_group, criterion_main, Criterion, black_box};

fn bench(c: &mut Criterion) {
    let input = sample_input();
    c.bench_function("sum_squares", |b| b.iter(|| sum_squares(black_box(&input))));
}
criterion_group!(benches, bench);
criterion_main!(benches);
```
- Benchmark the **realistic workload**, not a microbenchmark that optimizes away (use `black_box`).
- Measure the metric you chose in Phase 0 (throughput, p99, RSS). For memory, measure RSS under load, not
  just allocations.
- Compare against the *old* implementation on the same machine and inputs. "Rust is faster" is a claim you
  either back with numbers or don't make. If the win is smaller than expected, the boundary overhead
  (`interop.md`) or an un-idiomatic port (excess cloning — `pitfalls.md`) is the usual cause.

## What to test at each phase

- **Phase 3 (before porting):** stand up the differential harness and pick the corpus. Record golden
  outputs from the oracle.
- **Phase 4 (per module):** the module must pass the differential harness against the oracle before you
  commit it. Add proptest "new == reference" properties for the core logic.
- **Phase 6 (rollout):** shadow in production, log mismatches, triage before canary.
- **Phase 7 (idiomatize):** the same tests must still pass after refactoring — that's how you refactor
  fearlessly. Add criterion benchmarks to confirm the metric and guard against regressions.
