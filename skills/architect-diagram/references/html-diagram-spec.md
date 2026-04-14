# HTML Diagram Specification

Use this specification when generating `diagram.html`.

## Purpose

Produce a self-contained interactive architecture diagram grounded in:

- `architecture/model.yaml`
- `architecture/views/*.yaml`
- `architecture/manifest.yaml`

## Required behavior

1. Entry at system-context view when available.
2. Drill-down from system -> container -> component where supporting views exist.
3. Breadcrumb navigation with clickable ancestors.
4. Explicit back navigation control.
5. Detail panel for selected entity with:
   - name
   - kind/type
   - description/responsibilities
   - technology/language when present
   - confidence level when present
6. Sequence views (if available) exposed in a separate panel/tab.
7. **Comment Mode** for planning feedback:
   - global `Comment` toggle button (keyboard shortcut: `C`)
   - visual mode indicator when enabled
   - while enabled, clicking the diagram opens a comment composer anchored to click position
   - comment composer supports multiline text and explicit submit/cancel actions
   - submitted comments are queued locally and visible in a lightweight queue list
8. Global `Submit` action to finalize queued comments:
   - opens a modal containing copy-ready markdown for the coding agent
   - markdown must include each comment with associated target id (or `null` for empty-space clicks)
   - include a one-click copy control for the markdown payload

## Comment targeting rules

- If click intersects a rendered architecture element, bind comment to that element via `element_id`.
- If click intersects a rendered relationship/edge, bind comment to that relationship via `relationship_id`.
- If click does not map to any architecture target, set both `element_id` and `relationship_id` to `null`.
- Persist `view_id` and user-entered text for every queued comment.
- Include display label (element/relationship name) when available for human readability.

## Edge/line hit-target requirements

Thin connectors (lines/arrows) must remain easy to click:

- provide an invisible interaction layer per edge (`pointer-events` target), or equivalent
- enforce a minimum clickable thickness of at least 12px around visual edge geometry
- expose `data-relationship-id` on edge hit targets

## Data and grounding constraints

- Render only entities and relationships present in architecture artifacts.
- Do not invent edges, components, or metadata.
- If deeper views are missing, treat node as leaf and show details panel.
- Comment target IDs must come directly from artifact IDs.

## HTML constraints

- Single self-contained HTML file.
- Inline CSS and JS only.
- Stable metadata attributes on rendered entities:
  - `data-element-id`
  - `data-view-id`
- Stable metadata attributes on relationship hit targets:
  - `data-relationship-id`
  - `data-view-id`
- When relationships are rendered, include relationship metadata in DOM/JS state.

## Style constraints

- Engineering-first, legible over decorative.
- Consistent color semantics by element kind.
- Clear visual distinction between drillable and non-drillable nodes.
- Comment mode should be visually obvious without obscuring core diagram readability.

## Reference implementation

For concrete interaction and payload behavior, see:

- `references/comment-mode-reference.html`
