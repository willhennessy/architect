# Claude Architect — PRD

## One-line pitch

Claude Architect is a human-to-agent steering interface to develop more robust system architectures with coding agents.

## Problem

Engineers have stopped writing code. They now direct coding agents through a chat interface and PRs are up 200% as a result.

The problem is that coding agents implicitly hide core architectural decisions. The result is either (a) suboptimal architecture that would have benefitted from more steering by the engineer or (b) the engineer needs to parse chatbot conversations and lines of code.

This problem arises in both new project development and PRs to existing codebases.

Senior engineers need a higher-level interface to steer and verify system evolution before costs compound in implementation, maintenance, and PR review.

## Core thesis

In a world of coding agents, the primary value of senior engineers is to make sound architecture decisions that direct agent behavior and set guardrails for ongoing development.

Chat based coding agents hide many implicit architecture decisions. The engineer is left with a suboptimal design and an incomplete picture of the system.

A C4 architecture diagram is an effective control surface for steering coding agents.

## Primary user

Senior engineers / tech leads building **new systems** with AI coding agents.

## Positioning statement

Claude Architect helps senior engineers steer coding agents at planning time by turning architecture into an interactive control surface before code is written.

## Why now

Agent-written code is rapidly increasing PR volume.
The interface for engineering must move up the stack from line edits to architecture steering.

---

## Main integration point

**Coding agent planning mode.**

Invocation model:

- Default: auto-trigger Architect when the user is in planning context
- Manual override: `/architect`

In plan mode, the agent must produce:

1. Architecture diagram
2. Explanation of **WHY**
3. Evidence from plan assumptions/constraints

This gives the engineer a clear moment to critique and steer direction before implementation.

After architecture review, the agent must implement code according to the architecture diagram. If the agent discovers a reason to change the architecture during implementation, surface that to the engineer for review. A key principle is that the engineer should be aware of all architecture decisions.

**Trust gate:** no implementation starts until architecture state = `approved`. If architecture drift is detected during implementation, the workflow routes back to architecture review before continuing.

**Anthropic product angle:** the end-state is to build this as a single integrated Architect product inside Claude with Imagine built in (not a permanent multi-tool handoff flow).

## Bridge contract

### Inputs

- Engineer intent (text, rough diagram, or whiteboard photo)
- Constraints
- Optional project context references

### Outputs

- Semantic architecture artifact
- WHY / rationale
- Evidence (plan assumptions, constraints, tradeoffs)
- Open questions
- State marker

### State machine

- `proposed`
- `approved`
- `implementing`
- `drifted`

## Why this wedge

Instead of targeting engineers maintaining mature, complex systems, architect focuses on **greenfield builds** where architecture is still fluid.

This lowers the immediate requirement for perfect architecture extraction accuracy and maximizes value at the highest-leverage moment: **before implementation begins**.

---

## User research

### Hypotheses to test

Goal: invalidate or validate these as quickly as possible.

**Overall:** a visual architecture diagram will reduce time and increase quality of agent planning mode.

Phase 1:

1. **Strong architecture is important**: Engineers value a rigorous architecture and will invest time to get it right. Thoughtful planning yields better results from implementation.
   1. assumption: what is "better"? Low latency, lower maintenance, fewer errors in agent output because it has a stronger sense of how to reason?
2. **The best architecture comes from human:agent collaboration**: both players add value. The engineer feels augmented by the agent, but does not fully trust the agent either.
3. **Visual architecture diagrams are a faster medium to communicate key technical decisions**
   They help engineers quickly assess if the agent understands goals, tradeoffs, boundaries correctly. identify otherwise invisible architecture decisions made by the agent and steer the agent more effectively.

Phase 2: **Point-and-click feedback on the diagram is faster; or provides more contextual feedback to the agent; delivers better results.**

Phase 3: **Faster, safer, more legible evolution**: A semantic architecture representation establishes useful guardrails for ongoing development. Or at minimum, it provides useful PR diffs to accelerate PR reviews with confidence.

