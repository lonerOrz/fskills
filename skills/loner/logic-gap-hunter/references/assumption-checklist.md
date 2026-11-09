# Implicit Assumption Checklist

For each assumption, record: the assumption statement, its category, and the
consequence if it does not hold. Do not propose remedies here.

## Caller contract

- Caller always supplies non-null arguments.
- Caller always invokes methods in a specific order.
- Caller never re-enters the function before the prior invocation returns.
- Caller never passes an object it later mutates concurrently.

## Configuration

- A required configuration key is always present.
- A configured value is always within a valid range.
- Environment-specific defaults are identical across deployment targets.

## Concurrency and timing

- The function is never invoked concurrently on the same key.
- An external callback arrives before the timeout expires.
- Clock skew between nodes is bounded.
- A lock is held for the entire critical section.

## External dependency

- The downstream service is idempotent under retry.
- The downstream service never returns a partial success.
- The downstream contract does not change within a deployment window.
- Network failure manifests as an explicit error, not a silent timeout.

## Data and serialization

- Persisted data always conforms to the current schema.
- Round-trip serialization preserves all fields.
- Character encoding is uniform across producers and consumers.

## Resource and environment

- Sufficient memory and file descriptors are available.
- Temporary storage is writable and not shared across processes.
- The process is not killed mid-operation by an external supervisor.
