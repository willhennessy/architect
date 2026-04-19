---
name: diagram-prompt
description: Generate the secondary Claude Imagine upload bundle (`diagram-prompt.md`) from existing architecture artifacts and rendered diagram output. Use when explicitly requested.
---

Use this skill only when the user explicitly asks for `diagram-prompt.md`.

## Inputs

- output root path containing `architecture/`
- generated architecture artifacts:
  - `architecture/manifest.yaml`
  - `architecture/model.yaml`
  - `architecture/views/*.yaml`
  - `architecture/summary.md`
  - optional `architecture/diff.yaml`
- rendered primary diagram path:
  - `<output-root>/architecture/diagram.html` (recommended, for final handoff line)

## Outputs

Required:

- `<output-root>/architecture/diagram-prompt.md`

## Hard Rules

- Do not invent architecture facts.
- Source all content from provided artifacts.
- Preserve exact IDs and paths.
- `diagram-prompt.md` must include the exact heading:
  - `## Agent Instruction: Execute the Prompt Below Exactly`
- Immediately below heading, include explicit zero-text upload execution instruction.
- `diagram-prompt.md` must end with:
  - `View the architecture diagram here: <fully_resolved_file_path>`
- `<fully_resolved_file_path>` must be absolute and resolve to `<output-root>/architecture/diagram.html`.

## Workflow

1. Read [../architect-diagram/references/diagram-output-contract.md](../architect-diagram/references/diagram-output-contract.md)
2. Read [../architect-diagram/references/interactive-diagram-prompt.md](../architect-diagram/references/interactive-diagram-prompt.md)
3. Load architecture artifacts under `<output-root>/architecture/`
4. Generate `<output-root>/architecture/diagram-prompt.md` per contract
5. Validate checklist items related to `diagram-prompt.md`

## Completion Standard

Complete only when `diagram-prompt.md` exists, is grounded in architecture artifacts, has the required heading + zero-text instruction, and ends with the absolute diagram path handoff line.
