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
4. Detail panel for selected entity with:
   - name
   - kind/type
   - description/responsibilities
   - technology/language when present
   - confidence level when present
   - collapsible behavior:
     - default state is collapsed to maximize diagram canvas space
     - auto-expand when the user clicks a diagram node
     - include an in-sidebar collapse control so users can close it manually
5. Sequence views (if available) exposed in a separate panel/tab.
6. **Comment Mode** for planning feedback:
   - global `Comment` toggle button (keyboard shortcut: `C`)
   - visual mode indicator when enabled
   - while enabled, clicking the diagram opens a comment composer
   - comment composer supports multiline text and explicit submit/cancel actions
   - submitted comments are queued locally and visible in a queue list
7. Global `Submit` action to finalize queued comments:
   - opens a modal containing copy-ready JSON for the coding agent
   - JSON must include each comment with associated target IDs (or `null` for empty-space clicks)
   - include a one-click copy control for the JSON payload

## Hybrid rendering model (preferred)

Use a fixed HTML app template and inject per-view SVG fragments:

- template app: `templates/diagram-app.html`
- fragment source: `<output-root>/diagram-svg/<view-id>.svg`
- injector: `scripts/render-diagram-html.py`

This keeps interactions stable while allowing LLM-quality layout.

Fallback behavior:

- if SVG fragment missing for a view, template fallback layout may render the view.

Demo-quality mode:

- `python3 scripts/render-diagram-html.py --output-root <output-root> --demo-mode`
- demo mode requires SVG fragments for selected non-sequence views and disables fallback for those views.

## Comment targeting rules

- If click intersects a rendered architecture element, bind comment to that element via `element_id`.
- If click intersects a rendered relationship/edge, bind comment to that relationship via `relationship_id`.
- If click does not map to any architecture target, set both `element_id` and `relationship_id` to `null`.
- Persist `view_id` and user-entered text for every queued comment.
- Include display label (element/relationship name) when available for human readability.

## Edge/line hit-target requirements

Thin connectors (lines/arrows) must remain easy to click:

- provide an interaction layer per edge (`pointer-events` target), or equivalent
- enforce a minimum clickable thickness of at least 12px around visual edge geometry
- expose `data-relationship-id` on edge hit targets

## Diagram legibility constraints

- If a legend is present, place it outside the architecture drawing/system boundary region.
- Arrows must not intersect node interiors; route from perimeter-to-perimeter with collision avoidance.
- Arrow labels should stay near their line with small padding and be angled parallel to edge direction when feasible.
- Do not display confidence labels in the SVG diagram canvas; show confidence only in the details sidebar.

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

## Robustness constraints

- Generated inline JavaScript must be syntactically valid.
- Avoid malformed nested template expressions (for example: `${x-${y}}`).
- SVG fragments must not contain `<script>` tags.
- After generation, run `scripts/validate-diagram-html.sh <output-root>/diagram.html` and fix failures before completion.

## Style constraints

- Engineering-first, legible over decorative.
- Consistent color semantics by element kind.
- Clear visual distinction between drillable and non-drillable nodes.
- Comment mode should be visually obvious without obscuring core diagram readability.
- Prefer grouped/clustered layout over naive uniform grids.
