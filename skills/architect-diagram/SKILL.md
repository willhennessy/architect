---
name: architect-diagram
description: Generate an interactive HTML architecture diagram (`diagram.html`) with drill-down navigation and Comment Mode from existing architecture artifacts (`manifest.yaml`, `model.yaml`, and views). Use after architect-plan or architect-discover has generated architecture artifacts.
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

- `<output-root>/diagram.html` (primary)

Recommended intermediate output:

- `<output-root>/diagram-svg/<view-id>.svg` (one per non-sequence view)

Optional debug output:

- `<output-root>/diagram-data.json` (when `--write-data-json` is enabled)

## Hard Rules

- Do not invent architecture facts.
- Source all content from provided artifacts.
- Preserve exact IDs and paths from source artifacts.
- `diagram.html` must be fully self-contained (inline CSS/JS; no external dependencies).
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

## Rendering approach

Primary path (preferred):

1. Generate styled SVG fragments from architecture artifacts:
   - `python3 skills/architect-diagram/scripts/generate-svg-fragments.py --output-root <output-root>`
2. Inject fragments into template app:
   - `python3 skills/architect-diagram/scripts/render-diagram-html.py --output-root <output-root> --demo-mode`

Fallback/testing path:

- If explicitly requested for quick iteration, allow fallback renderer:
  - `python3 skills/architect-diagram/scripts/render-diagram-html.py --output-root <output-root> --mode fast`

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
3. Generate SVG fragments under `<output-root>/diagram-svg/`.
4. Render `diagram.html` via template injection.
5. Validate:
   - `skills/architect-diagram/scripts/validate-diagram-html.sh <output-root>/diagram.html`
6. Return path and summary of what was rendered.

## Completion Standard

Complete only when `diagram.html` exists, is grounded in artifacts, and passes validation.
