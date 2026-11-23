# C++ to Rust Porting Playbook

Use this reference for end-to-end migration sequencing.

## Phase 0: Inventory and Scope

1. Catalog modules by criticality, defect rate, and complexity.
2. Identify mandatory functionality for the first Rust release.
3. Define explicit out-of-scope items.
4. Build a dependency graph to pick safe migration slices.

Deliverables:

- Scope doc with include/exclude lists
- Module dependency map
- Migration order with risk notes

## Phase 1: Freeze Behavior

1. Add characterization tests for all required API behavior.
2. Capture golden vectors for serialization/parsing outputs.
3. Add deterministic fixtures for edge conditions and error paths.
4. Add performance baselines on representative workloads.

Deliverables:

- Behavior parity test suite
- Golden corpus
- Benchmark baseline report

## Phase 2: Rust Architecture

1. Design crate boundaries around cohesive domains.
2. Define public API shapes and error taxonomy first.
3. Mark where ownership, borrowing, and lifetimes enforce invariants.
4. Identify transitional FFI seams for incremental rollout.

Deliverables:

- Crate map
- API draft with type signatures
- Error model
- FFI seam plan

## Phase 3: Vertical Slice Porting

1. Port one slice at a time (model + logic + boundary + tests).
2. Keep old and new implementations runnable side-by-side when practical.
3. Run tests and benchmarks per slice.
4. Merge only when slice gates pass.

Deliverables per slice:

- Rust implementation
- Tests and benchmarks
- Parity report

## Phase 4: Consolidation and Cleanup

1. Remove replaced C++ code paths.
2. Collapse temporary adapters that are no longer needed.
3. Tighten unsafe boundaries and invariants documentation.
4. Finalize API docs and migration notes.

Deliverables:

- Rust-only path for scoped features
- Dead code removal commit set
- Safety review notes

## Phase 5: Hardening

1. Add fuzzing/property tests for parser and boundary-heavy logic.
2. Add stress and concurrency tests where relevant.
3. Add observability checks (logs, metrics, structured errors).

Deliverables:

- Hardening test suite
- Production-readiness checklist
