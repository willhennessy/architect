---
name: architect-diagram-prompt
description: Generate an upload-ready diagram prompt bundle (`diagram-prompt.md`) from architecture artifacts (`manifest.yaml`, `model.yaml`, and views) so Claude Imagine can render an interactive drill-down architecture diagram. Use after architect-plan or architect-discover has already generated architecture artifacts.
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

## Output

- `<output-root>/diagram-prompt.md`

## Hard Rules

- Do not invent architecture facts.
- Source all content from the provided artifacts.
- Preserve exact IDs and paths from source artifacts.
- Use the exact top heading required by the bundle contract.
- Include a zero-text upload execution instruction directly under that heading.

## Workflow

1. **Validate bundle requirements**
   - Read [references/diagram-bundle-format.md](references/diagram-bundle-format.md).
   - Verify the output root and required architecture artifact paths exist.

2. **Load architecture artifacts**
   - Read `manifest.yaml`, `model.yaml`, `summary.md`, and all available `views/*.yaml` (plus optional `diff.yaml`).

3. **Construct the interactive diagram prompt**
   - Read [references/interactive-diagram-prompt.md](references/interactive-diagram-prompt.md).
   - Build the prompt using that specification and adapt role/context to the actual system and stack.

4. **Build drill-down mappings**
   - Derive mappings from available view files and manifest artifact listings.

5. **Assemble `diagram-prompt.md`**
   - Follow section order and required content from `diagram-bundle-format.md`.
   - Include: required heading, zero-text instruction, constructed prompt, virtual tree, mapping table, and full artifact contents.

6. **Run contract checks only when needed**
   - If artifact shape is ambiguous or inconsistent, read [../references/architecture-contract.md](../references/architecture-contract.md) to resolve view/schema expectations.
   - If unresolved issues remain, record them explicitly in the bundle instead of guessing.

7. **Run final validation checklist**
   - Execute the checklist in `diagram-bundle-format.md` before completing.

## Completion Standard

Complete only when `diagram-prompt.md` is self-contained and upload-ready for Claude Chat / Claude Imagine.
