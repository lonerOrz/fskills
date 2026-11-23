# Advanced C++ to Rust Pattern Map

Use this reference for hard-to-port C++ constructs: templates, RTTI, macros, move semantics, and common anti-patterns. This extends `cpp-rust-pattern-map.md` with principal-engineer-level patterns.

## Template Metaprogramming

### CRTP (Curiously Recurring Template Pattern)

C++:
```cpp
template <typename Derived>
struct Base {
    void interface() { static_cast<Derived*>(this)->implementation(); }
};
struct Concrete : Base<Concrete> {
    void implementation() { /* ... */ }
};
```

Rust: Use trait default methods. Rust traits already have `Self` — CRTP is unnecessary.
```rust
trait Interface {
    fn implementation(&self);
    fn interface(&self) { self.implementation(); }  // default method calls Self
}
struct Concrete;
impl Interface for Concrete {
    fn implementation(&self) { /* ... */ }
}
```

**Key insight**: Do NOT force CRTP into Rust. The trait system already provides what CRTP exists to achieve in C++.

### SFINAE / enable_if / C++20 Concepts

C++:
```cpp
template <typename T>
    requires std::integral<T>
T double_it(T val) { return val * 2; }
```

Rust: Trait bounds and where clauses.
```rust
fn double_it<T: std::ops::Mul<Output = T> + From<u8>>(val: T) -> T {
    val * T::from(2)
}
// Or with num crate:
fn double_it<T: num::Integer + Copy>(val: T) -> T {
    val + val
}
```

C++20 Concepts map closely to Rust trait bounds. Rust produces clearer error messages because traits are explicitly declared rather than duck-typed.

### Variadic Templates

C++:
```cpp
template <typename... Args>
void log(Args&&... args) { (std::cout << ... << args); }
```

