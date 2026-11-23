# Interop: calling Rust from the source language

Read only the section for the source language you're migrating from. Each section covers the recommended
tool, a minimal working example, how data crosses the boundary, and the sharp edges.

Contents:
- General rules of the boundary
- Python (PyO3 + maturin)
- Node.js / JavaScript / TypeScript (napi-rs; wasm alternative)
- C (bindgen / cbindgen)
- C++ (cxx; bindgen for C-style APIs)
- Java / JVM (jni crate)
- Ruby (magnus)
- C# / .NET (C ABI + csbindgen / P/Invoke)
- Go (C ABI via cgo, or a service boundary)
- WebAssembly (wasm-bindgen / wasm-pack; universal boundary)

## General rules of the boundary

These apply no matter the language.

- **Make the boundary coarse.** Each crossing has a cost (marshalling, copying, sometimes a lock). Cross
  once with a batch, not N times in a loop. If the host calls your Rust function a million times with a
  scalar, you'll lose to the boundary overhead — redesign so Rust receives the whole workload.
- **Own your memory across the boundary carefully.** Every allocation that crosses must have a clear owner
  and a defined free path. Prefer having each side own what it allocates. Most binding frameworks
  (PyO3, napi-rs, magnus, cxx) handle this for you — lean on them instead of raw pointers.
- **Never let a Rust panic unwind across the FFI boundary** — it's undefined behavior. Convert errors to
  the host language's error type at the edge. Framework macros do this; for raw `extern "C"` functions,
  wrap the body in `std::panic::catch_unwind` and return an error code.
- **Expose a thin `extern` surface, keep a fat safe core.** Write your real logic as ordinary safe Rust,
  and add a thin binding layer on top. Don't scatter `unsafe`/`extern` through the codebase.

## Python (PyO3 + maturin)

The standard path. `pyo3` provides the bindings; `maturin` builds and packages them as a wheel.

`Cargo.toml`:
```toml
[lib]
name = "myrust"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"] }
```

`src/lib.rs`:
```rust
use pyo3::prelude::*;

/// A coarse-grained function: hand it the whole workload, not one item at a time.
#[pyfunction]
fn sum_squares(values: Vec<f64>) -> f64 {
    values.iter().map(|x| x * x).sum()
}

#[pymodule]
fn myrust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_squares, m)?)?;
    Ok(())
}
```

Build & use:
```bash
pip install maturin
maturin develop --release   # builds and installs into the current venv
python -c "import myrust; print(myrust.sum_squares([1,2,3]))"
```

Sharp edges:
- **The GIL.** PyO3 functions hold the GIL by default. For CPU-bound parallel work, release it with
  `Python::allow_threads` so other Python threads can run while Rust computes.
- **NumPy interop:** use the `numpy` crate to receive `PyReadonlyArray` zero-copy instead of copying lists.
- **Errors:** return `PyResult<T>`; map Rust errors to Python exceptions via `PyErr`. Panics are converted
  to exceptions by PyO3, but prefer explicit `Result`.

## Node.js / JavaScript / TypeScript (napi-rs)

`napi-rs` produces a native Node addon and generates TypeScript types automatically. Preferred over the
older `neon` for new work.

```rust
use napi_derive::napi;

#[napi]
pub fn sum_squares(values: Vec<f64>) -> f64 {
    values.iter().map(|x| x * x).sum()
}
```
Scaffold with `npm init napi`, build with `napi build --release`. It emits `index.d.ts` so TS callers get
types for free.

Sharp edges:
- Node is single-threaded; for CPU-bound work use napi's `AsyncTask` / threadsafe functions to run on a
  worker thread and not block the event loop.
- Async Rust integrates with JS promises via `#[napi]` on `async fn` (with the `tokio_rt` feature).

**Alternative — wasm:** if you want one artifact that runs in the browser *and* Node, compile to wasm
(see the WebAssembly section) instead of a native addon.

## C (bindgen / cbindgen)

