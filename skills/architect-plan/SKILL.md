---
name: architect-plan
description: Architecture planning sidecar for Claude's native Plan Mode. Turn product requirements, constraints, team size, timeline, assumptions, and tradeoffs into canonical architecture artifacts and, when useful, an interactive diagram. Strongly consider this skill in Plan Mode when a user is planning a new or changing software system and asks for the architecture, system design, service breakdown, or technical plan before implementation, including prompts like "propose the architecture", "design the system", or "help me plan the architecture."
---

Use this skill for planning-mode architecture design.

This skill must emit the same artifact schema as `architect-init`.

## Plan Mode++ Contract (critical)

This skill is a planning sidecar, not a replacement planner.

- Direct slash invocation must still feel like normal planning:
  - if the user explicitly invokes `/architect-plan` or `/architect:plan`, do **not** treat that as permission to skip normal planning behavior
  - do **not** start by writing `architecture/*.yaml` files
  - when high-impact architecture choices are unresolved, ask 1-3 focused architecture-shaping questions first, with clear recommendations when possible
  - produce the first serious visible architecture draft before writing hidden artifacts
- Preserve Claude's native Plan Mode behavior:
  - keep Claude's normal questioning pattern before planning
  - keep Claude's normal planning structure, tone, and approval flow
  - keep Claude's natural use of tables, ASCII/system breakdowns, and long-form architecture sections when Claude would normally choose them
  - keep `Open Decisions` visible when the design is not yet locked
- Do **not** introduce an Architect-owned visible planning framework:
  - no bespoke Architect response template
  - no second approval loop
  - no artifact walkthrough dump unless the user explicitly asks for artifact detail
- Treat artifact generation as mostly behind-the-scenes work.
- Use a two-track output model:
  - hidden track: contract-conformant architecture artifacts
  - visible track: ordinary Claude Plan Mode output
- The user-facing response should remain Claude's normal plan. Architect should add only a small diagram handoff when a diagram is actually produced.
- Do **not** let the hidden artifact schema leak into the visible plan by default:
  - avoid artifact-oriented headings such as `Canonical Architecture Model`, `Repo Archetype`, `Data Ownership`, or `Files to Create` unless the user explicitly asks for artifact detail
  - do not expose stable IDs, coverage hints, evidence IDs, output-root details, or artifact file inventories in the visible plan
- Only surface `manifest.yaml`, `model.yaml`, `views/*.yaml`, `summary.md`, or validation details when:
  - the user explicitly asks for them, or
  - they are needed to explain a blocker or important tradeoff
- `summary.md` may still contain structured sections such as `Key Decisions`, but that artifact structure must **not** dictate the assistant's user-facing response shape.
- In native Plan Mode, stay in native Plan Mode for the planning conversation.
- For diagram generation in native Plan Mode:
  - finish the normal Plan Mode response first
  - ask the handoff question at the end:
    `Do you want to review an interactive <strong><span style="color: #2563eb;">architecture diagram</span></strong>?`
  - prefer to place that CTA as the final user-visible sentence
  - if the environment emits a recap, summary, or `/plan` preview after the main draft, include the CTA there so it still lands at the very end
  - if the user says yes, `draw the diagram`, or any equivalent affirmative response, treat that as explicit approval to write the architecture artifacts and render the diagram in the current Plan Mode session
  - treat that same approval as permission for the full diagram-generation pass in the current session:
    - required file writes and edits for architecture artifacts
    - required bash/script commands for validation and rendering
    - appending the diagram link section to the Plan Mode document when present
  - stay in Plan Mode and proceed with the writes; do **not** ask the user to exit Plan Mode first, and do **not** preemptively assume writes are blocked
  - do **not** ask the user to separately approve the plan in order to write artifacts or render the diagram
  - it is acceptable to think or say, in effect, "Plan Mode is still active but the user approved. Let me write the architecture artifacts and render the diagram."
  - do **not** mention internal tool names such as `ExitPlanMode`, and do **not** describe tool availability
  - do **not** ask for additional per-command approval for those diagram operations once the user has said yes
  - only if an actual write/edit/bash action is denied after trying should you fall back to a plain user-facing handoff to exit Plan Mode
