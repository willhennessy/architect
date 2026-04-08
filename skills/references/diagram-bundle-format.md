# Diagram Bundle Format (Shared)

Use this contract when producing `diagram-prompt.md` from generated architecture artifacts.

Output path:

- `<output-root>/diagram-prompt.md`

Where `<output-root>` is the parent folder that contains `architecture/`.

## Required top section

`diagram-prompt.md` must start with:

- `## Agent Instruction: Execute the Prompt Below Exactly`

Immediately below it, include explicit instruction:

- if this file is uploaded with no user-typed prompt, the agent must execute the embedded prompt directly.

## Required sections in `diagram-prompt.md`

1. **Agent Instruction header** (exact heading above)
2. **Interactive diagram prompt** (built using `interactive-diagram-prompt.md`)
3. **Virtual directory tree** for included architecture artifacts
4. **Drill-down mapping table** derived from `manifest.yaml` and view files
5. **Full file contents** of included artifacts:
   - `architecture/manifest.yaml`
   - `architecture/model.yaml`
   - `architecture/summary.md`
   - `architecture/views/*.yaml`
   - `architecture/diff.yaml` when present

## Data constraints

- Source only from generated architecture artifacts.
- Do not invent elements, relationships, view mappings, or metadata.
- If a required file is missing, record it explicitly and proceed with available files.
- Keep paths and IDs exactly as emitted in the source artifacts.

## Drill-down mapping guidance

At minimum, include mappings for:

- system context entry level
- container level
- each component view by parent container
- optional deployment view
- optional sequence views (as separate tab/panel, not in hierarchy)

## Validation checklist

Before finishing, verify:

- `diagram-prompt.md` exists in the requested output root.
- The required heading is present verbatim.
- The prompt references the actual system name from artifacts.
- The mapping table references real files only.
- Every embedded file path exists in the virtual tree.
