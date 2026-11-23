# C++ to Rust Pattern Map

Use this map when translating architecture and semantics, not just syntax.

| C++ Pattern | Rust Pattern | Notes |
|---|---|---|
| `new/delete`, manual ownership | RAII via ownership + `Drop` | Prefer stack ownership and explicit `Box` only when needed. |
| `std::unique_ptr<T>` | `Box<T>` | Use when stable heap allocation is required. |
| `std::shared_ptr<T>` | `Arc<T>` | Add `Mutex`/`RwLock` only for shared mutability. |
| `std::optional<T>` | `Option<T>` | Prefer exhaustive matching over null-like checks. |
| exceptions | `Result<T, E>` | Model recoverable errors in typed enums. |
| class hierarchy + virtual methods | traits + composition | Keep trait objects only when dynamic dispatch is required. |
| tagged unions/manual discriminators | enums | Encode states directly with data-bearing variants. |
| mutable global state | explicit context/state structs | Pass dependencies through constructors/functions. |
| `const` discipline | ownership + borrowing (`&T`, `&mut T`) | Borrow checker becomes the mutation contract. |
| iterators with invalidation hazards | iterator adapters over slices/collections | Favor borrow-scoped iteration and immutable defaults. |

## Semantic Refactoring Heuristics

1. Replace boolean mode flags with enum states.
2. Replace partially initialized structs with constructors and private fields.
3. Replace method families that can fail silently with `Result` returning APIs.
4. Replace inheritance-only reuse with small composable helper types.
5. Replace large mutating methods with pure transformation functions plus explicit commit points.

## Advanced Construct Map

| C++ Pattern | Rust Pattern | Notes |
|---|---|---|
| CRTP | Trait default methods with `Self` | Rust traits already have `Self`; CRTP is unnecessary. |
| SFINAE / `enable_if` / Concepts | Trait bounds + where clauses | Clearer error messages by design. |
| Variadic templates | `macro_rules!` / proc macros / tuple impls | Rust has no variadic generics (RFC #376 open). |
| Expression templates | Lazy eval types + proc macros | No direct equivalent; redesign or wrap existing crate. |
| Template specialization | Separate trait impls / sealed traits / newtypes | Full specialization is unstable in Rust. |
| `dynamic_cast` / RTTI | Enum dispatch (preferred), `Any` trait, trait objects | Eliminate runtime type checks where possible. |
| `#define` constants | `const` or `static` | Prefer `const` for compile-time values. |
| Function-like macros | Generic functions, `macro_rules!`, proc macros | Replace with generics first; macros as last resort. |
| `#ifdef` conditional compilation | `#[cfg(...)]` attributes | `cfg(target_os)`, `cfg(feature)`, `cfg(debug_assertions)`. |
| `std::move()` + move constructor | Default (all assignments move) | Remove `std::move()` calls; Rust moves by default. |
| Moved-from state (valid but unspecified) | Compile error (variable consumed) | Rust prevents use-after-move at compile time. |
| `std::string` (arbitrary bytes) | `String` (always valid UTF-8) or `Vec<u8>` | Validate encoding at FFI boundary; use `Vec<u8>` for binary data. |
| `std::swap` | `std::mem::swap` | Both O(1) for owned types. |

Load [advanced-pattern-map.md](./advanced-pattern-map.md) for detailed examples, code snippets, RTTI replacement strategies, and anti-patterns.

## Error Taxonomy Guidance

1. Define domain error enums per subsystem.
2. Wrap lower-level IO/parse errors with context-rich variants.
3. Avoid lossy string conversion at subsystem boundaries.
4. Preserve stable error semantics for callers during migration.
