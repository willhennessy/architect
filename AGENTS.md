# AGENTS.md

## Architecture Artifact Rules

When generating architecture artifacts for this repository:

- Build one canonical architecture model first, then derive audience-specific views from it.
- Treat the canonical model as the source of truth. Do not define competing architecture facts separately in views.
- Preserve stable IDs across regenerations whenever the underlying concept has not changed.
- Use evidence-backed modeling. Prefer runtime and deploy evidence over docs or naming signals when they conflict.
- Keep C4 abstraction levels strict. Do not mix system, container, and component concepts in the same view.
- Make data ownership and system-of-record information first-class whenever the codebase supports that inference.
- Normalize names and deduplicate concepts. Do not create near-duplicate elements unless evidence shows they are distinct.
- In update flows, prefer semantic diffs over full rewrites and emit explicit added/removed/changed model deltas.

## Scope

These are repo-wide working rules. Detailed schemas, output formats, and step-by-step extraction procedures belong in the relevant skill files rather than here.

## Repo-Local Skills

Repo-local skills that should be auto-discovered by Codex or Claude live under `.agents/skills/` and `.claude/skills/`. Keep `skills/` as the source-of-truth for authored skill content, and expose repo-local installs from there.
