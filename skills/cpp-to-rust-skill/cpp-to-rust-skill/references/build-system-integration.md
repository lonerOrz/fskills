# Build System Integration

Use this reference when C++ and Rust must coexist in the same build graph.

## Pick One Orchestrator

Use a single build system as the outer driver. Invoke the other language's toolchain as a subprocess or plugin.

| Outer Build System | Rust Integration | Maturity |
|---|---|---|
| CMake | Corrosion (`corrosion-rs/corrosion`) | Production-ready |
| Bazel | `rules_rust` + Crate Universe | Production-ready |
| Meson | Native Rust module support | Usable, smaller community |
| GN (Chromium) | Built-in Rust target type | Chromium-specific |
| Cargo-only | `build.rs` invokes `cc`/`cmake` crate | Works for Rust-primary projects |

## CMake + Cargo via Corrosion

Corrosion is the most mature bridge. It invokes Cargo from CMake with proper target directories and flag propagation.

```cmake
include(FetchContent)
FetchContent_Declare(
    Corrosion
    GIT_REPOSITORY https://github.com/corrosion-rs/corrosion.git
    GIT_TAG v0.5
)
FetchContent_MakeAvailable(Corrosion)

corrosion_import_crate(MANIFEST_PATH rust/Cargo.toml)
target_link_libraries(my_cpp_target PRIVATE my_rust_crate)
```

### Gotchas

1. Platform-dependent C++ stdlib linking. Add to `build.rs`:

```rust
#[cfg(target_os = "macos")]
println!("cargo:rustc-link-lib=dylib=c++");
#[cfg(target_os = "linux")]
println!("cargo:rustc-link-lib=dylib=stdc++");
```

2. CMake's built-in Rust support is limited. Prefer Corrosion over `ExternalProject_Add`.
3. Debug/release profile mismatches between CMake and Cargo cause linker errors. Ensure both use the same optimization level.

## Bazel + rules_rust

```starlark
load("@rules_rust//rust:defs.bzl", "rust_library")

rust_library(
    name = "my_rust_lib",
    srcs = ["src/lib.rs"],
    deps = ["@crate_index//:serde"],
)

cc_binary(
    name = "my_cpp_app",
    srcs = ["main.cpp"],
    deps = [":my_rust_lib"],
)
```

### Gotchas

1. Use Crate Universe to import external crates as Bazel targets.
2. `cargo_build_script` rule handles `build.rs` scripts.
3. bzlmod support is still maturing; bugs are more likely in that mode.
4. CXX maintains working Bazel BUILD targets tested in CI.

## Cargo-Primary with build.rs

When Rust owns the build and links C++ as a dependency:

```rust
// build.rs
fn main() {
    cc::Build::new()
        .cpp(true)
        .file("src/legacy.cpp")
        .include("include")
        .flag_if_supported("-std=c++17")
        .compile("legacy");
}
```

For complex C++ builds, use the `cmake` crate:

```rust
// build.rs
fn main() {
    let dst = cmake::Config::new("cpp_project")
        .define("BUILD_SHARED_LIBS", "OFF")
        .build();
    println!("cargo:rustc-link-search=native={}/lib", dst.display());
    println!("cargo:rustc-link-lib=static=mylib");
}
```

## Crate Type Selection

| crate-type | Use Case |
|---|---|
| `staticlib` | Link Rust into C/C++ binary as a static archive |
| `cdylib` | Produce a C-compatible shared library (.so/.dylib/.dll) |
| `rlib` | Default Rust library (Rust-to-Rust only) |
| `lib` | Cargo decides (usually rlib) |

For FFI consumption, set in `Cargo.toml`:

```toml
[lib]
crate-type = ["staticlib", "cdylib"]
```

## Sanitizer Integration in Mixed Builds

When C++ and Rust coexist, both must be compiled with sanitizers. If Rust initializes memory that C++ later reads, the C++ memory sanitizer must know the memory is valid.

1. Pass `-Zsanitizer=address` to rustc alongside `-fsanitize=address` in CFLAGS/CXXFLAGS.
2. Link against the same sanitizer runtime (compiler-rt vs libasan).
3. Test the boundary layer under sanitizers, not just each side independently.

## Reproducible Builds

1. Pin Rust toolchain version in `rust-toolchain.toml`.
2. Use `Cargo.lock` in version control for applications (not libraries).
3. Vendor dependencies with `cargo vendor` for air-gapped or deterministic builds.
4. Audit transitive dependencies with `cargo-audit` and `cargo-deny`.
