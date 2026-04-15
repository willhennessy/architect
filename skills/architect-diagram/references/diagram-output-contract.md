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

## Deterministic renderer requirements

Use the deterministic renderer as the default implementation path:

- `python3 scripts/render-diagram-html.py --output-root <output-root> --mode <fast|rich>`

Mode policy:

- `fast` (default): system-context + container focus, lower visual density, lower latency/cost.
- `rich`: includes additional detail views (including sequence when available).

## Comment Mode requirements (`diagram.html`)

`diagram.html` must include Comment Mode with all of the following:

1. A global `Comment` toggle control and keyboard shortcut `C`.
2. While comment mode is active, clicking on the diagram opens a comment composer.
3. Submitted comments are queued locally (not auto-submitted externally).
4. Comment target binding:
   - node click -> `element_id` populated
   - edge/arrow click -> `relationship_id` populated
   - empty space click -> both IDs are `null`
5. Edge hitbox padding for reliable selection of thin lines/arrows.
6. A global `Submit` action that opens a modal with copy-ready JSON output.
7. Modal instruction telling user to paste JSON into coding agent.

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
6. Final one-line terminal/browser instruction for the rendered HTML:
   - `View the architecture diagram here: <fully_resolved_file_path>`
   - `<fully_resolved_file_path>` must resolve to `<output-root>/diagram.html` as an absolute path.

## Data constraints

- Source only from generated architecture artifacts.
- Do not invent elements, relationships, view mappings, or metadata.
- If a required file is missing, record it explicitly and proceed with available files.
- Keep paths and IDs exactly as emitted in source artifacts.

## Comment handoff payload requirements

The comment export JSON in the modal must include:

```json
{
  "system_name": "<system_name>",
  "comments": [
    {
      "index": 1,
      "view_id": "<view_id>",
      "element_id": "<element_id|null>",
      "relationship_id": "<relationship_id|null>",
      "target_label": "<optional label>",
      "comment": "<raw user text>"
    }
  ]
}
```

Required per comment entry:

- `index`
- `view_id`
- `element_id` (nullable)
- `relationship_id` (nullable)
- `comment`

## Validation checklist

Before finishing, verify:

- `diagram.html` exists in the requested output root.
- `diagram.html` is self-contained (no external dependencies).
- `diagram.html` drill-down hierarchy only references real view files.
- `diagram.html` includes comment mode (`Comment` toggle + `C` shortcut + submit modal).
- edge hit targets are selectable and include `data-relationship-id`.
- comment export is JSON and includes required fields (`view_id`, `element_id`, `relationship_id`, `comment`).
- deterministic render path was used (`render-diagram-html.py`) unless an explicit exception is documented.
- `scripts/validate-diagram-html.sh <output-root>/diagram.html` passes.
- inline JavaScript parses cleanly (`node --check` via validator when available).
- no malformed template expressions like `${x-${y}}` remain in HTML/JS output.
- `diagram-prompt.md` exists in the requested output root.
- The required `diagram-prompt.md` heading is present verbatim.
- The prompt references the actual system name from artifacts.
- The mapping table references real files only.
- Every embedded file path exists in the virtual tree.
- `diagram-prompt.md` ends with: `View the architecture diagram here: <fully_resolved_file_path>`.
- the final `<fully_resolved_file_path>` is absolute and points to `<output-root>/diagram.html`.
