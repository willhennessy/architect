# Diagram Output Contract

Use this contract when producing diagram artifacts from architecture files.

## Output paths

- `<output-root>/architecture/diagram.html` (primary; produced by `architect-diagram`)
- `<output-root>/architecture/diagram-prompt.md` (secondary; produced by `architect-diagram-prompt` only when requested)
- `<output-root>/architecture/.out/diagram-svg/<view-id>.svg` (internal SVG fragment cache)
- `<output-root>/architecture/.out/feedback-jobs/` (internal comment-loop job state)

## Primary requirements (`diagram.html`)

- Single-file HTML with inline CSS/JS.
- External assets are disallowed except for the approved Instrument Sans Google Fonts links (`fonts.googleapis.com` / `fonts.gstatic.com`) when that typography path is intentionally used.
- Grounded in provided architecture artifacts only.
- Drill-down + breadcrumb navigation.
- Comment Mode with element/edge/canvas targeting and JSON handoff.
- Stable metadata attributes:
  - nodes: `data-element-id`, `data-view-id`
  - edges: `data-relationship-id`, `data-view-id`
- Interactive node targets must cover the full rendered node card, including header bars and text, so clicks/comments never fall through to canvas.

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

- `architecture/diagram.html` exists.
- `architecture/diagram.html` is a single-file artifact.
- Any external dependency is limited to the approved Instrument Sans Google Fonts links; arbitrary external assets remain disallowed.
- diagram metadata attributes are present for interactive targets.
- comment export is JSON and includes `view_id`, `element_id`, `relationship_id`, `comment`.
- person/actor nodes are rendered as padded rectangular cards rather than avatar-style pictograms.
- person/actor title and subtype text are contained within the node box.
- visible relationship arrows use lighter strokes than node borders while retaining large invisible hit targets.
- `skills/architect-diagram/scripts/validate-diagram-html.sh <output-root>/architecture/diagram.html` passes.

If `diagram-prompt.md` was requested:

- heading exists: `## Agent Instruction: Execute the Prompt Below Exactly`
- ends with: `View the architecture diagram here: <fully_resolved_file_path>` (absolute path to `<output-root>/architecture/diagram.html`)
