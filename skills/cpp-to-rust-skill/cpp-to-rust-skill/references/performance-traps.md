# Performance Traps in Ported Rust Code

Use this reference to avoid Rust patterns that silently degrade performance compared to the C++ original. These are the traps that pass correctness tests but fail benchmarks.

## Trap 1: Excessive Cloning

The most common performance anti-pattern in ported code. New Rust developers call `.clone()` or `.to_owned()` to satisfy the borrow checker. Each clone of a heap type (`Vec`, `String`, `HashMap`) triggers a new allocation and copy.

### Detection

```bash
# Count clone calls in the codebase
grep -rn '\.clone()' src/ | wc -l
```

Review every `.clone()` call. Ask: is this clone structurally necessary or am I avoiding a borrow redesign?

### Fixes

| Instead of | Use | When |
|---|---|---|
| `fn process(s: String)` | `fn process(s: &str)` | Function only reads the data |
| `data.clone()` passed to branch | `Cow<'a, T>` | Ownership needed only on some paths |
| `vec.clone()` for iteration | `&vec` or `vec.iter()` | Iteration does not need ownership |
| `map.get(key).cloned()` | `map.get(key)` and borrow | When the value is used briefly |
| Cloning into closures | `&` references or `Arc` for shared read access | Closures that outlive the borrow scope |

### Guideline

Use `&str` instead of `&String`, `&[T]` instead of `&Vec<T>`, and `&Path` instead of `&PathBuf` at API boundaries. Accept borrowed forms; let callers decide on ownership.

## Trap 2: Debug-Mode Iterator Overhead

Rust iterators are zero-cost in release mode (LLVM inlines and optimizes them). In debug mode, iterators are NOT inlined and carry significant overhead — often 10-100x slower than equivalent C++ loops.

### Impact

Benchmark comparisons run in debug mode are misleading. Always benchmark in release mode.

### Fix

For development builds where performance matters (integration tests, large data processing):

```toml
# Cargo.toml
[profile.dev]
opt-level = 1  # Basic optimization, keeps debug info

[profile.dev.package."*"]
opt-level = 2  # Optimize dependencies fully even in dev
```

## Trap 3: Enum Size Bloat

Rust enums carry a discriminant tag. All variants occupy the size of the largest variant.

```rust
// This enum is 24 bytes because of LargeVariant
enum Message {
    Ping,                           // 0 bytes payload
    Text(String),                   // 24 bytes payload
    LargeVariant([u8; 1024]),       // 1024 bytes payload  <-- inflates ALL variants
}
// sizeof Message = 1024 + discriminant
```

### Niche Optimization

The compiler uses invalid bit patterns to eliminate discriminants:

| Type | Size | Why |
|---|---|---|
| `Option<&T>` | 8 bytes | Null pointer used as `None` discriminant |
| `Option<NonZeroUsize>` | 8 bytes | Zero used as `None` discriminant |
| `Option<bool>` | 1 byte | Uses unused bit patterns |
| `Option<usize>` | 16 bytes | No niche available — discriminant added |

### Fix

Box large variants to keep the enum small:

```rust
enum Message {
    Ping,
    Text(String),
    LargeVariant(Box<[u8; 1024]>),  // Now 8 bytes (pointer)
}
// sizeof Message = 24 + discriminant
```

## Trap 4: Bounds Checking in Hot Loops

Rust performs bounds checking on every `slice[index]` access. In tight inner loops over large arrays, this is measurable (5-15% overhead vs unchecked C++ access).

### Fixes (in order of preference)

1. **Use iterators** — they avoid bounds checks entirely:

```rust
// BAD: bounds check on every access
for i in 0..data.len() {
    sum += data[i];
}

// GOOD: no bounds checks
for val in &data {
    sum += val;
}

// GOOD: iterator adapters also avoid bounds checks
let sum: u64 = data.iter().sum();
```

2. **Use `get_unchecked()` in verified unsafe blocks** (last resort):

```rust
// SAFETY: loop bound ensures i < data.len()
unsafe { sum += *data.get_unchecked(i); }
```

3. **Assert the bound once, then use a subslice**:

```rust
assert!(end <= data.len());
let window = &data[start..end];  // bounds checked once
for val in window {               // no further checks
    sum += val;
}
```

## Trap 5: FFI Call Overhead

CXX bridge overhead varies by operation type:

| Operation | Overhead vs native | Notes |
|---|---|---|
| Simple int pass/return | ~4x | Significant for high-frequency calls |
| String processing | ~1.3x | Moderate |
| Vector/bulk data | ~1.05x | Negligible |

### Fix

1. **Batch FFI calls.** Pass a slice of 1000 items instead of making 1000 individual calls.
2. **Move data in bulk.** Transfer ownership of large buffers across the boundary instead of copying elements.
3. **Minimize boundary crossings.** Do as much work as possible on one side before crossing.
4. **Profile the boundary.** Use `perf`/`instruments` to identify if FFI overhead is actually the bottleneck before optimizing.

## Trap 6: Allocation Pattern Differences

### Vec Growth Strategy

Rust's `Vec` doubles capacity on reallocation (same as most `std::vector` implementations), but the exact growth factor and initial capacity may differ from your C++ platform.

### Fix

Pre-allocate when the size is known:

```rust
let mut buf = Vec::with_capacity(expected_size);
```

### Global Allocator

Rust uses the system allocator by default. If the C++ code relied on jemalloc or tcmalloc, switch explicitly:

```rust
// Cargo.toml
[dependencies]
tikv-jemallocator = "0.6"

// main.rs or lib.rs
#[global_allocator]
static GLOBAL: tikv_jemalloc::Jemalloc = tikv_jemalloc::Jemalloc;
```

### Box vs Stack

`Box<T>` always heap-allocates. C++ compilers sometimes elide `new` via NRVO (Named Return Value Optimization). Rust also has NRVO but does not guarantee it. Profile if heap allocation frequency is higher than expected.

## Trap 7: String Handling

C++ `std::string` is not necessarily UTF-8. Rust `String` is always valid UTF-8, and conversions from raw bytes (`&[u8]` to `&str`) require validation.

### Impact

UTF-8 validation on every conversion from C++ strings is an O(n) cost that did not exist in the C++ version.

### Fix

1. Use `String::from_utf8_unchecked` in unsafe blocks when the C++ side guarantees UTF-8 encoding.
2. Use `&[u8]` / `Vec<u8>` for binary data that is not text.
3. Use `OsStr`/`OsString` for filesystem paths and platform strings.
4. Avoid repeated validation — validate once at the FFI boundary, then use `&str` internally.

## Performance Verification Checklist

1. Always benchmark in `--release` mode. Never compare debug Rust vs optimized C++.
2. Use Criterion for statistical significance: `cargo bench` with `criterion` crate.
3. Profile allocations with DHAT (`--features dhat-heap`) or `jemalloc` stats.
4. Profile CPU with `perf record` (Linux) or Instruments (macOS).
5. Compare peak RSS (resident set size) between C++ and Rust versions.
6. Check for unexpected allocations with `#[global_allocator]` counting wrappers.
