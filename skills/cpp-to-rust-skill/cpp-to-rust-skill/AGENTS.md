# AGENTS.md

Shared instructions for AI coding agents working in this repository.

## Goal

Maintain and improve the reusable C++ to Rust migration skill in this repository so it stays reliable for real production ports.

## Canonical Source of Truth

1. Treat `SKILL.md` as the canonical workflow.
2. Keep supporting references in `references/` concise and task-focused.
3. Keep UI metadata in `agents/openai.yaml` aligned with skill behavior.

## Cross-Agent Compatibility Rules

1. Keep instructions deterministic and non-interactive by default.
2. Use small, composable instruction files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) instead of duplicating large prompt blocks.
3. Preserve identical operational guidance across adapters unless the platform requires a clear exception.

## Update Workflow

1. Update `SKILL.md` first.
2. Update references after core workflow changes.
3. Update adapters and metadata last.
4. Update `references/sources.md` when adding or replacing external guidance.
