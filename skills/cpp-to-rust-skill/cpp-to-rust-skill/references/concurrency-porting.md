# Concurrency Porting Guide

Use this reference when migrating C++ concurrent and parallel code to Rust.

## The Core Shift

C++ concurrency relies on programmer discipline (data races are undefined behavior but not caught at compile time). Rust enforces thread safety at compile time through the `Send` and `Sync` trait bounds. Every shared reference must be either immutable or exclusively owned.

This means most C++ concurrency patterns cannot be translated line-by-line. They must be redesigned around Rust's ownership model.

## Send and Sync (No C++ Equivalent)

| Trait | Meaning | Implication |
|---|---|---|
| `Send` | Type can be transferred to another thread | Most types are `Send`; `Rc<T>` is not |
| `Sync` | Type can be shared between threads via `&T` | `Mutex<T>` is `Sync`; `Cell<T>` is not |

These are auto-derived by the compiler. When the compiler rejects a concurrent pattern, it is usually detecting a real data race that C++ would silently allow.

Do NOT work around `Send`/`Sync` errors with `unsafe impl Send` unless you can formally justify the invariant.

## Pattern Map: C++ Concurrency to Rust

### Mutexes and Locks

| C++ | Rust | Notes |
|---|---|---|
| `std::mutex` + separate data | `Mutex<T>` wraps the data | Rust ties the lock to the data it protects. No lock-without-data bugs. |
| `std::shared_mutex` | `RwLock<T>` | Use when reads vastly outnumber writes. |
| `std::lock_guard` | `MutexGuard` (returned by `.lock()`) | RAII in both languages. Rust guard auto-releases on drop. |
| `std::scoped_lock` (multi-lock) | Lock ordering by convention or `parking_lot` | Rust stdlib does not have built-in multi-lock. |
| `std::condition_variable` | `Condvar` paired with `Mutex` | Same pattern: wait in a loop checking the predicate. |

### Atomics

| C++ | Rust | Notes |
|---|---|---|
| `std::atomic<T>` | `std::sync::atomic::AtomicT` | Close mapping. Same memory orderings (Relaxed, Acquire, Release, AcqRel, SeqCst). |
| `std::atomic<T>::compare_exchange` | `AtomicT::compare_exchange` | Rust version takes separate success/failure orderings. |
| `std::memory_order` | `std::sync::atomic::Ordering` | Identical semantics. |

**Key difference**: Building lock-free data structures in Rust is harder because you cannot have multiple mutable references. Use `crossbeam-epoch` for epoch-based reclamation instead of hazard pointers.

**Canonical reference**: Mara Bos, *Rust Atomics and Locks* (O'Reilly, 2023).

### Thread Pools

| C++ Pattern | Rust Equivalent | When to Use |
|---|---|---|
| Manual thread pool / `std::async` | **Rayon** (`rayon::ThreadPool`) | Data-parallel workloads, parallel iterators |
| OpenMP `#pragma omp parallel for` | **Rayon** `par_iter()` | Drop-in parallel iteration with work-stealing |
| Custom task queue | **Crossbeam** scoped threads + channels | Fine-grained task control with scoped lifetimes |
| `std::thread::hardware_concurrency` | `std::thread::available_parallelism` | Same purpose |

Rayon's work-stealing outperforms manual pools by 15-25% on irregular workloads.

### Shared Ownership

| C++ | Rust | Notes |
|---|---|---|
| `shared_ptr<T>` (no mutation) | `Arc<T>` | Immutable shared ownership across threads. |
| `shared_ptr<T>` + `mutex` | `Arc<Mutex<T>>` | Shared mutable state. Use sparingly (see anti-patterns below). |
| `shared_ptr<T>` (single-threaded) | `Rc<T>` | Not `Send`. Use only within one thread. |
| `weak_ptr<T>` | `Weak<T>` (from `Arc::downgrade`) | Break reference cycles. |

### Message Passing

| C++ | Rust | Notes |
|---|---|---|
| Custom queue + mutex + condvar | `std::sync::mpsc::channel` | Multi-producer, single-consumer. Stdlib. |
| Lock-free MPMC queue | `crossbeam::channel` | High-performance bounded/unbounded MPMC. |
| `std::promise` / `std::future` | `oneshot::channel` (tokio or crossbeam) | Single-value delivery. |

**Prefer channels over shared state.** Channels make ownership transfer explicit and eliminate lock contention.

## Async/Await: C++20 Coroutines vs Rust Futures

These are fundamentally different models.

| Aspect | C++20 Coroutines | Rust async/await |
|---|---|---|
| Model | Compiler transforms into coroutine frame (heap-allocated by default) | Compiler generates a state-machine `Future` (zero-allocation by default) |
| Executor | Not provided; bring your own | Runtime-specific: Tokio, async-std, smol |
| Cancellation | Implementation-defined | Drop the future = cancel |
| Thread affinity | No built-in concept | `Send` bounds control thread migration |
| Overhead | Heap allocation per coroutine frame | No allocation unless boxed (`Box<dyn Future>`) |

### Porting Strategy

1. Map C++ coroutine tasks to `async fn` in Rust.
2. Pick one runtime (Tokio is the ecosystem default) and commit to it.
3. Do NOT mix runtimes within a single binary.
4. Use `tokio::task::spawn_blocking` for CPU-heavy work inside an async context.
5. At FFI boundaries, do NOT expose Rust futures to C++. Use a blocking wrapper or callback-based API.

### Gotchas

1. Rust futures are lazy (nothing happens until polled). C++ coroutines may begin execution immediately.
2. `Send` + `Sync` bounds on futures create friction when porting C++ coroutines that freely share state across suspension points.
3. Holding a `MutexGuard` across an `.await` point causes deadlocks. Use `tokio::sync::Mutex` (not `std::sync::Mutex`) in async code.

## Anti-Patterns to Avoid

### `Arc<Mutex<T>>` Everywhere

The single most common mistake when porting C++ shared-state concurrency. Teams wrap everything in `Arc<Mutex<T>>` to silence the borrow checker.

**Problems:**
- Defeats compile-time safety (lock poisoning panics at runtime instead)
- Unnecessary lock contention
- Hides design flaws

**Fix:** Redesign data ownership. Use channels for communication, split data into per-thread owned segments, or restructure around message-passing.

### `Rc<RefCell<T>>` in Concurrent Code

`Rc` is NOT `Send`. Using `Rc<RefCell<T>>` across threads is a compile error. If you find yourself reaching for `Arc<RefCell<T>>`, stop — `RefCell` is also not `Sync`. Use `Arc<Mutex<T>>` or redesign.

### Blocking Inside Async

Calling blocking I/O or `std::sync::Mutex::lock` inside an `async fn` blocks the runtime thread. Use `tokio::task::spawn_blocking` or `tokio::sync::Mutex`.
