---
name: diagram
description: Generate an interactive HTML architecture diagram (`diagram.html`) with drill-down navigation and Comment Mode from existing architecture artifacts (`manifest.yaml`, `model.yaml`, and views). Use after architect-plan or architect-init has generated architecture artifacts.
---

Use this skill only after architecture artifacts already exist.

## Inputs

- output root path containing `architecture/`
- generated architecture artifacts:
  - `architecture/manifest.yaml`
  - `architecture/model.yaml`
  - `architecture/views/*.yaml`
  - `architecture/summary.md`
  - optional `architecture/diff.yaml`

## Outputs

Required:

- `<output-root>/architecture/diagram.html` (primary)

Recommended intermediate output:

- `<output-root>/architecture/.out/diagram-svg/<view-id>.svg` (one per non-sequence view)

Optional debug output:

- `<output-root>/architecture/.out/diagram-data.json` (when `--write-data-json` is enabled)

## Hard Rules

- Do not invent architecture facts.
- Source all content from provided artifacts.
- Preserve exact IDs and paths from source artifacts.
- `diagram.html` must remain a single-file artifact with inline CSS/JS; external assets are disallowed except for the approved Instrument Sans Google Fonts links when that typography path is intentionally used.
- `diagram.html` must implement drill-down + breadcrumb navigation.
- `diagram.html` must implement Comment Mode (`Comment` toggle + `C` shortcut + queued comments + JSON submit modal).
- Do not render confidence labels directly on canvas/SVG; show confidence in details sidebar only.
- Details sidebar behavior:
  - collapsed by default
  - auto-expands on node click
  - manual collapse control in sidebar
- By default, do **not** generate `diagram-prompt.md` in this skill.
- If user asks for upload bundle generation, use `architect-diagram-prompt`.
- **Sequence diagrams are disabled by default.** Include sequence only when explicitly requested.
- Person/actor nodes must render as the same rectangular card family used by other nodes, with sufficient padding for label text.
- Do not render person nodes as oversized head-and-body pictograms or circle-over-rectangle figures.
- When a person/actor subtype label is shown inside a node, prefer compact inline copy like `[👤 User]`.
- Visible relationship arrows should use lighter strokes than node borders; keep the visual stroke subtle while preserving large invisible hit targets for comment-mode interaction.
- Header-band geometry and person-card header positioning currently have two owners: authored SVG output in `scripts/generate-svg-fragments.py` and browser-side normalization in `templates/diagram-app.html`. If you adjust header band size, label alignment, or person-card header placement, update both paths.

## Rendering approach

Primary path (preferred):

1. Generate styled SVG fragments from architecture artifacts:
   - `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate-svg-fragments.py --output-root <output-root>`
2. Inject fragments into template app:
   - `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render-diagram-html.py --output-root <output-root> --demo-mode`

Fallback/testing path:

- If explicitly requested for quick iteration, allow fallback renderer:
  - `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render-diagram-html.py --output-root <output-root> --mode fast`

## Sequence behavior

Default:

- sequence views are excluded from render payload/tabs.

Opt-in (explicit request only):

- pass `--include-sequence` to `render-diagram-html.py`

## Workflow

1. Read contracts/specs:
   - `references/diagram-output-contract.md`
   - `references/html-diagram-spec.md`
   - `references/svg-fragment-spec.md`
2. Load architecture artifacts under `<output-root>/architecture/`.
3. Generate SVG fragments under `<output-root>/architecture/.out/diagram-svg/`.
4. Render `architecture/diagram.html` via template injection.
5. Validate:
   - `${CLAUDE_PLUGIN_ROOT}/scripts/validate-diagram-html.sh <output-root>/architecture/diagram.html`
6. Return path and summary of what was rendered.

## Completion Standard

Complete only when `architecture/diagram.html` exists, is grounded in artifacts, and passes validation.