### Target personas

- **architects**: Dan, Moldy, etc
- **vibe coders**: Flor, Justin, Ian, etc

### Validation criteria (first 10 interviews)

- ≥70% report missing key architecture context in current plan-mode output at least occasionally
- ≥60% say they would use architecture steering in planning at least weekly
- ≥50% prefer diagram-assisted review over text-only planning output for major features### Questions

### Interview questions

1. Tell me about the last feature where you used an agent for planning.
2. What was your first prompt? What context did you give the agent?
3. Why did you provide that level of context? why not more, or less?
4. What did the agent get right/wrong in the first draft?
5. How many planning iterations did you do, and how long did planning take?
6. What signals told you “this is ready to implement”?
7. Did you request any diagrams? If yes, what changed after seeing it?
8. What architecture mistakes are hardest to catch when reading text-only plans?
9. Where did trust with the agent break, if at all?
10. If you had a clickable diagram of the architecture plan, what would you want to do first?
11. How often would you use this workflow (never / monthly / weekly / daily)?

## Success metrics

### Engine quality metrics

1. % of architecture claims with explicit evidence
2. Reviewer-rated trust/correctness of rationale
3. Hallucination rate on architecture claims (target: low and decreasing over rounds)

### Workflow utility metrics

1. % of planning sessions with at least one engineer-requested architectural change
2. Time to approved architecture plan
3. Engineer-rated confidence before implementation
4. % of implementation PRs matching approved architecture intent

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

### Phase 0 — Architecture engine + eval foundation (already built)

1. Semantic architecture generation skill exists
2. Structured output contract exists (model + views + summary + manifest)
3. Eval loop exists with scoring and reflections

### Phase 1 — Plan mode diagram + simple chat-based feedback

1. Engineer provides intent (text, rough diagram, or whiteboard photo)
2. Architect auto-triggers in planning mode (or user invokes `/architect`)
3. Agent runs planning mode and generates architecture diagram + WHY.
4. Agent writes the final output to a single file per the skill definition. (later, generate HTML diagram to support point and click comments)
5. **Prototype workflow (temporary):** Engineer uploads the output file to Claude Chat.
6. Claude Chat generates an interactive diagram using Claude Imagine.
7. Engineer reviews and gives feedback (MVP via chat with the coding agent; later point-and-click comments)
8. Agent iterates on plan + architecture
9. Engineer approves architecture
10. Agent implements

#### Personal milestones (publish observations)

1. Agent understanding of architecture
2. Utility of this vs `/init` (does this improve agent code output? does it improve engineer confidence in the system?)
3. State of the art diagram generators: Claude Imagine vs Codex Images vs HTML

### Phase 2 — Point-and-click feedback on diagram

Upgrade feedback from chat-only to direct, pointed diagram interaction.

1. Engineer enters **Comment Mode** (button or `C`) and clicks node/edge/canvas to annotate architectural concern
2. Comment is queued with associated `element_id`/`relationship_id` (or `null` for canvas clicks)
3. Engineer batch-submits comments; UI provides copy-ready JSON payload for the coding agent
4. Agent maps annotation to plan changes
5. Agent regenerates architecture + WHY
6. Engineer iterates until approval

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

---

## Product architecture

### Capability layer (architecture engine)

- Semantic architecture generation
- Evidence and confidence model
- Canonical model + derived views
- Evaluation loop with scoring and reflections

### Experience layer (Claude Architect UX)

- Planning-mode invocation (auto + manual override)
- Feedback and revision loop
- Approval gate before implementation
- Drift detection and return-to-review workflow
- Integrated diagram interaction experience

---

## Appendix C — Claude-native end-state

The long-term product should be a native Claude Architect experience with built-in Imagine interaction:

- no manual artifact upload for normal usage
- architecture generation, visualization, feedback, and revision in one integrated loop
- persistent architecture state across planning, implementation, and PR review
- first-class architecture diffs and risk flags in code review workflows
