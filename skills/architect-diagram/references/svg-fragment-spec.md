# SVG Fragment Specification (Primary Diagram Layer)

Use this when generating per-view diagram fragments for template injection.

Output location:

- `<output-root>/diagram-svg/<view-id>.svg`

One SVG file per non-sequence diagram view.

## Required structure

- File content should be a single `<svg ...>...</svg>` fragment (no full HTML document).
- No `<script>` tags.
- No external references (`<image href="http...">`, `<use href="http...">`, etc.).
- Include `viewBox` and explicit width/height attributes.

## Required metadata for interactivity

Every clickable node must include:

- `data-element-id="<artifact element id>"`
- `data-view-id="<view-id>"` (recommended; injector can backfill)
- `data-target-label="<human label>"` (recommended; injector can backfill)

Every clickable edge target must include:

- `data-relationship-id="<artifact relationship id>"`
- `data-view-id="<view-id>"` (recommended; injector can backfill)
- `data-target-label="<human label>"` (recommended; injector can backfill)

For thin edges/arrows, include enlarged invisible hit targets (`stroke-width >= 12`).

## Visual quality guidance

Aim for architecture-readable layout, not uniform grid:

- group by boundary and role
- cluster related services
- align layers (external, app, data/messaging)
- minimize edge crossings
- keep labels readable

## Sequence views

Sequence views are optional as SVG fragments; the app has a built-in fallback renderer.
If you provide sequence SVG fragments, preserve step numbering and participant labels.

## Validation

After injection, run:

- `scripts/validate-diagram-html.sh <output-root>/diagram.html`
