# Sources

Last updated: 2026-02-27

## Rust language and ecosystem

- The Rust Programming Language (book): [doc.rust-lang.org/book](https://doc.rust-lang.org/book/)
- Rust API Guidelines: [rust-lang.github.io/api-guidelines](https://rust-lang.github.io/api-guidelines/)
- Rustonomicon (unsafe Rust): [doc.rust-lang.org/nomicon](https://doc.rust-lang.org/nomicon/)
- Rust reference: [doc.rust-lang.org/reference](https://doc.rust-lang.org/reference/)
- Rust Atomics and Locks (Mara Bos, O'Reilly 2023): [marabos.nl/atomics](https://marabos.nl/atomics/)
- Rust Performance Book: [nnethercote.github.io/perf-book](https://nnethercote.github.io/perf-book/)
- Effective Rust: [lurklurk.org/effective-rust](https://lurklurk.org/effective-rust/)

## C++ to Rust interop and migration tooling

- cxx (safe bidirectional C++/Rust interop): [github.com/dtolnay/cxx](https://github.com/dtolnay/cxx)
- autocxx (auto-generate safe CXX wrappers from C++ headers): [github.com/google/autocxx](https://github.com/google/autocxx)
- bindgen (generate Rust FFI bindings from C/C++ headers): [github.com/rust-lang/rust-bindgen](https://github.com/rust-lang/rust-bindgen)
- cbindgen (generate C/C++ headers from Rust): [github.com/mozilla/cbindgen](https://github.com/mozilla/cbindgen)
- C2Rust (transpile C to Rust, C99 only): [github.com/immunant/c2rust](https://github.com/immunant/c2rust)
- Crubit (Google, bidirectional bindings, experimental): [github.com/google/crubit](https://github.com/google/crubit)
- Diplomat (IDL-based multi-language FFI from Rust): [github.com/rust-diplomat/diplomat](https://github.com/rust-diplomat/diplomat)
- cargo-c (build Rust as C-compatible library): [github.com/nickel-org/cargo-c](https://github.com/nickel-org/cargo-c)

## Build system integration

- Corrosion (CMake + Cargo bridge): [github.com/corrosion-rs/corrosion](https://github.com/corrosion-rs/corrosion)
- rules_rust (Bazel Rust integration): [bazelbuild.github.io/rules_rust](https://bazelbuild.github.io/rules_rust/)
- cc crate (compile C/C++ from build.rs): [docs.rs/cc](https://docs.rs/cc/)
- cmake crate (invoke CMake from build.rs): [docs.rs/cmake](https://docs.rs/cmake/)

## Quality, verification, and testing

- cargo-fuzz (coverage-guided fuzzing): [rust-fuzz.github.io/book/cargo-fuzz.html](https://rust-fuzz.github.io/book/cargo-fuzz.html)
- Criterion (statistical benchmarks): [bheisler.github.io/criterion.rs/book](https://bheisler.github.io/criterion.rs/book/)
- proptest (property-based testing): [github.com/proptest-rs/proptest](https://github.com/proptest-rs/proptest)
- Bolero (unified fuzz + property test + verification): [github.com/camshaft/bolero](https://github.com/camshaft/bolero)
- Miri (detect UB in unsafe code via interpretation): [github.com/rust-lang/miri](https://github.com/rust-lang/miri)
- Kani (AWS, formal verification / model checking): [github.com/model-checking/kani](https://github.com/model-checking/kani)
- Rudra (fast static analysis for memory safety bugs): [github.com/sslab-gatech/Rudra](https://github.com/sslab-gatech/Rudra)
- cargo-careful (extra UB checks): [github.com/RalfJung/cargo-careful](https://github.com/RalfJung/cargo-careful)

## Supply chain and dependency management

- cargo-audit (vulnerability scanning): [github.com/rustsec/rustsec](https://github.com/rustsec/rustsec)
- cargo-deny (license + dependency checking): [github.com/EmbarkStudios/cargo-deny](https://github.com/EmbarkStudios/cargo-deny)

## Concurrency crates

- Rayon (data-parallel, work-stealing): [github.com/rayon-rs/rayon](https://github.com/rayon-rs/rayon)
- Crossbeam (scoped threads, channels, epoch GC): [github.com/crossbeam-rs/crossbeam](https://github.com/crossbeam-rs/crossbeam)
- Tokio (async runtime): [tokio.rs](https://tokio.rs/)

## Interoperability initiative

- Rust Foundation C++/Rust Interop Initiative: [rustfoundation.org/interop-initiative](https://rustfoundation.org/interop-initiative/)
- C++/Rust Interoperability Problem Statement: [github.com/rustfoundation/interop-initiative](https://github.com/rustfoundation/interop-initiative/blob/main/problem-statement.md)

## Real-world migration case studies

- Google Android Rust adoption: [security.googleblog.com (Nov 2025)](https://security.googleblog.com/2025/11/rust-in-android-move-fast-fix-things.html)
- Chromium Rust/C++ interop: [chromium.org/memory-safety](https://www.chromium.org/Home/chromium-security/memory-safety/rust-and-c-interoperability/)
- Cloudflare Pingora: [github.com/cloudflare/pingora](https://github.com/cloudflare/pingora)
- Meta C to Rust on mobile: [engineering.fb.com (Jul 2025)](https://engineering.fb.com/2025/07/01/developer-tools/an-inside-look-at-metas-transition-from-c-to-rust-on-mobile/)
- ClickHouse Rust integration: [clickhouse.com/blog/rust](https://clickhouse.com/blog/rust)
- Mozilla Stylo (integrating Rust in Firefox): [manishearth.github.io](https://manishearth.github.io/blog/2021/02/22/integrating-rust-and-c-plus-plus-in-firefox/)

## Skill ecosystem references

- OpenAI skills examples: [openai/skills](https://github.com/openai/skills)
