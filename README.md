# fskills

A declarative, deterministic skill package manager and aggregator for AI agents.

`fskills` tracks, filters, and synchronizes upstream skill packages into a unified local workspace with strict atomic materialization and lockfile pinning.

---

## Design Principles

- **Declarative**: Upstream repositories, target namespaces, and package filters are declared in `source.toml`.
- **Deterministic**: Revisions are strictly pinned by commit SHA in `source.lock.toml`.
- **Zero-Waste Inspection**: State checking (`check`) inspects remote Git tree metadata without performing full repository clones.
- **Strict Pruning**: Package synchronization is bidirectional; removing a selector or deleting an upstream package immediately prunes orphaned local directories.
- **Atomic Materialization**: Updates are staged and swapped within the same filesystem transaction to prevent partially written directories.
