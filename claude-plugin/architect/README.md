# Architect Claude Plugin

Architect as a Claude plugin.

This is the new primary packaging path for:

- `/architect:discover`
- `/architect:plan`
- `/architect:diagram`
- `/architect:diagram-prompt`

It also owns the live comment loop:

1. `architecture/diagram.html` submits comments to the plugin runtime on `http://127.0.0.1:8765`
2. the plugin runtime persists the feedback job and forwards it into the same Claude session as a channel event
3. Claude updates job state through `update_feedback_status`
4. Claude finalizes the update through `finalize_feedback_update`
5. the user refreshes the same `architecture/diagram.html`

## Getting started

Install Architect from the official Claude marketplace:

```bash
claude plugin install architect@claude-plugins-official
```

Start Claude with the Architect channel enabled:

```bash
claude \
  --channels plugin:architect@claude-plugins-official \
  --append-system-prompt "When an architect-comments channel event arrives, acknowledge it immediately, inspect the referenced job and output root, implement the requested updates directly, use update_feedback_status for progress, use finalize_feedback_update instead of guessing render commands, and do not stop after proposing a plan unless you are blocked or the feedback is genuinely ambiguous or high-risk."
```

`--append-system-prompt` is required to guarantee Claude responds to comments.

In Claude:

1. Run `/mcp` and confirm `plugin:architect:architect-comments` is connected.
2. Run `/architect:plan` or `/architect:discover`.
3. Architect writes visible artifacts under `./architecture/` by default.
4. Open `./architecture/diagram.html`.
5. Submit comments from the diagram.
6. Refresh the same file when the UI says `Refresh the page to see updates.`

That is the whole loop.
