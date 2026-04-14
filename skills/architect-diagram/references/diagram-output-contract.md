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
  - relationship metadata when rendering edges
- Sequence views (if present) must be separated from core drill-down hierarchy.

### Required deterministic validation

Before declaring completion, run:

- `scripts/validate-diagram-html.sh <output-root>/diagram.html`

If it fails, fix and rerun until it passes.

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

## Validation checklist

Before finishing, verify:

- `diagram.html` exists in the requested output root.
- `diagram.html` is self-contained (no external dependencies).
- `diagram.html` drill-down hierarchy only references real view files.
- `scripts/validate-diagram-html.sh <output-root>/diagram.html` passes.
- inline JavaScript parses cleanly (`node --check` via validator when available).
- no malformed template expressions like `${x-${y}}` remain in HTML/JS output.
- `diagram-prompt.md` exists in the requested output root.
- The required `diagram-prompt.md` heading is present verbatim.
- The prompt references the actual system name from artifacts.
- The mapping table references real files only.
- Every embedded file path exists in the virtual tree.