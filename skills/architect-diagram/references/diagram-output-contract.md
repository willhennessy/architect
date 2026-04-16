# Diagram Output Contract

Use this contract when producing diagram artifacts from architecture files.

## Output paths

- `<output-root>/diagram.html` (primary; produced by `architect-diagram`)
- `<output-root>/diagram-prompt.md` (secondary; produced by `architect-diagram-prompt` only when requested)

## Primary requirements (`diagram.html`)

- Self-contained HTML (inline CSS/JS only).
- Grounded in provided architecture artifacts only.
- Drill-down + breadcrumb navigation.
- Comment Mode with element/edge/canvas targeting and JSON handoff.
- Stable metadata attributes:
  - nodes: `data-element-id`, `data-view-id`
  - edges: `data-relationship-id`, `data-view-id`

## Rendering pipeline

Preferred production pipeline:

1. Generate SVG fragments:
   - `python3 skills/architect-diagram/scripts/generate-svg-fragments.py --output-root <output-root>`
2. Render template-injected HTML:
   - `python3 skills/architect-diagram/scripts/render-diagram-html.py --output-root <output-root> --demo-mode`

## Sequence policy

- **Disabled by default** in diagram flow.
- Include sequence only when explicitly requested via `--include-sequence`.

## Validation checklist

Before finishing:

- `diagram.html` exists.
- `diagram.html` is self-contained.
- diagram metadata attributes are present for interactive targets.
- comment export is JSON and includes `view_id`, `element_id`, `relationship_id`, `comment`.
- person/actor nodes are rendered as padded rectangular cards rather than avatar-style pictograms.
- person/actor title and subtype text are contained within the node box.
- visible relationship arrows use lighter strokes than node borders while retaining large invisible hit targets.
- `skills/architect-diagram/scripts/validate-diagram-html.sh <output-root>/diagram.html` passes.

If `diagram-prompt.md` was requested:

- heading exists: `## Agent Instruction: Execute the Prompt Below Exactly`
- ends with: `View the architecture diagram here: <fully_resolved_file_path>` (absolute path to `<output-root>/diagram.html`)
