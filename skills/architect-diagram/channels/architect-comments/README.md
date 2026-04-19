# Architect Comments Channel

This is the legacy bare-server development channel for Architect comment feedback.

The primary packaging path is now the plugin runtime at:

- `/Users/will/.codex/worktrees/d07d/architect/claude-plugin/architect/README.md`

Use this bare channel server when you want to debug the channel transport directly outside the plugin wrapper.

It exists so the user's live Claude session can own the full comment-update loop:

1. `architecture/diagram.html` submits a batched feedback job to the localhost bridge
2. the bridge persists the job and forwards it to this channel server
3. Claude receives a `<channel ...>` event in the active session
4. Claude acknowledges the feedback, updates bridge job status through the MCP tool, and takes over the update loop
5. Claude validates and rerenders the same `architecture/diagram.html` through the finalize MCP tool before marking the job complete

## Install

From this directory:

```bash
npm install
```

## Legacy bare-server path (known good)

This is the **known-good bare-server setup** for Claude handoff today.

It was validated against Claude Code `2.1.111`, the in-repo bridge, and the development channel server in this repo.

### 1) From the repo root, install the channel dependency

```bash
REPO_ROOT=$(pwd)
cd "$REPO_ROOT/skills/architect-diagram/channels/architect-comments"
npm install
cd "$REPO_ROOT"
```

### 2) Write a temporary MCP config for Claude

```bash
REPO_ROOT=$(pwd)
cat > /tmp/architect-channel-mcp.json <<EOF
{
  "mcpServers": {
    "architect-comments": {
      "command": "node",
      "args": [
        "${REPO_ROOT}/skills/architect-diagram/channels/architect-comments/channel.mjs"
      ],
      "env": {
        "ARCHITECT_CHANNEL_PORT": "8788"
      }
    }
  }
}
EOF
```

### 3) Start the bridge in Claude handoff mode

```bash
REPO_ROOT=$(pwd)
python3 "$REPO_ROOT/skills/architect-diagram/scripts/comment_feedback_bridge.py" \
  --claude-channel-url http://127.0.0.1:8788/notify \
  --channel-handoff-only
```

### 4) In a second terminal, start Claude with the development channel enabled

```bash
claude \
  --mcp-config /tmp/architect-channel-mcp.json \
  --strict-mcp-config \
  --dangerously-load-development-channels server:architect-comments \
  --permission-mode auto \
  --append-system-prompt "When an architect-comments channel event arrives, treat the channel text as the user-visible acknowledgment, call update_feedback_status with state=acknowledged without sending a second acknowledgment message in chat, inspect the referenced job and output root from the channel metadata, implement the requested updates directly, use update_feedback_status for progress, use finalize_feedback_update instead of guessing render commands, and do not stop after proposing a plan unless you are blocked or the feedback is genuinely ambiguous or high-risk."
```

### 5) Approve the development-channel prompt and verify the connection

- choose `I am using this for local development`
- run `/mcp`
- confirm `architect-comments` shows as connected before submitting comments

### 6) Submit comments from `architecture/diagram.html`

Expected result:

- the bridge prints the immediate acknowledgement
- Claude receives an `architect-comments` channel event in the same live session
- Claude reports progress through `update_feedback_status`
- Claude uses `finalize_feedback_update`
- the browser tells the user to refresh the same `architecture/diagram.html`

### Known-good notes

- Use `--dangerously-load-development-channels server:architect-comments`
- Do **not** also pass `--channels server:architect-comments`
- Use `--permission-mode auto`, not `plan`
- `claude --help` may not list every Channels-related flag
- Claude may still print a misleading startup warning about `no MCP server configured with that name`; if `/mcp` shows `architect-comments` connected, the session is good

## Run with Claude manually

If you do not want the blessed copy-paste flow above, you can still configure Claude manually.

Create an MCP config that points at this server. Example:

```json
{
  "mcpServers": {
    "architect-comments": {
      "command": "node",
      "args": [
        "/ABSOLUTE/PATH/TO/skills/architect-diagram/channels/architect-comments/channel.mjs"
      ],
      "env": {
        "ARCHITECT_CHANNEL_PORT": "8788"
      }
    }
  }
}
```

Then start Claude with the development channel enabled:

```bash
claude \
  --mcp-config /ABSOLUTE/PATH/TO/mcp.json \
  --dangerously-load-development-channels server:architect-comments
```

If you want Claude to stay idle until a feedback event arrives, add behavior guidance via a system prompt instead of a trailing user prompt:

```bash
claude \
  --mcp-config /ABSOLUTE/PATH/TO/mcp.json \
  --dangerously-load-development-channels server:architect-comments \
  --permission-mode auto \
  --append-system-prompt "When an architect-comments channel event arrives, treat the channel text as the user-visible acknowledgment, call update_feedback_status with state=acknowledged without sending a second acknowledgment message in chat, inspect the referenced job and output root from the channel metadata, implement the requested updates directly, use update_feedback_status for progress, use finalize_feedback_update instead of guessing render commands, and do not stop after proposing a plan unless you are blocked or the feedback is genuinely ambiguous or high-risk."
```

After Claude starts, run `/mcp` and confirm `architect-comments` is connected before submitting a batch.

The channel exposes two MCP tools:

- `update_feedback_status` — posts progress, ready, completed, blocked, or failed status updates back to the localhost bridge using the `bridge_url` and `job_id` from the channel event
- `finalize_feedback_update` — runs the hardening validator, rerenders `architecture/diagram.html` with the exact repo render command, preserves the bridge URL when provided, and validates the generated HTML before Claude marks the job complete

Recommended Claude behavior for a normal feedback batch:

1. Treat the visible channel line as the acknowledgment and call `update_feedback_status` with `state=acknowledged` without posting a second chat acknowledgment
2. Inspect the referenced artifacts and call `update_feedback_status` with `state=analyzing`
3. Edit the architecture artifacts
4. Call `finalize_feedback_update` with `output_root` and `bridge_url`
5. If finalize succeeds, call `update_feedback_status` with `state=completed` and the exact message `Refresh the page to see updates.`

## Run the bridge in Claude handoff mode

```bash
python3 skills/architect-diagram/scripts/comment_feedback_bridge.py \
  --claude-channel-url http://127.0.0.1:8788/notify \
  --channel-handoff-only
```

With that running, a normal comment submit should create a job and forward the batch into Claude instead of running the deterministic updater. The deterministic worker is now fallback behavior, not the primary product path.
