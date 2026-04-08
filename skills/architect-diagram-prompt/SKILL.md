---
name: architect-diagram-prompt
description: Generate an upload-ready diagram prompt bundle (`diagram-prompt.md`) from architecture artifacts (`manifest.yaml`, `model.yaml`, and views) so Claude Imagine can render an interactive drill-down architecture diagram. Use after architect-plan or architect-discover has already generated architecture artifacts.
---

Use this skill only after architecture artifacts already exist.

## Required References

Read these before writing output:

- [../references/interactive-diagram-prompt.md](../references/interactive-diagram-prompt.md)
- [../references/diagram-bundle-format.md](../references/diagram-bundle-format.md)
- [../references/architecture-contract.md](../references/architecture-contract.md)

## Inputs

- output root path containing `architecture/`
- generated architecture artifacts:
  - `architecture/manifest.yaml`
  - `architecture/model.yaml`
  - `architecture/views/*.yaml`
  - `architecture/summary.md`
  - optional `architecture/diff.yaml`

## Output

- `<output-root>/diagram-prompt.md`

## Hard Rules

- Do not invent architecture facts.
- Source all content from the provided artifacts.
- Use the exact top heading required by `diagram-bundle-format.md`.
- Include a zero-text upload execution instruction directly under that heading.
- Preserve exact IDs and paths from source artifacts.

## Workflow

1. Validate required artifact paths exist.
2. Load `manifest.yaml`, `model.yaml`, and all available `views/*.yaml`.
3. Construct the interactive prompt using the shared template.
4. Build drill-down mappings from available views.
5. Write a self-contained `diagram-prompt.md` bundle that includes:
   - required heading + zero-text instruction
   - constructed prompt
   - virtual tree
   - mapping table
   - full embedded artifact contents
6. Run validation checklist from `diagram-bundle-format.md`.

## Completion Standard

Complete only when `diagram-prompt.md` is self-contained and upload-ready for Claude Chat / Claude Imagine.
