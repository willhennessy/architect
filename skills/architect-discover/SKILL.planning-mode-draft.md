---
name: architect-discover
description: Architecture steering for coding-agent planning plus codebase architecture discovery. Use this skill when: (1) planning a new system/feature with an AI coding agent and you want architecture-first steering before implementation, or (2) discovering/modeling architecture from an existing codebase. Produces a canonical semantic architecture model, rationale (WHY), evidence, and state-gated handoff artifacts.
---

# Architect Skill (Planning-Mode + Discovery)

This skill has two operating modes:

1. **planning mode** (default for greenfield/new-feature planning)
2. **discovery mode** (existing repo architecture extraction; former behavior)

The source of truth is always a canonical semantic architecture model. Diagrams are render targets, not the source of truth.

---

## Outcome

Produce grounded architecture artifacts that enable an engineer to steer agent behavior before code is written, and maintain architecture coherence over time.

Minimum output artifacts:

1. `architecture/model.yaml`
2. `architecture/manifest.yaml`
3. `architecture/summary.md`
4. `architecture/views/*.yaml` as needed
5. `architecture/diff.yaml` in update mode only

Planning-mode additionally requires:

6. `architecture/decision-log.yaml` (WHY + tradeoffs + open questions)
7. explicit `state` marker in manifest: `proposed|approved|implementing|drifted`

---

## Mode selection

Select mode from context:

- **planning mode** if the user is planning a new system/feature, asks for architecture before implementation, or is in plan mode
- **discovery mode** if the user asks to inspect/model an existing repo’s architecture

If ambiguous, ask one clarifying question:
- “Should I generate architecture from your intent (planning mode) or infer it from existing code (discovery mode)?”

---

## Trust gate (mandatory)

- No implementation starts until architecture state = `approved`.
- If implementation reveals architecture drift, set state = `drifted`, surface the reason, and route back to architecture review.
- Do not silently absorb major architecture changes during implementation.

---

## Planning mode workflow (new)

### 1) Frame intent
Capture:
- goal
- constraints
- assumptions
- explicit non-goals
- optional context refs (docs, whiteboard photo, rough diagram)

### 2) Propose architecture
Generate:
- canonical model (`model.yaml`)
- required views (smallest useful set)
- `decision-log.yaml` with:
  - key decisions
  - rationale (WHY)
  - tradeoffs
  - confidence per claim
  - open questions

### 3) Evidence discipline (planning evidence)
In planning mode, evidence is plan evidence first:
- requirements
- constraints
- assumptions
- tradeoffs

Do not fabricate code-level evidence if code does not exist yet.

### 4) Feedback iteration
On feedback:
- map feedback to concrete model deltas
- regenerate model + decision-log
- summarize what changed and why
- keep state `proposed` until explicit approval

### 5) Approval handoff
When user approves:
- set state `approved`
- emit implementation handoff contract in summary:
  - guardrails
  - boundaries not to violate
  - known risks

### 6) Drift handling
If drift detected during implementation:
- set state `drifted`
- produce drift summary
- request review loop before continuing

---

## Discovery mode workflow (existing behavior)

Use the existing extraction pipeline for unfamiliar codebases:
- classify repo archetype
- build canonical model first
- derive strict-level views
- enforce confidence + evidence hierarchy
- write summary + manifest + optional diff

(Keep existing hard rules and validation behavior from prior version.)

---

## Required output contract

Before writing outputs, read:
- `references/output-format.md`

Use schemas exactly.

Default output path:
- `architecture/manifest.yaml`
- `architecture/model.yaml`
- `architecture/views/*.yaml`
- `architecture/summary.md`
- `architecture/diff.yaml` (update mode)
- `architecture/decision-log.yaml` (planning mode)

---

## Manifest requirements (updated)

`manifest.yaml` must include:
- `mode: planning|discovery`
- `state: proposed|approved|implementing|drifted`
- `evidence_type: plan|code|mixed`
- stable artifact paths

---

## Hard rules (carry forward + additions)

- Explore first, infer second, write last.
- Build one canonical model, derive views from it.
- Keep C4 abstraction boundaries strict.
- Use confidence levels: `confirmed|strong_inference|weak_inference`.
- Record unknowns instead of guessing.
- Sequence participants must exist in model.
- Treat data ownership/system-of-record as first-class.
- In planning mode, never pretend assumptions are confirmed code facts.
- Enforce trust gate and drift routing.

---

## Diagram rendering policy

Architecture model is primary. Rendering is swappable.

- MVP/prototype may use Claude Chat/Imagine via bundled prompt file
- Later, render natively in integrated Architect UX

Do not make rendering format the source of truth.

---

## Validation checklist additions

In addition to existing validation checks, verify:
- mode is correctly set (`planning` or `discovery`)
- planning mode includes `decision-log.yaml`
- manifest includes valid state value
- no implementation handoff is emitted as approved unless state = `approved`
- drift transitions set state to `drifted` and include reason

---

## Common mistakes to avoid (additions)

Do not:
- run discovery-heavy repo scans when user asked for intent-first planning
- treat speculative planning assumptions as confirmed runtime truth
- skip explicit architecture approval before implementation
- hide implementation-time architecture deviations
