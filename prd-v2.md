# Claude Architect — PRD v2 (Greenfield Planning-Mode Wedge)

## One-line pitch
Claude Architect is a planning-mode architecture control surface for senior engineers building new systems with coding agents.

## Why this wedge
Instead of targeting engineers maintaining mature, complex systems, v2 focuses on **greenfield builds** where architecture is still fluid.

This lowers the immediate requirement for perfect architecture extraction accuracy and maximizes value at the highest-leverage moment: **before implementation begins**.

## Problem
AI coding agents increase development velocity, but architecture reasoning remains human-constrained. Critical design decisions are often made implicitly during planning and hidden in code output. Senior engineers need a higher-level steering interface to surface, challenge, and direct architecture decisions before costs compound in implementation, maintenance, and PR review.

### Old draft (for review)
> Coding agents can move from idea to code quickly, but hidden architecture decisions are often made implicitly during planning. Senior engineers need a way to surface and steer those decisions before they become expensive in implementation and PR review.
>
> AI coding agents increase development velocity, but architecture reasoning remains human-constrained. It is increasingly hard for senior engineers to maintain architectural coherence through line-level PR reviews. Senior engineers need a higher level interface to steer and verify system evolution.
>
> Coding agents are writing code faster than ever. The bottleneck remains human review - but you don’t need to review every line. Architect is a new steering interface for coding agents that lets you operate with leverage at a higher layer of abstraction. Review architecture - not lines of code.

## Primary user
Senior engineers / tech leads building **new systems** with AI coding agents.

## Core thesis
The architecture diagram is not documentation—it is the control surface for steering agent plans.

## Main integration point
**Coding agent planning mode.**

In plan mode, the agent must produce:
1. Architecture diagram
2. Explanation of **WHY**
3. Evidence from plan assumptions/constraints

This gives the engineer a clear moment to critique and steer direction before implementation.

After architecture review, the agent implements according to the approved architecture. If implementation reveals a reason to change architecture, that change is surfaced back to the engineer for review before continuing.

**Anthropic product angle:** the end-state is a single integrated Claude Architect experience with built-in diagram generation and interaction (Claude Imagine-native), rather than a multi-tool handoff.

---

## Hypotheses to test
Goal: invalidate or validate these as quickly as possible.

1. **Real need:** Engineers want more architecture insight than coding agents currently provide during planning.
2. **Visual architecture diagrams with point-and-click feedback improve vibe coding quality.**
3. **This interaction improves engineer understanding of system evolution.**
4. **Faster, safer, more legible evolution:** semantic architecture representation creates useful guardrails (or at minimum better PR diffs).

---

## MVP scope (v2)
### In scope
1. Planning-mode diagram generation from agent plan
2. Diagram + WHY + plan evidence
3. Engineer feedback loop (chat-based in MVP)
4. Agent revision loop until architecture approval
5. Hand-off to implementation mode after approval

### Out of scope (v2)
- Full real-time visual co-editing UI
- Perfect legacy codebase extraction
- Deep multi-repo architecture inference
- Enforcement-only workflow without planning loop

### Diagram generation
Treat diagram generation as independent from architecture generation so visualization can be swapped later.

- MVP: output semantic architecture artifact only
- Prototype rendering: Claude Chat / Claude Imagine
- Later: native HTML/interactive rendering in integrated Claude Architect experience

---

## Product flow + roadmap

### Phase 1 — Plan mode diagram + simple chat-based feedback
1. Engineer provides intent (text, rough diagram, or whiteboard photo)
2. Agent runs planning mode and produces architecture output + WHY + plan evidence
3. Agent writes final output to one structured artifact file
4. **Prototype workflow (temporary):** engineer uploads artifact to Claude Chat for Claude Imagine visualization
5. Engineer reviews and gives feedback via chat with coding agent
6. Agent iterates on plan + architecture until approval
7. Engineer approves architecture
8. Agent implements against approved architecture

Why this matters: it surfaces architecture decisions and assumptions for steering before implementation.

#### Personal milestones (publish observations)
1. Agent understanding of architecture
2. Utility vs `/init` (does this improve agent code output and engineer confidence?)
3. State of the art diagram generators: Claude Imagine vs Codex Images vs HTML

### Phase 2 — Point-and-click feedback on diagram
Upgrade feedback from chat-only to direct, targeted diagram interaction.

1. Engineer clicks node/edge to annotate concern
2. Agent maps annotation to plan changes
3. Agent regenerates architecture + WHY
4. Engineer iterates until approval

**Prerequisite:** stable node/edge IDs across regenerations so comments remain attached to intent.

### Phase 3 — PR diffs (post-vibe-coding scale phase)
Most useful after the initial single-engineer vibe-coding phase, when teams scale to more engineers, more PRs, and more complexity.

1. Baseline architecture graph
2. Per-PR delta
3. Visual + textual summary + evidence refs + risk flags
4. Shared team artifact for architecture coherence over time

### Phase 4 — Integrate with existing codebases
Enable engineers to add Claude Architect to existing codebases and established PR workflows.

This is likely the hardest phase: senior engineers already hold nuanced mental models of their systems, so output must meet a much higher bar for accuracy and trust.

1. Existing-repo architecture extraction with high-confidence evidence
2. Alignment checks against known system boundaries/ownership
3. PR workflow integration without adding review overhead
4. Trust metrics: precision of inferred components/edges and low hallucination rates

---

## Evidence model
For greenfield planning, evidence is primarily **plan evidence**:
- Requirements
- Constraints
- Assumptions
- Tradeoffs

(Phase 3+) add code evidence:
- File/symbol refs
- Commit/PR refs

---

## Success metrics (v2)
1. % of planning sessions with at least one engineer-requested architectural change
2. Time to approved architecture plan
3. Engineer-rated confidence before implementation
4. % of implementation PRs matching approved architecture intent
5. % of architecture claims with explicit evidence + reviewer-rated trust/correctness of rationale

---

## Risks and mitigations
1. **Risk:** Diagram becomes cosmetic output, not steering tool.
   - **Mitigation:** Require explicit feedback→revision loop before implementation.

2. **Risk:** Agent rationale feels generic or ungrounded.
   - **Mitigation:** Force structured WHY tied to assumptions/constraints/tradeoffs.

3. **Risk:** Workflow overhead hurts adoption.
   - **Mitigation:** Keep MVP in existing planning chat flow; no heavy UI dependency.

---

## Positioning statement
Claude Architect helps senior engineers steer coding agents at planning time by turning architecture into an interactive control surface before code is written.
