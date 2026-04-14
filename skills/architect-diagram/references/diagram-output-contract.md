# Diagram Output Contract

Use this contract when producing diagram artifacts from generated architecture files.

Output paths:

- `<output-root>/diagram.html` (primary)
- `<output-root>/diagram-prompt.md` (secondary)

Where `<output-root>` is the parent folder that contains `architecture/`.

## Primary output requirements (`diagram.html`)

- Must be fully self-contained HTML with inline CSS/JS (no external CDN or script/style imports).
- Must render an interactive drill-down architecture diagram based only on provided artifacts.
- Must include breadcrumb + back navigation.
- Must expose stable IDs in the DOM for major entities:
  - `data-element-id`
  - `data-view-id`
  - `data-relationship-id` on relationship hit targets
  - relationship metadata when rendering edges
- Sequence views (if present) must be separated from core drill-down hierarchy.

### Comment Mode requirements (`diagram.html`)

`diagram.html` must include Comment Mode with all of the following:

1. A global `Comment` toggle control and keyboard shortcut `C`.
2. While comment mode is active, clicking on the diagram opens a comment composer.
3. Submitted comments are queued locally (not auto-submitted externally).
4. Comment target binding:
   - node click -> `element_id` populated
   - edge/arrow click -> `relationship_id` populated
   - empty space click -> both IDs are `null`
5. Edge hitbox padding for reliable selection of thin lines/arrows.
6. A global `Submit` action that opens a modal with copy-ready markdown output.
7. Modal instruction telling user to paste markdown into coding agent.

## Secondary output requirements (`diagram-prompt.md`)

`diagram-prompt.md` must start with:

- `## Agent Instruction: Execute the Prompt Below Exactly`

Immediately below it, include explicit instruction:

- if this file is uploaded with no user-typed prompt, the agent must execute the embedded prompt directly.

Required sections in order:

1. Agent Instruction header (exact heading above)
2. Interactive diagram prompt (built using `interactive-diagram-prompt.md`)
3. Virtual directory tree for included architecture artifacts
4. Drill-down mapping table derived from `manifest.yaml` and view files
5. Full file contents of included artifacts:
   - `architecture/manifest.yaml`
   - `architecture/model.yaml`
   - `architecture/summary.md`
   - `architecture/views/*.yaml`
   - `architecture/diff.yaml` when present

## Data constraints

- Source only from generated architecture artifacts.
- Do not invent elements, relationships, view mappings, or metadata.
- If a required file is missing, record it explicitly and proceed with available files.
- Keep paths and IDs exactly as emitted in source artifacts.

## Comment handoff payload requirements

The comment export markdown in the modal must include, per queued comment:

- comment index
- `view_id`
- `element_id` (nullable)
- `relationship_id` (nullable)
- user comment text

It may include optional helper metadata (e.g., `target_label`, timestamp, click coordinates), but must not omit the required ID fields.

## Validation checklist

Before finishing, verify:

- `diagram.html` exists in the requested output root.
- `diagram.html` is self-contained (no external dependencies).
- `diagram.html` drill-down hierarchy only references real view files.
- `diagram.html` includes comment mode (`Comment` toggle + `C` shortcut + submit modal).
- edge hit targets are selectable and include `data-relationship-id`.
- comment export includes required IDs (`view_id`, `element_id`, `relationship_id`).
- `diagram-prompt.md` exists in the requested output root.
- The required `diagram-prompt.md` heading is present verbatim.
- The prompt references the actual system name from artifacts.
- The mapping table references real files only.
- Every embedded file path exists in the virtual tree.
