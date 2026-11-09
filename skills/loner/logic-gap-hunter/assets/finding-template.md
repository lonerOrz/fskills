# Finding: <short title>

| Field | Value |
|---|---|
| Location | `<file>:<line-range>` |
| Dimension | e.g. concurrency / idempotency / boundary |
| Reachability | `reachable` / `assumption-dependent` / `theoretical-only` |
| Severity (initial) | high / medium / low / theoretical |

## Trigger sequence

The exact call order, input, or timing that reaches the suspect path.

## Expected behavior

What the code intends to do under that trigger.

## Actual behavior

What the code does under that trigger, with the relevant line range.

## Implicit assumption

The assumption that must hold for the code to behave as expected.

## Consequence if assumption fails

The observable failure mode.

## Minimal verification

A test case, assertion, or static-analysis query that would confirm or refute the
counterexample. State what result would count as confirmation.
