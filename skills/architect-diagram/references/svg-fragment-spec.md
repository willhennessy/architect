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
Keep the visible relationship stroke itself light and diagram-secondary (typically about `1.0-1.25px`), separate from the oversized invisible hit target.

## Visual quality guidance

Aim for architecture-readable layout, not uniform grid:

- group by boundary and role
- cluster related services
- align layers (external, app, data/messaging)
- minimize edge crossings
- keep labels readable

### Node shape rules (required)

1. **Person / actor nodes**
   - Render people/actors as the same padded rectangular card family used for other nodes.
   - Do not use large head-and-body pictograms, circle-over-rectangle silhouettes, or tall avatar-style shapes.
   - Keep the title and subtype label inside the card with normal card padding.
   - If a subtype label is shown, prefer compact inline copy such as `[👤 User]`.

2. **Text containment**
   - Node boxes must be sized to contain both title and subtitle text with visible padding.
   - Never let title or subtitle text spill outside the node box.

### Additional legibility constraints (required)

1. **Legend placement**
   - If you include a legend, place it **outside** the architecture drawing region/system boundary.
   - Never place the legend inside architectural layers or inside the system boundary panel.

2. **Edge geometry**
   - Route arrows from node perimeter to node perimeter.
   - Edge paths must not pass through the interior of any node box.
   - Prefer orthogonal/curved routing that avoids node overlap over direct crossing lines.
   - Keep visible arrow strokes thinner than node borders so relationships read as connective tissue, not primary shapes.

3. **Edge labels**
   - Keep relationship labels close to their edge (small offset, ~4–10px).
   - Rotate labels to align roughly parallel with edge direction where possible.
   - Avoid floating labels far away from their associated line.

4. **Confidence display**
   - Do not render confidence tokens (e.g., `confirmed`, `strong_inference`, `weak_inference`) as visible labels inside the SVG diagram.
   - Confidence must be shown in the details sidebar only.

## Sequence views

Sequence views are optional as SVG fragments; the app has a built-in fallback renderer.
If you provide sequence SVG fragments, preserve step numbering and participant labels.

## Validation

After injection, run:

- `scripts/validate-diagram-html.sh <output-root>/diagram.html`