- When used outside native Plan Mode with a separate "behave like Plan Mode" system prompt, continue following this same sidecar contract.

## Required Output Contract

Before writing hidden artifact outputs, read [../references/architecture-contract.md](../references/architecture-contract.md) and follow it exactly.

Do **not** front-load this contract read before the first visible architecture draft in normal plan-mode use.

Resolve the contract through the skill-relative reference path only.

- In the repo checkout, use `../references/architecture-contract.md`.
- In plugin installs, use the mirrored skill reference shipped with the plugin at `skills/references/architecture-contract.md`.
- If that lookup fails, stop and report the missing contract path.
- Do **not** run a repo-wide search for alternate contract files, artifact examples, `manifest.yaml`, `model.yaml`, or nearby architecture outputs.

Default output path:

- `architecture/manifest.yaml`
- `architecture/model.yaml`
- `architecture/views/*.yaml`
- `architecture/summary.md`
- `architecture/diff.yaml` in update mode only
- `architecture/diagram.html` (primary interactive diagram)
- `architecture/diagram-prompt.md` only when explicitly requested

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
- For greenfield planning or direct `/architect-plan` invocation, do **not** start by exploring the current project directory, reading repo docs, reading the architecture contract, reading examples/evals, or spawning Explore agents unless the user explicitly asks for repo-aware tailoring or artifact-only regeneration.
- Unless the user explicitly asks for examples or eval analysis, do **not** read from `evals/`, `examples/`, `iteration-*`, `skill-snapshot/`, or similar archive/snapshot directories to infer the contract or bootstrap artifacts.
- The host planner owns the visible planning conversation. This skill owns artifact generation only.
- Build one canonical model first, then derive views.
- Use explicit confidence levels: `confirmed`, `strong_inference`, `weak_inference`.
- For planning-only runs, set `evidence_basis: plan` in `manifest.yaml`.
- Encode plan evidence in shared schema using `plan://...` evidence paths and plan evidence kinds.
- Keep `architecture_state` simple:
  - default `proposed`
  - set `approved` only when the user explicitly approves
  - do not auto-transition to `implementing`; the end user decides when implementation starts
  - do not require `architecture_state: approved` before writing artifacts or rendering the diagram; `proposed` is the normal review state
- Follow the host planner's feedback/revision loop instead of creating a second one.
- Preserve stable IDs across revisions for unchanged architecture concepts.
- Do not collapse distinct responsibilities into one generic container when separation is a key decision (for example: keep webhook, notification, and audit processing distinct unless there is explicit rationale to merge).
- `summary.md` must include a **Key Decisions** section, and each key decision should include explicit coverage hints using `covers: <id1,id2,...>` referencing element/relationship/view IDs when possible.
- Run decision coverage, decomposition policy, and semantic drift checks before finalizing revisions:
  - `skills/architect-plan/scripts/decision-coverage-check.py`
  - `skills/architect-plan/scripts/container-decomposition-check.py`
  - `skills/architect-plan/scripts/semantic-diff-gate.py` (when a baseline model exists)
- Record unknowns; do NOT fabricate precision. This is critical.
- Follow C4 boundary rules and avoid mixed abstraction levels in one view.
- Do not suppress Claude's normal use of tables or ASCII/system breakdowns in the visible plan.
- Do not mirror the artifact schema or `summary.md` structure in the visible plan unless the user explicitly asks for artifact detail.
- Do not replace a natural architecture plan with canonical-model tables simply because the artifacts exist behind the scenes.
- Do not make `Write(architecture/...)` the first visible action of the skill unless the user explicitly asked for artifact-only regeneration.
- If focused questions are needed and a special question tool is unavailable, ask the questions plainly in chat. Do **not** narrate internal tool availability, deferred tool state, or hidden control flow.
- Do not narrate internal exploration steps such as "reading the contract," "exploring current project state," or "internalizing patterns" in the visible response.
- Avoid meta transition lines such as "I have enough context to proceed," "Let me write the plan now," or similar status narration when moving from defaults/questions into the architecture draft.
- Use `architect-diagram` only after the first serious architecture draft, and only when a diagram materially improves the plan:
  - render for large systems, multiple runtime boundaries, async flows, or cross-system integrations
  - render when the architecture is large or ambiguous enough that a visual will reduce confusion
  - render when the user explicitly asks for a diagram
  - skip rendering when the plan is simple enough that a diagram would add little value
