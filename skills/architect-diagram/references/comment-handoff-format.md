# Comment Handoff Format

Use this reference when implementing Comment Mode export in `diagram.html`.

## Goal

Produce a copy-ready payload that an engineer can paste directly into a coding agent so feedback stays attached to architecture IDs.

## Required export shape (markdown)

The submit modal must include markdown with this structure:

```md
## Architecture Review Comments

System: `<system_name>`
View: `<view_id>`

### Queued Comments
1. view_id: `<view_id>`
   element_id: `<element_id|null>`
   relationship_id: `<relationship_id|null>`
   comment: <freeform user text>

2. view_id: `<view_id>`
   element_id: `<element_id|null>`
   relationship_id: `<relationship_id|null>`
   comment: <freeform user text>
```

Rules:

- include all queued comments in insertion order
- preserve exact IDs from artifacts
- use explicit `null` when no element/relationship is hit
- do not remove or summarize user text

## Optional (recommended) companion JSON block

To improve reliability for coding-agent parsing, include a fenced JSON block below the markdown summary:

```json
{
  "system_name": "<system_name>",
  "comments": [
    {
      "index": 1,
      "view_id": "<view_id>",
      "element_id": "<element_id|null>",
      "relationship_id": "<relationship_id|null>",
      "target_label": "<optional label>",
      "comment": "<raw user text>"
    }
  ]
}
```

This is optional, but recommended as a better handoff for deterministic downstream tooling.

## UX requirements

- Provide a one-click copy button for the modal content.
- Include instruction text: `Copy this and paste it into your coding agent.`
- Keep the modal content self-contained; no hidden dependencies on browser storage.
