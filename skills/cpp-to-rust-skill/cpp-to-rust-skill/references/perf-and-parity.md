# Performance and Parity Gates

Use this reference to keep migration quality measurable.

## Functional Parity Gates

1. Characterization tests pass for all required features.
2. Golden vectors match byte-for-byte where protocol/file compatibility matters.
3. Error behavior remains compatible for public APIs.

## Differential Testing

The gold standard for validating migration correctness: provide the same input to both C++ and Rust implementations and compare outputs.

1. Build a harness that runs both implementations on the same input corpus.
2. Compare outputs byte-for-byte (or structurally for complex outputs).
3. Use differential fuzzing to generate random inputs and detect behavioral divergence.
4. Run differential tests as part of CI until C++ code paths are fully removed.

### Differential Fuzzing Setup

```rust
// Harness example using cargo-fuzz
fuzz_target!(|data: &[u8]| {
    let cpp_result = unsafe { cpp_parse(data.as_ptr(), data.len()) };
    let rust_result = rust_parse(data);
    assert_eq!(cpp_result, rust_result);
});
```

## Performance Gates

1. Compare Rust and C++ on the same representative workloads.
2. Track throughput, p95/p99 latency, allocations, and peak RSS.
3. Define acceptable regression thresholds before porting (for example <= 5%).
4. Block merges when regressions exceed thresholds without approved exceptions.
5. Always benchmark in `--release` mode. Never compare debug Rust vs optimized C++.
6. Use Criterion for statistical significance (confidence intervals, outlier detection).

Load [performance-traps.md](./performance-traps.md) for specific Rust patterns that silently degrade performance.

## Safety and Correctness Gates

1. Run `cargo test` and `cargo clippy` with strict warnings.
2. Run sanitizer/fuzz/property tests for parser or boundary-heavy paths.
3. Require explicit review for any newly introduced `unsafe`.

### Testing Spectrum

Apply progressively stronger verification based on risk level:

| Level | Tool | Use When |
|---|---|---|
| Unit tests | `cargo test` | Every module, every PR |
| Lint | `cargo clippy -- -D warnings` | Every PR (block merge on warnings) |
| Property tests | `proptest` / `quickcheck` | Parsing, encoding, math-heavy logic |
| Fuzzing | `cargo-fuzz` / `bolero` | Parser boundaries, format handlers, FFI layers |
| Miri | `cargo +nightly miri test` | Any code using `unsafe` |
| Formal verification | Kani | Critical unsafe code, security-sensitive paths |

### Sanitizer Integration for Mixed C++/Rust Builds

When C++ and Rust coexist in the same binary:

1. Compile both with matching sanitizers (`-fsanitize=address` + `-Zsanitizer=address`).
2. Link against the same sanitizer runtime (compiler-rt).
3. If Rust initializes memory that C++ later reads, the C++ memory sanitizer must know the memory is valid. This requires instrumenting both sides.
4. Test the FFI boundary layer under sanitizers, not just each side independently.

### Dependency Auditing

1. Run `cargo audit` in CI to catch known vulnerabilities.
2. Run `cargo deny check` for license compliance and duplicate dependencies.
3. Review `cargo tree` output before accepting new crate dependencies.
4. Set a policy for maximum acceptable transitive dependency count.

## Incremental Rollout Gates

1. Roll out by module with fallback switches where practical.
2. Monitor runtime metrics for parity in production-like environments.
3. Remove fallback code only after stable parity windows.
4. Keep differential tests running until the C++ code path is fully decommissioned.
