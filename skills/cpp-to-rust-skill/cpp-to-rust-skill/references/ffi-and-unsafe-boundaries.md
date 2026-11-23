# FFI and Unsafe Boundaries

Use this reference when incremental migration requires C++ and Rust to coexist.

## Boundary Rules

1. Keep FFI interfaces narrow and versioned.
2. Avoid exposing Rust-specific types directly over C ABI boundaries.
3. Use `#[repr(C)]` for shared structs and document layout assumptions.
4. Guarantee no Rust panic crosses FFI; convert to explicit error codes/results.
5. Define ownership transfer rules for every pointer argument and return value.

## Unsafe Containment Strategy

1. Place all raw-pointer and FFI interaction in dedicated boundary modules.
2. Provide safe wrappers with validated preconditions.
3. Add `// SAFETY:` comments for each unsafe block with concrete invariants.
4. Unit test wrappers with valid and invalid input shapes.

## Interop Transition Patterns

1. Keep existing C++ API stable while swapping implementation internals to Rust.
2. Use adapter layers to translate C++ structures into Rust domain types.
3. Decommission adapter paths once native Rust callers are available.

## ABI and Linking

### Symbol Mangling

- Rust's default mangling scheme is unstable and changes between compiler versions.
- For FFI, always use `extern "C"` + `#[no_mangle]` to produce C-compatible symbols.
- In the 2024 edition, `#[no_mangle]` requires `unsafe` qualification: `unsafe extern "C" fn`.

### Rust Has No Stable ABI

Every compiler version can change struct layout, vtable format, and calling conventions. For cross-language shared types:

1. Always use `#[repr(C)]` on structs and enums shared across FFI.
2. Use `#[repr(transparent)]` for single-field wrapper types.
3. Never pass Rust-specific types (`Vec`, `String`, `Box`) directly across FFI. Convert to C-compatible representations (`*const T`, `*mut c_char`, raw pointers + length).

### Platform-Specific Linking

| Platform | C++ stdlib | Link flag in build.rs |
|---|---|---|
| Linux (GCC) | libstdc++ | `cargo:rustc-link-lib=dylib=stdc++` |
| macOS (Clang) | libc++ | `cargo:rustc-link-lib=dylib=c++` |
| Windows (MSVC) | MSVCRT | Linked automatically; match `/MT` vs `/MD` CRT mode |

When both static and dynamic libraries exist in the same directory, the linker prefers the dynamic library. Use `-Clink-arg=-Bstatic` to force static linking on Linux.

### CRT Mode Matching (Windows)

C++ and Rust code linked into the same binary must use the same CRT linking mode:
- `/MT` (static CRT) = `+crt-static` in Rust
- `/MD` (dynamic CRT) = default Rust on MSVC

Mismatches cause linker errors or runtime crashes from heap mismatch.

### Panic Handling Across FFI

Unwinding across FFI boundaries is undefined behavior. Every Rust function callable from C/C++ must catch panics:

```rust
#[no_mangle]
pub extern "C" fn my_ffi_function(input: *const u8) -> i32 {
    match std::panic::catch_unwind(|| {
        // actual logic here
        0
    }) {
        Ok(result) => result,
        Err(_) => -1,  // return error code on panic
    }
}
```

Set `panic = "abort"` in release profile if no recovery is needed:

```toml
[profile.release]
panic = "abort"
```

## Review Checklist

1. Is every `unsafe` block justified and localized?
2. Are aliasing, lifetime, and thread-safety assumptions documented?
3. Are FFI inputs validated before dereference?
4. Is unwinding behavior defined and tested?
5. Are all shared types `#[repr(C)]`?
6. Is platform-specific linking handled in `build.rs`?
7. Are panics caught at every FFI entry point?
8. Is the CRT mode consistent across C++ and Rust (Windows)?
