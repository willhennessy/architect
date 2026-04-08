# Claude Architect — PRD v2

## One-line pitch
Claude Architect is a steering interface to develop more robust system architectures with coding agents.

Leave lines of code to the agent. Architect gives you control over higher level design decisions with a birds eye view architecture diagram and point-and-click feedback to the agent.

## Problem
AI coding agents increase development velocity, but architecture reasoning remains human-constrained. Critical architecture decisions are often made implicitly during planning and hidden in code output. It is increasingly hard for senior engineers to maintain architectural coherence through line-level PR reviews. Senior engineers need a higher-level interface to steer and verify system evolution before costs compound in implementation, maintenance, and PR review.

### Old draft (for review)
> Coding agents can move from idea to code quickly, but hidden architecture decisions are often made implicitly during planning. Senior engineers need a way to surface and steer those decisions before they become expensive in implementation, maintenance, and PR review.
>
> AI coding agents increase development velocity, but architecture reasoning remains human-constrained.
> It is increasingly hard for senior engineers to maintain architectural coherence through line-level PR reviews.
> Senior engineers need a higher level interface to steer and verify system evolution.
>
> Coding agents are writing code faster than ever. The bottleneck remains human review - but you don’t need to review every line. Architect is a new steering interface for coding agents that lets you operate with leverage at a higher layer of abstraction. Review architecture - not lines of code.

## Core thesis
In a world of coding agents, the primary value of senior engineers is to make sound architecture decisions that direct agent behavior and set guardrails for ongoing development.

Chat based coding agents hide many implicit architecture decisions. The engineer is left with a suboptimal design and an incomplete picture of the system.

A C4 architecture diagram is an effective control surface for steering coding agents.

## Primary user
Senior engineers / tech leads building **new systems** with AI coding agents.

## Positioning statement
Claude Architect helps senior engineers steer coding agents at planning time by turning architecture into an interactive control surface before code is written.

---

## Main integration point
**Coding agent planning mode.**

In plan mode, the agent must produce:
1. Architecture diagram
2. Explanation of **WHY**
3. Evidence from plan assumptions/constraints

This gives the engineer a clear moment to critique and steer direction before implementation.

After architecture review, the agent must implement code according to the architecture diagram. If the agent discovers a reason to change the architecture during implementation, surface that to the engineer for review. A key principle is that the engineer should be aware of all architecture decisions.

**Anthropic product angle:** the end-state is to build this as a single integrated Architect product inside Claude with Imagine built in (not a permanent multi-tool handoff flow).

## Why this wedge
Instead of targeting engineers maintaining mature, complex systems, v2 focuses on **greenfield builds** where architecture is still fluid.

This lowers the immediate requirement for perfect architecture extraction accuracy and maximizes value at the highest-leverage moment: **before implementation begins**.

---

## Hypotheses to test
Goal: invalidate or validate these as quickly as possible.

1. **Real need**: Engineers want more insight into the architecture than a coding agent proposes. This is key: is there a real pain point?
    1. Research questions
    2. Walk me through how you use plan mode for a major new feature?
    3. When using plan mode today, how much depth do you try to understand about the architecture that the agent is proposing? (some people will not care and fully trust the agent to architect)
    4. How do you get that information? Does the agent offer it proactively, or do you have to ask? Do you have to read the code?
    5. Have you ever asked the agent to draw a system diagram? How was it?
2. **Visual architecture diagrams with point-and-click feedback improve vibe coding quality.**
   They help engineers identify otherwise invisible architecture decisions made by the agent and steer the agent more effectively.
3. **This interaction improves engineer understanding of system evolution.**
   Together, engineer + agent can design better and faster systems.
4. **Faster, safer, more legible evolution**: A semantic architecture representation establishes useful guardrails for ongoing development. Or at minimum, it provides useful PR diffs to accelerate PR reviews with confidence.

---

## Success metrics (v2)
1. % of planning sessions with at least one engineer-requested architectural change
2. Time to approved architecture plan
3. Engineer-rated confidence before implementation
4. % of implementation PRs matching approved architecture intent
5. % of architecture claims with explicit evidence + reviewer-rated trust/correctness of rationale

---

## MVP scope
### In scope
1. Planning-mode diagram generation from agent plan
2. Diagram + WHY + plan evidence
3. Engineer feedback loop (chat-based in MVP)
4. Agent revision loop until architecture approval
5. Hand-off to implementation mode after approval

### Out of scope
- Full real-time visual co-editing UI
- Perfect legacy codebase extraction
- Deep multi-repo architecture inference
- Enforcement-only workflow without planning loop

### Diagram generation
Treat diagram generation as an independent task from architecture generation so that we can swap out different diagram visualization tools later.

For MVP, only output the semantic architecture. We will use Claude Chat to visualize it.

Later, we will generate an HTML diagram. This will enable more interactivity, but it’s out of scope for MVP.

---

## Product flow + roadmap

### Phase 1 — Plan mode diagram + simple chat-based feedback
1. Engineer provides intent (text, rough diagram, or whiteboard photo)
2. Agent runs planning mode and generates architecture diagram + WHY.
3. Agent writes the final output to a single file per the skill definition. (later, generate HTML diagram to support point and click comments)
4. **Prototype workflow (temporary):** Engineer uploads the output file to Claude Chat.
5. Claude Chat generates an interactive diagram using Claude Imagine.
6. Engineer reviews and gives feedback (MVP via chat with the coding agent; later point-and-click comments)
7. Agent iterates on plan + architecture
8. Engineer approves architecture
9. Agent implements

#### Personal milestones (publish observations)
1. Agent understanding of architecture
2. Utility of this vs `/init` (does this improve agent code output? does it improve engineer confidence in the system?)
3. State of the art diagram generators: Claude Imagine vs Codex Images vs HTML

### Phase 2 — Point-and-click feedback on diagram
Upgrade feedback from chat-only to direct, pointed diagram interaction.

1. Engineer clicks node/edge to annotate architectural concern
2. Agent maps annotation to plan changes
3. Agent regenerates architecture + WHY
4. Engineer iterates until approval

**Prerequisite:** stable node/edge IDs across regenerations so comments remain attached to intended elements.

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

## Evidence model
For greenfield planning, evidence is primarily **plan evidence**:
- Requirements
- Constraints
- Assumptions
- Tradeoffs

(Phase 2+) Add code evidence:
- File/symbol refs
- Commit/PR refs

---

## Risks and mitigations
1. **Risk:** Diagram becomes cosmetic output, not steering tool.
   - **Mitigation:** Require explicit feedback→revision loop before implementation.

2. **Risk:** Agent rationale feels generic or ungrounded.
   - **Mitigation:** Force structured WHY tied to assumptions/constraints/tradeoffs.

3. **Risk:** Workflow overhead hurts adoption.
   - **Mitigation:** Keep MVP in existing planning chat flow; no heavy UI dependency.
