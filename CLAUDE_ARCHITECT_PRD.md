# Claude Architect — PRD v1

## One-line pitch
Claude Architect is an evidence-backed architecture control surface that lets engineers steer coding agents through diagrams and review architecture diffs in every PR.

## Problem
AI coding agents increase change velocity, but architecture reasoning remains human-constrained.
Senior engineers can’t reliably maintain architectural coherence through line-level PR review alone.

## Primary user
Senior IC / tech lead reviewing architecture-impacting PRs in AI-assisted codebases.

## JTBD
“Help me quickly understand and steer architecture changes so I can approve PRs with confidence.”

## MVP scope (v1)
1. `architect init`
   - Extract baseline architecture model (context, containers, components, edges).
2. `architect iterate`
   - Display interactive diagram with component drill-down and rationale.
   - Accept point-and-comment feedback and regenerate architecture proposal.
3. `architect pr-diff <pr>`
   - Generate visual + textual architecture delta attached to PR.

## Output artifacts
- `architecture/context.yaml`
- `architecture/containers.yaml`
- `architecture/components/*.yaml`
- `architecture/diffs/<pr>.md|json`

## Required metadata per node/edge
- `evidence`: file paths, symbol refs, commit refs
- `confidence`: numeric score + threshold state
- `why`: rationale summary
- `owner` (optional v1.1)

## Risk flags (MVP)
- New boundary crossing
- Coupling increase
- Cross-cutting concern impact (auth/logging/config/observability)
- Runtime topology mismatch suspicion

## Success metrics
- **Accuracy:** reviewer rates “architectural delta captured correctly” in >80% of sampled PRs
- **Efficiency:** 25%+ reduction in architecture-review time on target PR set
- **Trust:** <15% high-severity hallucinated edges in eval dataset

## Non-goals (v1)
- Full visual whiteboard editor
- Full policy enforcement engine
- Multi-person real-time co-editing
- Broad executive/onboarding experiences

## Risks & mitigations
- Hallucinated structure → evidence-required edges + confidence gating
- Workflow friction → PR-native artifact + comment-compatible UX
- Scope creep → one repo type, one language family, one PR pipeline first

## Why now
Agent-written code is rapidly increasing PR volume.
The interface for engineering must move up the stack from line edits to architecture steering.

## Suggested CLI surface
- `/architect init`
- `/architect show`
- `/architect comment --target <edge|node> --text "..."`
- `/architect regenerate`
- `/architect approve`
- `/architect diff --pr <id>`