Rust has NO variadic generics (RFC #376 is still open as of 2026). Workarounds:

| Approach | Use Case |
|---|---|
| `macro_rules!` | Fixed repetitive patterns (like `println!`) |
| Procedural macros | Complex code generation |
| Tuple impls (up to fixed arity) | Standard library approach (implement for (A,), (A,B), etc.) |
| `frunk::HList` | Heterogeneous lists with type-level programming |

```rust
macro_rules! log {
    ($($arg:expr),*) => {
        $(print!("{}", $arg);)*
        println!();
    }
}
```

### Expression Templates

No direct Rust equivalent. C++ expression templates use template recursion to build lazy ASTs that evaluate without temporaries.

**Rust alternatives:**
1. Operator overloading returning lazy wrapper types (similar approach, more verbose).
2. Procedural macros that generate optimized expressions at compile time.
3. Const generics for compile-time computation (limited but growing).

**Guideline**: If the C++ codebase uses expression templates for performance (e.g., linear algebra), consider wrapping an existing Rust SIMD/linalg crate (`nalgebra`, `ndarray`) rather than porting the expression template machinery.

### Template Specialization

C++:
```cpp
template <typename T> struct Serializer { /* generic */ };
template <> struct Serializer<std::string> { /* specialized */ };
```

Rust: Full specialization is unstable. Workarounds:

1. **Separate trait impls** — Implement the trait differently for each type.
2. **Sealed traits** — Use a private module to control who can implement a trait.
3. **Newtype wrappers** — Wrap the type to provide a different impl.

```rust
trait Serialize {
    fn serialize(&self) -> Vec<u8>;
}
impl Serialize for String {
    fn serialize(&self) -> Vec<u8> { self.as_bytes().to_vec() }
}
impl Serialize for u64 {
    fn serialize(&self) -> Vec<u8> { self.to_le_bytes().to_vec() }
}
```

## RTTI, dynamic_cast, and Runtime Reflection

Rust has no built-in RTTI and no `dynamic_cast`.

### Replacement Strategies (in order of preference)

**1. Enum-based dispatch (best for finite type sets)**

```rust
enum Shape {
    Circle { radius: f64 },
    Rect { width: f64, height: f64 },
}
fn area(s: &Shape) -> f64 {
    match s {
        Shape::Circle { radius } => std::f64::consts::PI * radius * radius,
        Shape::Rect { width, height } => width * height,
    }
}
```

Compile-time exhaustiveness checking. Zero runtime overhead. Use when the set of variants is known.

**2. Trait objects (for open extension)**

```rust
trait Shape: std::fmt::Debug {
    fn area(&self) -> f64;
}
// Dynamic dispatch via &dyn Shape or Box<dyn Shape>
fn print_area(s: &dyn Shape) { println!("{:.2}", s.area()); }
```

**3. `Any` trait for downcasting (when you need runtime type testing)**

```rust
use std::any::Any;

trait Shape: Any {
    fn area(&self) -> f64;
    fn as_any(&self) -> &dyn Any;
}

impl dyn Shape {
    fn downcast_ref<T: Shape + 'static>(&self) -> Option<&T> {
        self.as_any().downcast_ref::<T>()
    }
}
```

Limitations: Requires `'static` lifetime. Can only test for concrete types, not trait implementations.

**4. Reflection crates (for complex needs)**

| Crate | Use Case |
|---|---|
| `bevy_reflect` | General-purpose reflection via derive macros |
| `facet` | Compile-time reflection building blocks |
| `typetag` | Serialization-compatible trait objects |

**Guideline**: If the C++ code uses `dynamic_cast` extensively, it often indicates a design that should be restructured into enums or traits in Rust rather than mimicked with `Any`.

## C++ Preprocessor Macros to Rust

| C++ Macro Pattern | Rust Equivalent |
|---|---|
| `#define CONSTANT 42` | `const CONSTANT: i32 = 42;` |
| `#define MAX(a,b) ((a)>(b)?(a):(b))` | `fn max<T: Ord>(a: T, b: T) -> T` or `std::cmp::max` |
| `#ifdef DEBUG` | `#[cfg(debug_assertions)]` or `#[cfg(feature = "debug")]` |
| `#ifdef _WIN32` | `#[cfg(target_os = "windows")]` |
| `#include` guards | Rust module system (no header files) |
| Code-generating macros (X-macros) | `macro_rules!` or procedural macros |
| `__FILE__`, `__LINE__` | `file!()`, `line!()`, `module_path!()` |
| `#pragma once` | Not needed (Rust modules are included exactly once) |
| Stringification (`#arg`) | `stringify!(expr)` |
| Token pasting (`##`) | Procedural macros with `quote!` |

### Guideline

Replace simple macros with `const`, `inline fn`, or generics. Reserve `macro_rules!` for patterns that genuinely need syntactic abstraction. Use proc macros sparingly — they increase compile time.

## Move Semantics

### The Core Difference

| Aspect | C++ | Rust |
|---|---|---|
| Default | Copy (for trivially copyable types) | Move |
| Move | Explicit via `std::move()` + move constructor | Implicit (all assignments move unless `Copy`) |
| Moved-from state | Valid but unspecified (can still use the variable) | Compile error (variable is consumed) |
| Copy | Implicit for POD, explicit `= default` for classes | Requires `#[derive(Copy, Clone)]`, only for stack types |
| Destructor after move | Still runs on moved-from object | Does NOT run (ownership transferred) |

### Porting Implications

1. **Remove all `std::move()` calls.** Rust moves by default. There is no equivalent needed.
2. **Remove move constructors and move assignment operators.** Rust handles this automatically.
3. **C++ `const&` parameters** often become `&T` (borrow) in Rust. C++ `&&` (rvalue ref) parameters have no Rust equivalent because moves are the default.
4. **C++ moved-from state** bugs (using an object after `std::move`) cannot occur in Rust — the compiler rejects it.
5. **Swap idiom**: C++ `std::swap` → Rust `std::mem::swap`. Both are O(1) for owned types.

## Migration Anti-Patterns

### 1. `Arc<Mutex<T>>` Everywhere

Wrapping everything in shared pointers + mutexes to silence the borrow checker. This is the #1 mistake in every C++ to Rust port.

**Why it is wrong**: Defeats compile-time safety guarantees. Introduces runtime panics (lock poisoning), unnecessary contention, and potential deadlocks.

**Fix**: Redesign data ownership. Use channels for communication. Split shared state into per-thread owned segments. Use interior mutability (`Cell`/`RefCell`) only where genuinely needed within a single thread.

### 2. Big-Bang Rewrite

Attempting to rewrite the entire C++ codebase at once before shipping anything.

**Why it fails**: Every documented successful migration (Google Android, Cloudflare Pingora, Meta mobile, ClickHouse) used incremental replacement. No documented big-bang success at scale.

**Fix**: Port one vertical slice at a time. Keep C++ and Rust running side-by-side. Ship each slice independently.

### 3. Literal Translation of Inheritance Hierarchies

Porting a C++ class hierarchy with virtual methods into Rust structs with `dyn Trait` everywhere and complex lifetimes.

**Fix**: Flatten to enums when the variant set is closed. Use composition (struct contains a strategy) rather than dynamic dispatch when the set is small and known.

### 4. Fighting the Borrow Checker with RefCell

Using `Rc<RefCell<T>>` to recreate C++'s shared mutable aliasing. This moves safety checks from compile time to runtime (panics on double borrow).

**Fix**: Restructure to avoid shared mutable aliasing. Common patterns:
- Split a large struct into smaller independent pieces
- Use indexes into a `Vec` instead of reference cycles
- Use an ECS (Entity Component System) pattern for complex object graphs

### 5. Ignoring Dependency Explosion

ClickHouse added 672 transitive Rust dependencies for initial integration. Each dependency is a supply chain risk and build time cost.

**Fix**:
- Audit with `cargo-audit` and `cargo-deny`
- Prefer crates with minimal transitive dependencies
- Vendor dependencies for reproducible builds
- Review `cargo tree` output before accepting new dependencies

## Real-World Lessons

| Organization | Scale | Key Takeaway |
|---|---|---|
| Google (Android) | 5M lines Rust | Write new code in Rust; let old C++ age out. Memory bugs dropped by 68%. |
| Cloudflare (Pingora) | Replaced NGINX | 70% less CPU, 67% less memory. Serving 1T+ requests/day. |
| Meta (mobile) | Billions of users | Gradual migration with FFI bridges. Developer happiness cited as a key benefit. |
| ClickHouse | 1.5M lines C++ | Incremental: Rust for specific modules. Sanitizer integration is critical. |
| Mozilla (Stylo) | Firefox CSS engine | Keep FFI tight (~10 functions). Deep bidirectional FFI is painful. |
| Google (Chromium) | Browser engine | CXX works for 92% of functions. "C++ is the ruler" strategy. |
| Discord | Read States service | 10x perf improvement (from Go, but principles apply). Ownership model eliminated GC issues. |
