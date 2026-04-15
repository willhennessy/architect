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

Recommended intermediate output (for high-quality primary rendering):

- `<output-root>/diagram-svg/<view-id>.svg` (one per non-sequence view)

Optional debug output:

- `<output-root>/diagram-data.json` (when `--write-data-json` is enabled)

## Hard Rules

- Do not invent architecture facts.
- Source all content from the provided artifacts.
- Preserve exact IDs and paths from source artifacts.
- `diagram.html` must be fully self-contained (inline CSS/JS; no external dependencies).
- `diagram.html` must support drill-down navigation from available view hierarchy and breadcrumb navigation.
- `diagram.html` must implement Comment Mode (`Comment` toggle + `C` shortcut + comment queue + submit modal JSON handoff).
- Use stable element metadata in HTML (`data-element-id`, `data-view-id`, and relationship metadata where applicable).
- If a legend is included, it must be outside the architecture/system boundary region.
- Relationship arrows should avoid node-interior intersections and keep labels close/parallel to edge direction.
- Do not show confidence labels directly on diagram SVG nodes/edges; confidence belongs in the details sidebar only.
- Details sidebar must be collapsed by default, auto-expand on node click, and provide an in-sidebar manual collapse control.
- By default, do **not** generate `diagram-prompt.md` in this skill.
- If user asks for Claude Imagine upload bundle generation, use `architect-diagram-prompt`.

## Rendering approach (hybrid)

Primary path (demo-quality):

1. Use the model to generate per-view SVG fragments (layout quality)
2. Inject those fragments into the fixed HTML app template (stable UX + interactions)

Fallback path (when SVG fragments are missing):

- deterministic built-in layout in the template app

## Rendering modes (fallback complexity control)

`render-diagram-html.py` mode impacts fallback layout:

- **fast (default):** lane-based fallback layout, lower complexity
- **rich:** layered graph fallback layout with denser labeling

## Workflow

1. **Validate output requirements**
   - Read [references/diagram-output-contract.md](references/diagram-output-contract.md).
   - Verify the output root and required architecture artifact paths exist.

2. **Load architecture artifacts**
   - Read `manifest.yaml`, `model.yaml`, `summary.md`, and available `views/*.yaml` (plus optional `diff.yaml`).

3. **Generate SVG fragments for primary diagram views (recommended)**
   - Read [references/svg-fragment-spec.md](references/svg-fragment-spec.md).
   - Generate `<output-root>/diagram-svg/<view-id>.svg` for each non-sequence view.

4. **Render primary HTML diagram (template injection)**
   - Read [references/html-diagram-spec.md](references/html-diagram-spec.md).
   - Read [references/comment-handoff-format.md](references/comment-handoff-format.md).
   - Run:
     - `python3 scripts/render-diagram-html.py --output-root <output-root> --mode fast`
   - For strict demo quality, require fragments:
     - `python3 scripts/render-diagram-html.py --output-root <output-root> --mode fast --require-svg-fragments`
   - Use `--mode rich` when richer fallback layout is needed.

5. **Run deterministic diagram validation (required)**
   - Run `scripts/validate-diagram-html.sh <output-root>/diagram.html`.
   - If validation fails, fix and rerun until it passes.

6. **Run contract checks only when needed**
   - If artifact shape is ambiguous or inconsistent, read [../references/architecture-contract.md](../references/architecture-contract.md) to resolve schema expectations.
   - If unresolved issues remain, record them explicitly instead of guessing.

7. **Run final validation checklist**
   - Execute the checklist in `diagram-output-contract.md` before completing.

## Completion Standard

Complete only when `diagram.html` exists, is grounded in the architecture artifacts, and passes the validation checklist (including deterministic HTML validation).
