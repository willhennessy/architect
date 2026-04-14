---
name: architect-plan
description: Generate a planning-time architecture proposal (before implementation) from user intent, constraints, assumptions, and tradeoffs; iterate with engineer feedback until explicit approval; emit canonical architecture artifacts and automatically render an HTML diagram via architect-diagram. Use when the user is designing a new system or major feature and wants architecture steering - especially use in Plan Mode.
---

Use this skill for planning-mode architecture design.

This skill must emit the same artifact schema as `architect-discover`.

## Required Output Contract

Before writing outputs, read [../references/architecture-contract.md](../references/architecture-contract.md) and follow it exactly.

Default output path:

- `architecture/manifest.yaml`
- `architecture/model.yaml`
- `architecture/views/*.yaml`
- `architecture/summary.md`
- `architecture/diff.yaml` in update mode only

If the user specifies another path, honor it.

## Input Contract (minimal)

Collect and normalize:

- product/system intent
- requirements and constraints
- non-functional constraints (latency, reliability, cost, security, compliance)
- assumptions and tradeoffs
- optional rough diagram or whiteboard input

If critical constraints are missing, record unknowns explicitly instead of inventing answers.

## Hard Rules

- Keep implementation out of scope. This skill stops at architecture artifacts + rendered diagram outputs.
- Do not require a repository scan for normal plan-mode use.
- Build one canonical model first, then derive views.
- Use explicit confidence levels: `confirmed`, `strong_inference`, `weak_inference`.
- For planning-only runs, set `evidence_basis: plan` in `manifest.yaml`.
- Encode plan evidence in shared schema using `plan://...` evidence paths and plan evidence kinds.
- Keep `architecture_state` simple:
  - default `proposed`
  - set `approved` only when the user explicitly approves
  - do not auto-transition to `implementing`; the end user decides when implementation starts
- Run an explicit engineer feedback/revision loop until approval.
- Preserve stable IDs across revisions for unchanged architecture concepts.
- Record unknowns; do not fabricate precision.
- Follow C4 boundary rules and avoid mixed abstraction levels in one view.
- In Plan Mode, do **not** present ASCII architecture diagrams as the primary visualization.
- After every draft/revision of architecture artifacts, automatically invoke `architect-diagram` so HTML diagram rendering is a fluid part of planning.

## Workflow

### 1) Frame scope and mode

Define:

- system in scope
- intended audience(s)
- output path
- mode: `initial` or `update`

If existing architecture artifacts are provided in update mode, preserve stable IDs and emit `diff.yaml`.

### 2) Build planning evidence ledger

Create an internal ledger of planning evidence IDs before writing YAML.

Recommended IDs:

- `req-*` requirements
- `con-*` constraints
- `asm-*` assumptions
- `trd-*` tradeoffs

Map each modeled claim to at least one evidence ID.

### 3) Model runtime boundaries + ownership

Define canonical elements and relationships from planning input:

- runtime/deployable boundaries
- data ownership and system of record
- critical request/async workflows
- key external dependencies

Use conservative confidence for uncertain claims.

### 4) Write canonical model

Write `architecture/model.yaml` first.

Do not write view-local facts that conflict with the canonical model.

### 5) Derive minimal useful views

Emit only views that improve understanding:

- always: `system-context`
- usually: `container`
- only when useful: `component-*`, `sequence-*`, `deployment`

### 6) Write summary and optional diff

Write `summary.md` using the fixed shared structure.

In update mode, write `diff.yaml`.

### 7) Render diagram outputs (required)

Immediately after writing/updating architecture artifacts, invoke `architect-diagram` using the same output root.

Expected outputs in output root:

- `diagram.html` (primary interactive diagram)
- `diagram-prompt.md` (secondary upload bundle)

Present the rendered diagram as part of the same planning response. The diagram step must feel automatic, not user-triggered.

### 8) Engineer feedback and revision loop

After producing a draft:

- present the architecture artifacts, rendered diagram, rationale, and unknowns to the engineer
- ask for targeted feedback on boundaries, ownership, risks, and tradeoffs
- apply feedback and regenerate artifacts
- rerun Step 7 so diagram output stays in sync with latest architecture
- keep `architecture_state: proposed` during iteration
- preserve stable IDs for unchanged elements and relationships
- run Step 9 validation after each revision

Repeat until the engineer explicitly approves.

### 9) Validate

Before presenting for approval or finishing any iteration, verify:

- all view element/relationship IDs resolve in `model.yaml`
- sequence participants and steps resolve in `model.yaml`
- ownership + system-of-record fields are explicit for major entities
- no cross-parent component mixing in component views
- no duplicated system-of-record assignments without explicit justification
- `diagram.html` and `diagram-prompt.md` exist and correspond to the current artifact set

## Handoffs

- If the user needs architecture from an existing repo, hand off to `architect-discover`.
- Use `architect-diagram` directly inside this skill for normal planning flow; only treat diagram generation as a separate handoff when the user explicitly requests diagram-only regeneration from existing artifacts.

## Completion Standard

Complete only when:

1. all artifacts conform to `../references/architecture-contract.md`
2. `manifest.yaml` includes `generated_by_skill: architect-plan`
3. planning evidence is explicit in `evidence` and confidence fields
4. `architecture_state` is present and accurately reflects explicit user approval state
5. engineer feedback has been incorporated through at least one explicit feedback/revision cycle when feedback is provided
6. `diagram.html` and `diagram-prompt.md` have been generated for the current approved/proposed revision
