# Claude Architect — PRD v1

## One-line pitch

Claude Architect is a new steering interface for senior engineers in an AI-native workflow. This agent skill creates an architecture control surface that to steer coding agents through diagrams and review architecture diffs in every PR.

## Problem

AI coding agents increase change velocity, but architecture reasoning remains human-constrained.
Senior engineers can’t reliably maintain architectural coherence through line-level PR review alone.

## Primary user

Senior IC / tech lead reviewing architecture-impacting PRs in AI-assisted codebases.

## JTBD

“Help me quickly understand and steer architecture changes so I can approve PRs with confidence.”

## MVP scope (v1)

1. `/architect init`
   - Extract baseline architecture model (context, containers, components, edges).
2. `/architect iterate`
   - Display interactive diagram with component drill-down and rationale.
   - Accept point-and-comment feedback and regenerate architecture proposal.
3. `/architect pr-diff <pr>`
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

# Press release

1. 90-second demo script (voiceover)

Title card (0:00–0:03)
“Claude Architect: diagrams as the control surface for coding agents”

Problem (0:03–0:12)
“Coding agents can generate PRs faster than humans can reason about architecture.
Senior engineers need a higher-level interface than line-by-line review.”

Step 1 — Initialize architecture (0:12–0:25)
“I run architect init on this repo.
Claude Architect builds an evidence-backed architecture model: context, containers, components, and dependency edges.”

Step 2 — Interactive architecture + WHY (0:25–0:40)
“Each component is clickable.
For every edge and design choice, I can inspect the rationale and source evidence: files, symbols, and commit references.”

Step 3 — Steering loop (lean-forward moment) (0:40–0:56)
“I click this edge and comment: ‘Route this through async queue, not direct sync call.’
The agent updates the architecture and explains second-order effects: latency, failure isolation, and ownership boundaries.”

Step 4 — Implementation handoff (0:56–1:05)
“Once approved, I switch from architect mode to implementation.
The coding agent executes against the approved architecture.”

Step 5 — PR architecture diff (1:05–1:24)
“When the PR opens, Claude Architect auto-attaches a visual architecture diff.
It shows what changed, why it changed, evidence links, and risk flags like boundary crossings and coupling increases.”

Close (1:24–1:30)
“Claude Architect turns diagrams from documentation into a control plane for AI-native engineering.”

───

2. Shot list / storyboard (what to show on screen)

1) Repo + problem text overlay (agent PR velocity up, architecture review bottleneck)
2) Terminal: architect init + generated architecture/\*.yaml
3) Diagram view: click container/component, open rationale panel
4) Comment action on edge (“use queue”)
5) Regenerated diagram + updated WHY panel
6) Terminal: “approve architecture / implement”
7) GitHub PR view with attached architecture diff artifact
8) Diff panel with 3 sections: Changed, Why, Risk
9)
───

1) Shot list / storyboard (what to show on screen)

1. Repo + problem text overlay (agent PR velocity up, architecture review bottleneck)
2. Terminal: architect init + generated architecture/*.yaml
3. Diagram view: click container/component, open rationale panel
4. Comment action on edge (“use queue”)
5. Regenerated diagram + updated WHY panel
6. Terminal: “approve architecture / implement”
7. GitHub PR view with attached architecture diff artifact
8. Diff panel with 3 sections: Changed, Why, Risk
9. Final frame: “Diagram = control surface”