- If a diagram is rendered, keep the user-visible mention to one compact appended section.
- Use demo mode in `architect-diagram` when explicit demo-quality output is requested; otherwise keep default fallback-friendly rendering behavior for iterative runs.

## Workflow

### 1) Ask focused architecture-shaping questions when needed

Before writing any hidden artifacts or reading any artifact contracts/examples, decide whether there are unresolved high-impact choices that would materially change the plan.

Normal greenfield/direct-plan behavior:

- start from the user's prompt, constraints, and any immediately obvious context
- ask focused questions when they materially change the architecture
- do **not** begin with repo exploration or contract study just to "get oriented"

Examples:

- platform/language choice
- tenancy model
- compliance/security bar
- sequencing vs parallelism in the workflow
- public API vs internal/admin-only product assumptions

If those choices are unresolved:

- ask 1-3 focused questions first
- keep the questions short and decisive
- recommend a default when possible

If the necessary choices are already clear from context, skip this step.

### 2) Produce the first visible architecture draft

Write the visible plan in ordinary Claude style before writing hidden artifacts.

Visible-plan rules:

- keep the response user-facing and decision-oriented
- use Claude's natural structure
- keep `Open Decisions` visible when the design is not yet locked
- do not expose artifact schema, IDs, evidence keys, file inventories, or contract mechanics
- do not mention internal repo exploration, contract-reading, tool availability, or hidden artifact workflow

Only after this first serious visible draft exists should you start externalizing hidden artifacts.

### 3) Frame hidden artifact scope and mode

Only now, if you are actually going to write hidden artifacts, read `../references/architecture-contract.md` and conform to it.

Define:

- system in scope
- intended audience(s)
- output path
- mode: `initial` or `update`

If existing architecture artifacts are provided in update mode, preserve stable IDs and emit `diff.yaml`.

### 4) Build planning evidence ledger

Create an internal ledger of planning evidence IDs before writing YAML.

Recommended IDs:

- `req-*` requirements
- `con-*` constraints
- `asm-*` assumptions
- `trd-*` tradeoffs

Map each modeled claim to at least one evidence ID.

### 5) Model runtime boundaries + ownership

Define canonical elements and relationships from planning input:

- runtime/deployable boundaries
- data ownership and system of record
- critical request/async workflows
- key external dependencies

Use conservative confidence for uncertain claims.

### 6) Write canonical model

Write `architecture/model.yaml` first.

Do not write view-local facts that conflict with the canonical model.

### 7) Derive minimal useful views

Emit only views that improve understanding:

- always: `system-context`
- usually: `container`
- only when useful: `component-*`, `sequence-*`, `deployment`

Every container should support drill-down when it has meaningful, evidenced internal boundaries.

### 8) Write summary and optional diff

Write `summary.md` using the fixed shared structure.

In `summary.md`, ensure **Key Decisions** uses explicit coverage hints where possible, for example:

- `- [DEC-001] Separate webhook service from notification service | covers: container-webhook-service,container-notification-service,view-container`

In update mode, write `diff.yaml`.

This structure is for the hidden artifact package only. Do **not** copy these artifact headings or coverage-hint patterns into the visible Claude plan by default.

### 9) Render diagram outputs when the draft is ready

