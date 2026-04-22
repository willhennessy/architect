# Plugin Publish Workflow

Use this when you want to publish the Architect plugin marketplace from the main `architect` repo.

Public marketplace identity:

- marketplace repo: `willhennessy/architect`
- marketplace name: `plugins`
- install string: `architect@plugins`

## What this does

The publish workflow keeps one source of truth:

- root marketplace catalog: `.claude-plugin/marketplace.json`
- plugin bundle: `claude-plugin/architect/`

The public marketplace is the GitHub repo itself. The local-dev marketplace under `claude-plugin/.claude-plugin/marketplace.json` stays available for unpublished development/testing, but it is not the public install path.

Local `.agents/` and `.claude/` skill-link directories are intentionally not part of the published repo surface. If you want those convenience symlinks in a local checkout, create them with:

```bash
./scripts/setup-local-skill-links.sh
```

## Run it

From the repo root:

```bash
./scripts/publish-plugin.sh
```

The script will:

1. require a clean git worktree
2. require the current branch to be `main`
3. sync the plugin bundle with `python3 scripts/sync-claude-plugin.py`
4. validate the root marketplace with `claude plugin validate .`
5. validate the plugin bundle with `claude plugin validate ./claude-plugin/architect`
6. verify:
   - marketplace file exists at `.claude-plugin/marketplace.json`
   - marketplace name is `plugins`
   - marketplace description is `Interactive architecture diagrams for planning, steering, and code review`
   - the `architect` plugin entry points to `./claude-plugin/architect`
7. print the final human checklist

## After the script passes

Do this manually:

1. review the diff
2. commit the synced plugin files + marketplace changes
3. push to GitHub

The script intentionally does **not** auto-push.

## End-user install flow

Once published, users install Architect like this:

```bash
claude plugin marketplace add willhennessy/architect
claude plugin install architect@plugins
```

And they launch Claude like this:

```bash
claude \
  --channels plugin:architect@plugins \
  --append-system-prompt "When an architect-comments channel event arrives, treat the channel text as the user-visible acknowledgment, call update_feedback_status with state=acknowledged without sending a second acknowledgment message in chat, inspect the referenced job and output root from the channel metadata, especially comments_summary and comments_json, implement the requested updates directly, use update_feedback_status for progress, use finalize_feedback_update instead of guessing render commands, and do not stop after proposing a plan unless you are blocked or the feedback is genuinely ambiguous or high-risk. If the comment is a connectivity check, a simple acknowledgment, or otherwise does not request an architecture change, resolve it immediately by calling update_feedback_status with state=completed and a concise message such as \"Resolved 1 comment. No architecture changes were requested.\" Do not ask a follow-up question for those no-op comments."
```

`--append-system-prompt` is still required for reliable comment handling.
