---
name: architect-diagram
description: Generate an interactive HTML architecture diagram (`diagram.html`) with drill-down navigation and Comment Mode as the primary output, plus a secondary Claude Imagine upload bundle (`diagram-prompt.md`), from existing architecture artifacts (`manifest.yaml`, `model.yaml`, and views). Use after architect-plan or architect-discover has generated architecture artifacts.
---

Use this skill only after architecture artifacts already exist.

## Inputs

- output root path containing `architecture/`
- generated architecture artifacts:
  - `architecture/manifest.yaml`
  - `architecture/model.yaml`
  - `architecture/views/*.yaml`
  - `architecture/summary.md`
  - optional `architecture/diff.yaml`

## Outputs

Required:

- `<output-root>/diagram.html` (primary)
- `<output-root>/diagram-prompt.md` (secondary)

## Hard Rules

- Do not invent architecture facts.
- Source all content from the provided artifacts.
- Preserve exact IDs and paths from source artifacts.
- `diagram.html` must be fully self-contained (inline CSS/JS; no external dependencies).
- `diagram.html` must support drill-down navigation from available view hierarchy and breadcrumb/back navigation.
- `diagram.html` must implement Comment Mode (`Comment` toggle + `C` shortcut + comment queue + submit modal JSON handoff).
- Use stable element metadata in HTML (`data-element-id`, `data-view-id`, and relationship metadata where applicable).
- `diagram-prompt.md` must include the exact top heading required by the output contract and a zero-text upload execution instruction directly below it.

## Workflow

1. **Validate output requirements**
   - Read [references/diagram-output-contract.md](references/diagram-output-contract.md).
   - Verify the output root and required architecture artifact paths exist.

2. **Load architecture artifacts**
   - Read `manifest.yaml`, `model.yaml`, `summary.md`, and available `views/*.yaml` (plus optional `diff.yaml`).

3. **Build drill-down mapping from artifacts**
   - Derive hierarchy and drill-down transitions from manifest/view files.
   - Keep sequence views separate from drill-down hierarchy.

4. **Render primary HTML diagram**
   - Read [references/html-diagram-spec.md](references/html-diagram-spec.md).
   - Read [references/comment-handoff-format.md](references/comment-handoff-format.md).
   - Optionally reuse interaction patterns from [references/comment-mode-reference.html](references/comment-mode-reference.html).
   - Generate `<output-root>/diagram.html` from architecture artifacts.

5. **Render secondary Claude Imagine prompt bundle**
   - Read [references/interactive-diagram-prompt.md](references/interactive-diagram-prompt.md).
   - Generate `<output-root>/diagram-prompt.md` per `diagram-output-contract.md`.

6. **Run contract checks only when needed**
   - If artifact shape is ambiguous or inconsistent, read [../references/architecture-contract.md](../references/architecture-contract.md) to resolve schema expectations.
   - If unresolved issues remain, record them explicitly instead of guessing.

7. **Run final validation checklist**
   - Execute the checklist in `diagram-output-contract.md` before completing.

## Completion Standard

Complete only when `diagram.html` and `diagram-prompt.md` both exist, are grounded in the same architecture artifacts, and pass the validation checklist.