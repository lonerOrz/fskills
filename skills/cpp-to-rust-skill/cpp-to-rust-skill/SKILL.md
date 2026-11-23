---
name: cpp-to-rust-port
description: Use for systematic migration of C++ libraries (full or partial) to production-grade Rust. Trigger when users ask to port a C/C++ codebase, rewrite selected modules, replace pointer-heavy/OOP-heavy designs with ownership-based Rust APIs, preserve behavior and performance, design incremental FFI bridges, set up mixed C++/Rust build systems, port concurrent or template-heavy code, or enforce advanced semantic Rust patterns (traits, enums, typestate, error taxonomy, unsafe encapsulation, and concurrency correctness).
---

# C++ to Rust Porting Skill

Execute C++ to Rust migrations with a parity-first, safety-first workflow. Port only the required surface area unless the user explicitly asks for a full rewrite.

## Choose Porting Scope First

1. Identify the minimal required feature set.
2. Freeze behavior with tests before rewriting code.
3. Prefer incremental replacement with stable interfaces.
4. Keep C++ in place for low-priority paths until Rust equivalents are validated.
5. Never attempt a big-bang rewrite. Every successful large-scale migration (Google Android, Cloudflare Pingora, Meta mobile, ClickHouse) used incremental replacement.

Load [porting-playbook.md](./references/porting-playbook.md) for the full phase-by-phase workflow.

## Build a Parity Harness Before Porting

1. Add characterization tests around public APIs and important edge cases.
2. Add corpus/golden tests for binary formats and protocol behavior.
3. Add benchmarks for throughput, latency, allocations, and memory.
4. Add differential tests that run both C++ and Rust implementations on the same inputs and compare outputs.
5. Treat this harness as the migration gate; avoid semantic rewrites without baseline evidence.

Load [perf-and-parity.md](./references/perf-and-parity.md) for test gates, differential testing strategy, and sanitizer integration.

## Set Up the Mixed Build System

1. Pick one build system as the outer orchestrator (CMake, Bazel, or Cargo).
2. Integrate the other language's toolchain via plugin or subprocess (Corrosion for CMake, rules_rust for Bazel, cc/cmake crates for Cargo-primary).
3. Match debug/release profiles, sanitizer flags, and CRT linking modes across both languages.
4. Pin Rust toolchain version in `rust-toolchain.toml` and commit `Cargo.lock`.
5. Audit transitive dependencies with `cargo-audit` and `cargo-deny` before accepting new crates.

Load [build-system-integration.md](./references/build-system-integration.md) for CMake, Bazel, and Cargo integration recipes.

## Design Idiomatic Rust APIs, Not Line-by-Line Translations

1. Model invalid states as unrepresentable states using enums/newtypes.
2. Replace inheritance trees with traits and composition.
3. Replace nullable/raw ownership contracts with `Option<T>`, `Result<T, E>`, and explicit lifetimes.
4. Separate zero-copy read paths from owning transform paths.
5. Prefer domain errors over string errors.
6. Replace C++ move constructors with Rust's default move semantics (remove all `std::move()` calls).
7. Replace `dynamic_cast`/RTTI with enum dispatch or trait objects (avoid `Any` unless genuinely needed).
8. Replace C++ preprocessor macros with `const`, generic functions, or `#[cfg()]` attributes before reaching for `macro_rules!`.

Load [cpp-rust-pattern-map.md](./references/cpp-rust-pattern-map.md) for basic construct mapping.
Load [advanced-pattern-map.md](./references/advanced-pattern-map.md) for templates, RTTI, macros, move semantics, and anti-patterns.

## Port Concurrency Carefully

1. Redesign around Rust's `Send`/`Sync` ownership model rather than mimicking C++ shared-state patterns.
2. Prefer channels (`crossbeam::channel`, `mpsc`) over `Arc<Mutex<T>>` for thread communication.
3. Map C++ thread pools to Rayon (data-parallel) or Crossbeam (scoped threads).
4. Map C++20 coroutines to Rust `async`/`await` with a single runtime (Tokio by default). Do not mix runtimes.
5. Never hold a `std::sync::MutexGuard` across an `.await` point. Use `tokio::sync::Mutex` in async code.
6. Do not expose Rust futures across FFI. Use blocking wrappers or callback APIs at the boundary.

Load [concurrency-porting.md](./references/concurrency-porting.md) for the full concurrency pattern map.

## Port in Vertical Slices

