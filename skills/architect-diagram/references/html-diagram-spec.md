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

## Data and grounding constraints

- Render only entities and relationships present in architecture artifacts.
- Do not invent edges, components, or metadata.
- If deeper views are missing, treat node as leaf and show details panel.

## HTML constraints

- Single self-contained HTML file.
- Inline CSS and JS only.
- Stable metadata attributes on rendered entities:
  - `data-element-id`
  - `data-view-id`
- When relationships are rendered, include relationship metadata in DOM/JS state.

## Style constraints

- Engineering-first, legible over decorative.
- Consistent color semantics by element kind.
- Clear visual distinction between drillable and non-drillable nodes.