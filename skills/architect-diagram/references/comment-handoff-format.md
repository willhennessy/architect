# Comment Handoff Format

Use this reference when implementing Comment Mode export in `diagram.html`.

## Goal

Produce a copy-ready JSON payload that an engineer can paste directly into a coding agent so feedback stays attached to architecture IDs.

## Required export shape (JSON)

The submit modal must include JSON with this structure:

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

Rules:

- include all queued comments in insertion order
- preserve exact IDs from artifacts
- use explicit `null` when no element/relationship is hit
- do not remove or summarize user text
- output valid JSON only (no markdown wrapper)

## UX requirements

- Provide a one-click copy button for the modal content.
- Include instruction text: `Copy this JSON and paste it into your coding agent.`
- Keep the modal content self-contained; no hidden dependencies on browser storage.
