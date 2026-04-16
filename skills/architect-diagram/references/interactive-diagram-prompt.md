# Interactive Diagram Prompt Specification

Used by `architect-diagram-prompt` to build `diagram-prompt.md`.

## Important default

- Sequence diagrams are **off by default** in the main diagram flow.
- Only include sequence instructions when explicitly requested.

## Prompt sections (order)

1. Role statement
2. Context block
3. Drill-down behavior
4. Comment Mode behavior
5. Data grounding constraints
6. Layout/style constraints
7. Robustness constraints
8. Final handoff line requirement:
   - `View the architecture diagram here: <fully_resolved_file_path>`

## Must enforce

- no invented elements/edges/IDs
- preserve artifact IDs exactly
- include target metadata for comments
- edge hit targets with `data-relationship-id`
- no confidence labels on diagram canvas (confidence in details panel only)
