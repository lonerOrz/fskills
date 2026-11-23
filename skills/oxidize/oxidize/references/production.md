# Production setup: workspace, tooling, CI, release

Set this up in **Phase 2, before writing logic**, so every commit passes through quality gates. Retrofitting
lint/CI onto an existing pile of code is painful and things rot in the gap.

Contents:
- Workspace layout
- Toolchain pinning (rust-toolchain, MSRV)
- Lint and format (clippy, rustfmt)
- Supply chain (cargo-deny, cargo-audit)
- Testing tooling (nextest, llvm-cov)
- CI
- Error handling and logging conventions
- Release and distribution

## Workspace layout

A migration usually produces several crates (the core logic, the FFI binding, maybe a CLI). Use a Cargo
**workspace** so they share a lock file, build cache, and lint config.

```
myproject/
├── Cargo.toml            # [workspace] — members + shared [workspace.dependencies]
├── rust-toolchain.toml   # pin the toolchain
├── deny.toml             # cargo-deny config
├── crates/
│   ├── core/             # pure, safe logic — no FFI, fully testable in isolation
│   │   ├── Cargo.toml
│   │   └── src/lib.rs
│   ├── bindings/         # thin FFI/pyo3/napi layer over core (the only place with unsafe/extern)
│   └── cli/              # optional binary front-end
└── .github/workflows/ci.yml
```
Root `Cargo.toml`:
```toml
[workspace]
resolver = "2"
members = ["crates/*"]

[workspace.dependencies]
serde = { version = "1", features = ["derive"] }
thiserror = "1"
# ... shared versions here; members write `serde.workspace = true`
```
**Keep `core` free of FFI and `unsafe`.** All the real logic lives there as ordinary safe Rust, testable
without any host language. The `bindings` crate is a thin adapter. This separation is what lets you unit
test, fuzz, and benchmark the logic directly, and swap the interop mechanism later.

See `assets/templates/` for copy-paste starting points (workspace `Cargo.toml`, `deny.toml`, CI yaml).

## Toolchain pinning (rust-toolchain, MSRV)

Pin the toolchain so every machine and CI uses the same compiler:
```toml
# rust-toolchain.toml
[toolchain]
channel = "1.83.0"          # or "stable"
components = ["clippy", "rustfmt"]
```
If you publish a library, decide a **Minimum Supported Rust Version (MSRV)**, set `rust-version` in
`Cargo.toml`, and test it in CI. For an internal service, pinning to recent stable is enough.

## Lint and format (clippy, rustfmt)

- `cargo fmt` — enforce formatting; add `rustfmt.toml` only if you need to deviate.
- `cargo clippy --all-targets --all-features -- -D warnings` — treat lints as errors in CI. Clippy catches
  a huge amount of un-idiomatic ported code (needless clones, manual loops that should be iterators,
  `unwrap` that should be `?`). During Phase 7 idiomatization, run it at `-W clippy::pedantic` and address
  what's worth addressing.
- Consider `#![deny(unsafe_code)]` on the `core` crate (allow it only in `bindings`) so `unsafe` can't
  sneak into your pure logic without a visible, deliberate exception.

## Supply chain (cargo-deny, cargo-audit)

- `cargo audit` — checks dependencies against the RustSec advisory DB for known vulnerabilities.
- `cargo deny check` — one tool for advisories **plus** license policy (block copyleft you can't ship),
  banned/duplicate crates, and untrusted sources. Configure in `deny.toml`. Run both in CI.

## Testing tooling (nextest, llvm-cov)

- `cargo nextest run` — faster, clearer test runner than `cargo test` (better output, parallelism,
  per-test isolation). Recommended for CI.
- `cargo llvm-cov` — coverage. Useful to confirm the ported module's branches are actually exercised by the
  differential corpus (see `verification.md`), not just that tests pass.

## CI

Minimum gates on every PR (see `assets/templates/ci.yml` for a ready GitHub Actions file):
1. `cargo fmt --check`
2. `cargo clippy --all-targets --all-features -- -D warnings`
3. `cargo nextest run` (or `cargo test`)
4. `cargo deny check` (+ `cargo audit`)

Cache the Cargo registry and `target/` (e.g. `Swatinem/rust-cache`) so CI stays fast. If you build FFI
artifacts (wheels, node addons, wasm), add a matrix job that builds them for the platforms you ship.

## Error handling and logging conventions

- Libraries return typed errors (`thiserror`); binaries use `anyhow` with `.context(...)`. See
  `translation-patterns.md`.
- Structured logging/tracing: use the `tracing` crate (spans + structured fields), not `println!`. It
  integrates with async and gives you production-grade observability — which you'll want during shadow and
  canary rollout to compare old vs new behavior.
- Configuration: `serde` + `figment`/`config` for layered config; `clap` (derive) for CLI args.

## Release and distribution

Depends on the artifact:
- **Service/binary:** build `--release`, ship a container or static musl binary (`x86_64-unknown-linux-musl`
  for a dependency-free binary). Strip symbols, consider LTO (`[profile.release] lto = true`) and
  `codegen-units = 1` for the last few percent of speed.
- **Python wheel:** `maturin build --release`; publish per-platform wheels (maturin's GitHub Action builds
  the matrix). See `interop.md`.
- **Node addon:** `napi build --release --platform`; publish per-platform optional-dependency packages.
- **wasm:** `wasm-pack build`; publish to npm or serve the `.wasm`.
- **Crate for other Rust:** `cargo publish` (after `cargo package` sanity check).

Turn on release profile optimizations deliberately and re-benchmark (`verification.md`) — a debug build can
be 10–100× slower and will make you think the migration failed.
