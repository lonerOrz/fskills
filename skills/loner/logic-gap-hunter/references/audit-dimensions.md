# Audit Dimensions

Mark each dimension `applicable` or `not-applicable` against the target scope.
For `applicable`, record the line range. For `not-applicable`, record the reason.

## Input domain

- Boundary values: minimum, maximum, zero, negative, empty.
- Malformed input: wrong type, missing required field, oversized payload.
- Default and fallback values: what happens when the value is absent.

## Nullability and presence

- Null, undefined, empty string, empty collection.
- Optional fields that downstream code assumes are populated.
- Return values that may be `None`/`null` but are dereferenced unconditionally.

## Type and precision

- Implicit coercion between numeric, string, and boolean.
- Integer overflow, floating-point comparison, rounding drift.
- Serialization and deserialization round-trip fidelity.

## State and ordering

- State transitions that assume a prior state was reached.
- Operations that are order-dependent but invoked without ordering guarantees.
- Retry or replay paths that re-enter a non-idempotent block.

## Concurrency and reentrancy

- Shared mutable state accessed without synchronization.
- Reentrant call paths through callbacks or event handlers.
- TOCTOU windows between check and use.

## Exception and failure paths

- Partial failure: one step fails after a prior step has committed side effects.
- Swallowed exceptions that leave state inconsistent.
- Cleanup blocks that themselves throw.

## Resource lifecycle

- Handles, connections, locks, or temporary files not released on every path.
- Resource acquisition inside a loop without release.
- Double release or release-after-transfer.

## External dependency behavior

- Downstream timeout, partial response, or degraded mode.
- Downstream non-idempotency under retry.
- Dependency version or contract drift assumed to be stable.

## Idempotency and duplication

- Duplicate submission producing double effect.
- At-least-once delivery assumed to be exactly-once.
- Deduplication keys that collide across distinct logical operations.

## Authorization and trust boundary

- Input crossing a trust boundary without validation.
- Authorization check performed on a different object than the one mutated.
- Internal caller assumed trusted without verification.
