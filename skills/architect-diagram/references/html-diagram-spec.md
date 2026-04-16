# HTML Diagram Specification

Use this when generating `diagram.html`.

## Required behavior

1. Start at system-context when available.
2. Support drill-down where deeper views exist.
3. Breadcrumb navigation.
4. Details sidebar:
   - collapsed by default
   - auto-expand on node click
   - manual collapse control
   - show confidence in sidebar only
5. Comment Mode:
   - toggle button + `C` shortcut
   - node/edge/canvas comment targeting
   - queued comments
   - global submit modal with JSON payload + copy button

## Rendering model

Use fixed app template + injected SVG fragments.

- generator: `skills/architect-diagram/scripts/generate-svg-fragments.py`
- renderer: `skills/architect-diagram/scripts/render-diagram-html.py`

## Sequence policy

- Sequence views are disabled by default.
- Include only when explicitly requested (`--include-sequence`).

## Style/legibility constraints

- engineering-friendly dark palette
- avoid confidence labels on SVG canvas
- if legend exists, place outside core architecture boundary
- arrows should avoid passing through node interiors when possible
- edge labels should stay close to edges and aligned with edge direction

## Validation

Run:

`skills/architect-diagram/scripts/validate-diagram-html.sh <output-root>/diagram.html`
