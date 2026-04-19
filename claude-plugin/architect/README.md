# Architect Claude Plugin

Architect as a Claude plugin.

This is the new primary packaging path for:

- `/architect:init`
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
  --append-system-prompt "When an architect-comments channel event arrives, treat the channel text as the user-visible acknowledgment, call update_feedback_status with state=acknowledged without sending a second acknowledgment message in chat, inspect the referenced job and output root from the channel metadata, implement the requested updates directly, use update_feedback_status for progress, use finalize_feedback_update instead of guessing render commands, and do not stop after proposing a plan unless you are blocked or the feedback is genuinely ambiguous or high-risk."
```

`--append-system-prompt` is required to guarantee Claude responds to comments without adding a redundant second acknowledgment in chat.

In Claude:

1. Run `/mcp` and confirm `plugin:architect:architect-comments` is connected.
2. Run `/architect:plan` or `/architect:init`.
3. Architect writes visible artifacts under `./architecture/` by default.
4. Open `./architecture/diagram.html`.
5. Submit comments from the diagram.
6. Refresh the same file when the UI says `Refresh the page to see updates.`

That is the whole loop.

## Troubleshooting

### `/mcp` shows `plugin:architect:architect-comments · ✘ failed`

The most common cause is that another Architect runtime is already using port `8765`.

Fix:

```bash
pkill -f architect_runtime.cjs
```

Then restart Claude and run `/mcp` again.

### Claude never responds after `Submit comments`

This usually means Claude was started without the required `--append-system-prompt`, or the Architect channel is not connected in the current session.

Fix:

1. Run `/mcp` and make sure `plugin:architect:architect-comments` is connected.
2. If it is not connected, restart Claude.
3. Make sure you launch Claude with the exact command shown above, including `--append-system-prompt`.

### The page says `Another comment update is already in progress`

Usually the previous comment job is still finishing up, or it just failed and the page has not refreshed yet.

Fix:

1. Wait about 20 seconds.
2. Refresh `architecture/diagram.html`.
3. Submit the comment again.

### The page falls back to copy-paste JSON instead of submitting comments

This usually means the rendered diagram no longer matches the folder it came from. The most common cause is moving or renaming the output folder after rendering.

Fix:

1. Keep the generated `architecture/` folder in the same location after Architect renders it.
2. If you already moved or renamed it, rerun `/architect:plan` or `/architect:init` and open the newly generated `architecture/diagram.html`.

### I refreshed, but I still do not see the change

Make sure you are refreshing the same `architecture/diagram.html` file that Claude updated.

Fix:

1. Refresh the exact same browser tab.
2. If you opened multiple copies of the diagram, close the older tabs and reopen `./architecture/diagram.html`.
3. If needed, hard refresh the page.
