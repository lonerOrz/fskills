# cpp-to-rust-skill

Open-source, generic agent skill repository for migrating C++ libraries to idiomatic Rust.

This repo contains the `cpp-to-rust-port` skill payload plus lightweight adapter files for common agent runtimes.

## Repository layout

```text
cpp-to-rust-skill/
├── AGENTS.md
├── CLAUDE.md
├── GEMINI.md
├── LICENSE
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── advanced-pattern-map.md      ← templates, RTTI, macros, move semantics, anti-patterns
    ├── build-system-integration.md  ← CMake+Cargo, Bazel+rules_rust, platform linking
    ├── concurrency-porting.md       ← atomics, async/await, thread pools, Send/Sync
    ├── cpp-rust-pattern-map.md      ← basic + advanced construct translation tables
    ├── cross-agent.md               ← cross-agent adapter design rules
    ├── ffi-and-unsafe-boundaries.md ← FFI safety, ABI, symbol mangling, panic handling
    ├── perf-and-parity.md           ← test gates, differential testing, sanitizer integration
    ├── performance-traps.md         ← cloning, iterators, enum bloat, FFI overhead, allocations
    ├── porting-playbook.md          ← phase-by-phase migration workflow
    └── sources.md                   ← 40+ tools, crates, case studies, and references
```

## Skill files

- `SKILL.md`: canonical operational instructions (12 sections covering scope, testing, build systems, idiomatic design, concurrency, FFI, anti-patterns, performance, and completion gates)
- `references/`: supporting migration guidance, pattern maps, and checklists
- `agents/openai.yaml`: optional metadata for skill catalogs that support it

## Cross-agent adapters

- `AGENTS.md`: generic shared agent guidance
- `CLAUDE.md`: Claude adapter (imports `AGENTS.md`)
- `GEMINI.md`: Gemini adapter (imports `AGENTS.md`)

## How to use

### Codex

```bash
mkdir -p ~/.codex/skills/cpp-to-rust-port
cp -R ./* ~/.codex/skills/cpp-to-rust-port/
```

Then invoke the skill with prompts like `Use $cpp-to-rust-port to migrate this C++ module to Rust.`

### Claude Code

1. Copy `AGENTS.md` and `CLAUDE.md` into the target project root.
2. Keep `SKILL.md` and `references/` available in the same repo for detailed guidance.

### Gemini CLI

1. Copy `AGENTS.md` and `GEMINI.md` into the target project root.
2. Keep `SKILL.md` and `references/` available in the same repo for detailed guidance.

## Design goals

- Port only required scope first, then expand safely. Never big-bang rewrite.
- Prefer semantic, idiomatic Rust over mechanical translation.
- Preserve behavior and performance with measurable parity gates and differential testing.
- Keep `unsafe` and FFI boundaries explicit and minimal.
- Handle real-world concerns: build system integration, concurrency porting, performance traps, ABI compatibility, and dependency management.
- Learn from industry: guidance informed by Google Android, Cloudflare Pingora, Meta mobile, Mozilla Stylo, and ClickHouse migrations.

## Sources

Primary references are documented in [references/sources.md](./references/sources.md).
