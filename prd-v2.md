# Claude Architect — PRD v2 (Greenfield Planning-Mode Wedge)

## One-line pitch
Claude Architect is a planning-mode architecture control surface for senior engineers building new systems with coding agents.

## Why this wedge
Instead of targeting engineers maintaining mature, complex systems, v2 focuses on **greenfield builds** where architecture is still fluid.

This lowers the immediate requirement for perfect architecture extraction accuracy and maximizes value at the highest-leverage moment: **before implementation begins**.

## Problem
Coding agents can move from idea to code quickly, but hidden architecture decisions are often made implicitly during planning. Senior engineers need a way to surface and steer those decisions before they become expensive in implementation and PR review.

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

---

## Hypotheses to test
Goal: invalidate or validate these as quickly as possible.

1. **Visual architecture diagrams with point-and-click feedback improve vibe coding quality.**
   They help engineers identify otherwise invisible architecture decisions made by the agent and steer the agent more effectively.

2. **This interaction improves engineer understanding of system evolution.**
   Together, engineer + agent can design better and faster systems.

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

---

## Workflow (v2)
1. Engineer provides intent (text, rough diagram, or whiteboard photo)
2. Agent runs planning mode and proposes architecture diagram + WHY
3. Engineer reviews and gives feedback (MVP via chat; later point-and-click)
4. Agent iterates on plan + architecture
5. Engineer approves architecture
6. Agent implements
7. (Phase 2+) PR architecture diff checks implementation vs intended architecture

---

## Evidence model (v2)
For greenfield planning, evidence is primarily **plan evidence**:
- Requirements
- Constraints
- Assumptions
- Tradeoffs

(Phase 2+) Add code evidence:
- File/symbol refs
- Commit/PR refs

---

## Success metrics (v2)
1. % of planning sessions with at least one engineer-requested architectural change
2. Time to approved architecture plan
3. Engineer-rated confidence before implementation
4. % of implementation PRs matching approved architecture intent

---

## Phases

### Phase 1 — Plan mode diagram + simple chat-based feedback
In coding agent plan mode, instruct the agent to produce an architecture diagram for the current plan.

Why this matters: it surfaces architecture decisions and assumptions for engineer steering before implementation.

MVP feedback mechanism: engineer gives architecture feedback through agent chat.

#### Personal milestones (publish observations)
1. Agent understanding of architecture
2. Utility vs `/init` (does this improve agent code writing?)
3. State of the art diagram generators: Claude Imagine vs Codex Images vs HTML

### Phase 2 — Point-and-click feedback on diagram
Upgrade feedback from chat-only to direct, pointed diagram interaction.

1. Engineer clicks node/edge to annotate architectural concern
2. Agent maps annotation to plan changes
3. Agent regenerates architecture + WHY
4. Engineer iterates until approval

### Phase 3 — PR diffs (post-vibe-coding scale phase)
PR-time architecture diff is most useful after the initial vibe-coding phase, when projects scale to more engineers, more PRs, and more complexity.

1. Baseline architecture graph
2. Per-PR delta
3. Visual + textual summary + evidence refs + risk flags
4. Shared team artifact for architecture coherence over time

### Phase 4 — Integrate with existing codebases
Enable engineers to add Claude Architect to existing codebases and established PR workflows.

This is likely the hardest phase: senior engineers already hold nuanced mental models of their systems, so architecture output must meet a much higher bar for accuracy and trust.

1. Existing-repo architecture extraction with high-confidence evidence
2. Alignment checks against known system boundaries/ownership
3. PR workflow integration without adding review overhead
4. Trust metrics: precision of inferred components/edges and low hallucination rates

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