Two directions, two tools:
- **Rust calling C** (wrapping an existing C lib you're not ready to replace): `bindgen` generates Rust
  FFI declarations from C headers.
- **C calling Rust** (exposing your new Rust to remaining C code): write `#[no_mangle] pub extern "C"`
  functions, and use `cbindgen` to generate a C header for them.

```rust
#[no_mangle]
pub extern "C" fn sum_squares(ptr: *const f64, len: usize) -> f64 {
    // Wrap the whole body so a panic can't unwind into C (that's UB).
    std::panic::catch_unwind(|| {
        let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
        slice.iter().map(|x| x * x).sum()
    })
    .unwrap_or(f64::NAN)
}
```
Set `crate-type = ["staticlib"]` or `["cdylib"]`. Define ownership rules explicitly: who allocates, who
frees, and document them in the generated header.

## C++ (cxx)

For C++, prefer `cxx`: it defines a shared, checked interface in a Rust module and generates safe glue for
both sides, avoiding hand-written `unsafe` for common patterns (strings, vectors, shared/unique pointers).

```rust
#[cxx::bridge]
mod ffi {
    extern "Rust" {
        fn sum_squares(values: &[f64]) -> f64;
    }
}

fn sum_squares(values: &[f64]) -> f64 {
    values.iter().map(|x| x * x).sum()
}
```
`cxx` handles `std::string`/`String`, `std::vector`/`Vec`, `std::unique_ptr`, and shared references
across the boundary with compile-time checks. For plain C-style C++ APIs, `bindgen` also works. For
mechanically transpiling C to (unsafe) Rust as a starting point, `c2rust` exists — but its output is
unidiomatic and unsafe; treat it as scaffolding to rewrite, not a finish line.

## Java / JVM (jni crate)

Use the `jni` crate to implement `native` methods. Declare `native` methods in Java, implement matching
`Java_<class>_<method>` `extern "system"` functions in Rust.

```rust
use jni::JNIEnv;
use jni::objects::JClass;
use jni::sys::jdouble;

#[no_mangle]
pub extern "system" fn Java_com_example_Native_squared(
    _env: JNIEnv, _class: JClass, x: jdouble,
) -> jdouble {
    x * x
}
```
Sharp edges: JNI signatures are verbose and error-prone; keep the JNI layer thin and delegate to plain
Rust immediately. Loading: `System.loadLibrary` from Java. For richer needs, look at `jni` helpers for
converting Java collections/strings.

## Ruby (magnus)

`magnus` is the modern binding crate (supersedes `rutie` for new work).

```rust
use magnus::{function, prelude::*, Error, Ruby};

fn sum_squares(values: Vec<f64>) -> f64 {
    values.iter().map(|x| x * x).sum()
}

#[magnus::init]
fn init(ruby: &Ruby) -> Result<(), Error> {
    let module = ruby.define_module("MyRust")?;
    module.define_singleton_method("sum_squares", function!(sum_squares, 1))?;
    Ok(())
}
```
Package as a gem with `rb-sys` + `rake-compiler`.

## C# / .NET (C ABI + csbindgen / P/Invoke)

Expose a C ABI from Rust (as in the C section) and call it from C# with `[DllImport]`/P/Invoke.
`csbindgen` can auto-generate the C# `DllImport` bindings from your Rust `extern "C"` functions, saving
the hand-marshalling.

## Go (C ABI via cgo, or a service boundary)

Go's FFI story is weaker: you cross via the C ABI using cgo. Build Rust as a C-compatible library
(`crate-type = ["staticlib"]` or `["cdylib"]`), expose `extern "C"` functions, and call them from Go via
`import "C"`. Be aware cgo calls have non-trivial overhead and complicate Go's scheduler/GC — keep the
boundary coarse. For many Go systems, a **strangler service boundary** (a small Rust service the Go app
calls over the network/gRPC) is cleaner than in-process cgo.

## WebAssembly (wasm-bindgen / wasm-pack)

The universal boundary: compile Rust to wasm and call it from JS (browser or Node), or from Python
(`wasmtime`), etc.

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn sum_squares(values: &[f64]) -> f64 {
    values.iter().map(|x| x * x).sum()
}
```
Build with `wasm-pack build --target web` (or `--target nodejs`/`bundler`). Sharp edges: wasm can't do
arbitrary syscalls (use WASI for a subset), threads need special setup, and everything crossing the
boundary is copied — keep payloads coarse and avoid chatty calls.