1. Port one subsystem end-to-end (data model, parser/logic, API boundary, tests).
2. Keep each slice releasable and benchmarked.
3. Avoid giant single-PR rewrites.
4. Remove dead C++ code only after Rust parity gates pass.

## Contain `unsafe` and FFI

1. Keep `unsafe` localized behind safe Rust APIs.
2. Document invariants above every `unsafe` block with `// SAFETY:` comments.
3. Catch panics at every FFI entry point with `std::panic::catch_unwind`. Unwinding across FFI is undefined behavior.
4. Define ownership transfer explicitly for every cross-language pointer.
5. Use `#[repr(C)]` on all types shared across FFI. Never pass `Vec`, `String`, or `Box` directly.
6. Handle platform-specific linking (stdc++ on Linux, c++ on macOS, MSVCRT on Windows).
7. Use FFI only as a transition seam, not a permanent architecture default.

Load [ffi-and-unsafe-boundaries.md](./references/ffi-and-unsafe-boundaries.md) for boundary rules, ABI details, and platform linking.

## Avoid Known Anti-Patterns

1. **Do not wrap everything in `Arc<Mutex<T>>`** to silence the borrow checker. Redesign ownership instead.
2. **Do not use `Rc<RefCell<T>>` as a crutch.** It moves safety checks from compile time to runtime panics.
3. **Do not translate C++ class hierarchies 1:1.** Flatten to enums or composition.
4. **Do not clone excessively.** Use borrows, `Cow`, and slices at API boundaries.
5. **Do not ignore dependency count.** Audit transitive dependencies before accepting new crates.

Load [advanced-pattern-map.md](./references/advanced-pattern-map.md) for the full anti-patterns catalog.

## Avoid Performance Traps

1. Always benchmark in `--release` mode. Debug Rust is 10-100x slower due to unoptimized iterators.
2. Watch for excessive `.clone()` calls — each one is a hidden heap allocation.
3. Box large enum variants to prevent size bloat across all variants.
4. Use iterators instead of indexed loops to avoid bounds-checking overhead.
5. Batch FFI calls to avoid per-call overhead (4x for simple types, negligible for bulk data).
6. Match global allocator to the C++ version if allocation behavior matters (jemalloc, tcmalloc).
7. Validate UTF-8 once at the FFI boundary, not on every string conversion.

Load [performance-traps.md](./references/performance-traps.md) for the full performance trap catalog.

## Apply Advanced Semantic Rust Patterns

1. Use typestate or sealed constructors to enforce protocol/state transitions.
2. Use trait-based extension points instead of virtual class hierarchies.
3. Use enum-driven dispatch for finite strategy sets.
4. Use `Arc`, channels, and task boundaries for concurrency with explicit ownership.
5. Use `Cow`, slices, and iterator pipelines for low-allocation data flow.
6. Use `#[non_exhaustive]` and forward-compatible error enums for stable public APIs.

## Define Completion Gates

1. Functional parity: all characterization, differential, and new Rust tests pass.
2. Safety parity: `unsafe` blocks are minimal, documented, and reviewed. Miri passes on unsafe code.
3. Performance parity: no regressions beyond agreed thresholds. Benchmarked in release mode with Criterion.
4. Operability parity: logging, metrics, and error observability preserved.
5. Maintenance parity: public Rust APIs are documented and idiomatic.
6. Supply chain: dependencies audited with `cargo-audit` and `cargo-deny`.
7. Build system: mixed build compiles cleanly with matching sanitizer and profile flags.

## Use References Intentionally

1. Load [porting-playbook.md](./references/porting-playbook.md) for migration sequencing and deliverables.
2. Load [cpp-rust-pattern-map.md](./references/cpp-rust-pattern-map.md) for basic construct-level translation.
3. Load [advanced-pattern-map.md](./references/advanced-pattern-map.md) for templates, RTTI, macros, move semantics, and anti-patterns.
4. Load [ffi-and-unsafe-boundaries.md](./references/ffi-and-unsafe-boundaries.md) for FFI safety, ABI, and platform linking.
5. Load [concurrency-porting.md](./references/concurrency-porting.md) for thread, async, and atomics porting.
6. Load [build-system-integration.md](./references/build-system-integration.md) for CMake, Bazel, and Cargo integration.
7. Load [performance-traps.md](./references/performance-traps.md) for Rust-specific performance pitfalls.
8. Load [perf-and-parity.md](./references/perf-and-parity.md) for test/bench gating and differential testing.
9. Load [sources.md](./references/sources.md) for canonical language, tooling, and case study references.