After the first serious architecture draft, decide whether the plan is complex enough that a visual adds clarity. If yes, invoke `architect-diagram` using the same output root.

Expected default visible output in the artifact package:

- `architecture/diagram.html` (primary interactive diagram)

Optional (only if explicitly requested by user):

- `architecture/diagram-prompt.md` via `architect-diagram-prompt`

If you render a diagram and workspace writes are available, surface it in the planning response as one compact appended section, for example:

```md
## Architecture Diagram
[Open architecture diagram](/absolute/path/to/architecture/diagram.html)
Comment directly on the diagram to give me feedback on the plan. I'll reply to your comments here.
```

Keep this section short. Do not turn the overall response into an artifact tour.

If the environment has created a Plan Mode document for the current plan, append the same short `Architecture Diagram` section to that document after `architecture/diagram.html` has been rendered, so the plan document itself links to the HTML file.

If workspace writes are blocked in native Plan Mode, do **not** replace this with a "deferred" note. Finish the normal plan, then ask the exact handoff question from the Plan Mode++ contract.

### 10) Stay synchronized with the host planning loop

After producing a draft or revision:

- let the host planner handle the user-facing feedback loop
- apply planning feedback to the artifacts and rerender the diagram when the architecture changes
- keep `architecture_state: proposed` during iteration
- preserve stable IDs for unchanged elements and relationships
- run Step 9 validation after each revision

Do not start a second approval loop. The host planner owns approval.

### 11) Validate

Before presenting for approval or finishing any iteration, verify:

- all view element/relationship IDs resolve in `model.yaml`
- sequence participants and steps resolve in `model.yaml`
- ownership + system-of-record fields are explicit for major entities
- no cross-parent component mixing in component views
- no duplicated system-of-record assignments without explicit justification
- decision coverage check passes (strict mode):
  - `python3 skills/architect-plan/scripts/decision-coverage-check.py --summary <output-root>/architecture/summary.md --model <output-root>/architecture/model.yaml --views-dir <output-root>/architecture/views --strict`
- container decomposition policy check passes (strict mode):
  - `python3 skills/architect-plan/scripts/container-decomposition-check.py --model <output-root>/architecture/model.yaml --summary <output-root>/architecture/summary.md --strict --only-when-mentioned`
- semantic drift gate passes when a baseline model exists:
  - `python3 skills/architect-plan/scripts/semantic-diff-gate.py --baseline <previous>/architecture/model.yaml --current <output-root>/architecture/model.yaml`
  - by default, do not allow name-stable ID shifts unless explicitly justified.
- when a diagram was rendered, `architecture/diagram.html` exists and corresponds to the current artifact set
- if requested, `architecture/diagram-prompt.md` exists and corresponds to the current artifact set

## Handoffs

- If the user needs architecture from an existing repo, hand off to `architect-init`.
- Use `architect-diagram` directly inside this skill for normal planning flow.
- Use `architect-diagram-prompt` only when user explicitly requests `diagram-prompt.md` generation.
- Treat diagram generation as a separate handoff only when the user explicitly requests diagram-only regeneration from existing artifacts.

## Completion Standard

Complete only when:

1. all artifacts conform to `../references/architecture-contract.md`
2. `manifest.yaml` includes `generated_by_skill: architect-plan`
3. planning evidence is explicit in `evidence` and confidence fields
4. `architecture_state` is present and accurately reflects explicit user approval state
5. feedback from the host planning loop has been incorporated when feedback is provided
6. when the plan is large/complex enough or the user requested a diagram, `architecture/diagram.html` has been generated for the current approved/proposed revision
7. if requested, `architecture/diagram-prompt.md` has been generated for the current approved/proposed revision
8. decision coverage check passes in strict mode for current artifacts
9. container decomposition policy check passes in strict mode for current artifacts
10. semantic drift gate passes for revision runs when baseline model is available (including name-stable ID checks)


## Sequence View Policy (default)

- Do not generate sequence views by default.
- Generate sequence views only when the user explicitly requests them.
