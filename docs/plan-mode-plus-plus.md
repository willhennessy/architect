# Claude Plan Mode ++

This doc defines the prompt stack for making Architect feel like a small enhancement to native Claude Plan Mode instead of a competing planner.

Important implementation note:

- direct slash invocation (`/architect-plan` or `/architect:plan`) must still preserve normal planning behavior
- the crucial behavior must live in `SKILL.md`, not only in `agents/openai.yaml`
- otherwise Claude may treat the skill invocation as permission to start writing artifacts immediately

## Goal

Preserve normal Claude Plan Mode behavior and add two quiet capabilities:

- Architect can externalize the architecture into contract-conformant artifacts
- Architect can render `architecture/diagram.html` when a visual would materially improve a large or complex plan

The user should still feel like they are talking to normal Claude Plan Mode.

## Fresh baseline

Fresh baseline to preserve:

User-provided fresh DocSign Plan Mode output on 2026-04-19 showed that native Claude Plan Mode:

- asked a few focused architecture-shaping questions up front, with clear recommendations
- produced a long-form architecture plan in Claude's own voice
- naturally used sections such as context, system components, data models, flows, infra, roadmap, and verification
- used tables and ASCII/system breakdowns when helpful
- ended with explicit `Open Decisions`
- did **not** dump artifacts or introduce a second planning framework
- did **not** expose artifact-schema headings like `Canonical Architecture Model` or stable model IDs

That is the canonical baseline to preserve. This replaces the earlier TL;DR-oriented baseline.

## Prompt stack

### 1) Preferred: native Plan Mode delta

Use this as the small additive prompt when Claude is already in native Plan Mode:

```text
Stay in Claude's normal Plan Mode behavior. Use Architect only as a behind-the-scenes architecture sidecar: capture the architecture in contract-conformant artifacts, and, for large or complex plans, render architecture/diagram.html after the first serious draft. Preserve your normal questioning style, planning structure, tone, approval flow, and use of open decisions. Do not replace the response with an Architect-specific template, artifact walkthrough, canonical-model dump, or second review loop. Keep artifact details hidden unless the user asks. Do not surface artifact-oriented headings like "Canonical Architecture Model", "Repo Archetype", "Data Ownership", or file inventories unless the user asks for artifact detail. Avoid meta transition lines like "I have enough context to proceed" or "Let me write the plan now." At the end of the normal plan, ask: `Do you want to review an interactive <strong><span style="color: #2563eb;">architecture diagram</span></strong>?` Prefer to place that CTA as the final user-visible sentence, and if the environment emits a recap or summary after the main draft, include the CTA there so it still lands at the very end. If the user says yes, `draw the diagram`, or any equivalent affirmative response, treat that as explicit approval and permission for the full diagram-generation pass in the current Plan Mode session, including required artifact writes, bash/script commands, validation, rendering, and plan-document link updates. Stay in Plan Mode and try the writes; do not preemptively refuse, do not ask the user to exit first, do not ask the user to separately approve the plan before writing artifacts or rendering the diagram, do not ask for additional per-command approval for those diagram operations, and do not mention internal tool names or tool availability. Proposed-state artifacts are valid review outputs; do not require `architecture_state: approved` before writing them. Only if an actual write/edit/bash action is denied after trying should you fall back to a plain request to exit Plan Mode.
```

### 2) Fallback: Plan Mode compatibility shim

Use this only when native Plan Mode cannot be used but Architect still needs write access for artifacts/diagram output:

```text
Behave like Claude's normal Plan Mode: ask a few focused architecture-shaping questions up front when needed, stay at planning level, produce the same kind of long-form architecture plan Claude would normally produce, and surface open decisions when the design is not yet locked. Architect is available only as a sidecar for writing architecture artifacts and, for large or complex systems, rendering architecture/diagram.html after the first serious draft. Do not invent a separate Architect planning template, artifact walkthrough, or approval loop. If the user approves diagram generation, try to write the artifacts and render the diagram in the current planning session first. Only if an actual write/edit/bash action is denied after trying should you ask to leave the current planning mode.
```

### 3) Skill contract

`architect-plan` itself should carry these rules:

- preserve the host planner's visible behavior
- treat artifact generation as behind-the-scenes work
- never own the approval loop
- direct slash invocation still asks focused questions first when needed
- visible plan draft comes before hidden artifact writes
- direct slash invocation should not start with repo exploration, contract reading, example/eval review, or tool-status narration
- only render diagrams for large/complex plans or explicit diagram requests
- when writes are blocked, ask the explicit end-of-plan handoff question instead of forcing an early mode switch

## Diagram trigger

Render `architecture/diagram.html` only after the first serious architecture draft, and only when any of these are true:

- the system has multiple runtime boundaries
- async flows matter to the design
- there are important cross-system integrations
- the architecture is large enough that a visual reduces ambiguity
- the user asks for a diagram

Skip the diagram only when the plan is small enough that the visual adds little value.

## Visible response contract

Default user-visible output should be:

1. native Claude Plan Mode response
2. optional tiny appended diagram section when a diagram was actually rendered

Preferred shape:

```md
## Architecture Diagram
[Open architecture diagram](/absolute/path/to/architecture/diagram.html)
Use Comment Mode there for feedback on boundaries, ownership, and risky flows.
```

If the environment creates a Plan Mode document, append the same short `Architecture Diagram` section to that document after the HTML file is rendered, so the doc links directly to `diagram.html`.

At the end of the normal plan:

```html
Do you want to review an interactive <strong><span style="color: #2563eb;">architecture diagram</span></strong>?
```

If the user says yes, `draw the diagram`, or equivalent:

```html
Plan Mode is still active, but the user approved. Let me write the architecture artifacts and render the interactive <strong><span style="color: #2563eb;">architecture diagram</span></strong>.
```

That yes should also count as permission for the full diagram-generation pass:

- required artifact writes/edits
- required bash/script commands for validation and rendering
- appending the diagram link section to the saved plan document when present

Only if an actual write attempt is denied:

```html
Please exit Plan Mode using the UI or `/exit`, and I'll generate the interactive <strong><span style="color: #2563eb;">architecture diagram</span></strong> right away and add its link to the plan document.
```

## Anti-patterns

Avoid these:

- replacing the normal plan with an Architect-specific template
- leaking the hidden artifact schema into the visible plan
- dumping `manifest.yaml`, `model.yaml`, and view file details into the chat by default
- inventing a second review loop owned by the skill
- opening with "Let me explore the current project state/read the architecture contract before drafting anything"
- narrating internal tool availability, deferred tool state, or contract-internalization steps
- saying `ExitPlanMode isn't available` or otherwise surfacing internal tool availability to the user
- preemptively refusing to write after the user approved the diagram because you assume Plan Mode blocks writes
- asking the user to separately approve the plan before writing proposed-state artifacts and the diagram
- asking for additional per-command approval after the user already approved the diagram pass
- transition filler like "I have enough context to proceed" or "Let me write the plan now"
- burying the diagram CTA before a later recap/summary so it no longer appears at the very end
- telling the user to leave Plan Mode before the normal plan is finished
- making the diagram section larger than the plan itself
