#!/usr/bin/env bash
set -euo pipefail

# One-shot isolated production install test setup.
# Creates a per-run sandbox that installs Architect through the public
# marketplace path, then launches Claude with the published plugin enabled.

usage() {
  cat <<'EOF'
Usage:
  new-prod-test.sh [--repo-url <git-url> | --repo-path <local-path>]

Options:
  --repo-url <url>       Clone target repo into isolated run folder (optional)
  --repo-path <path>     Copy local repo into isolated run folder (optional)
  --run-root <path>      Parent folder for runs (default: ~/tmp/architect-prod-tests)
  --name <suffix>        Optional folder name suffix appended after timestamp; also used as Claude session name
  --hotpatch-local-plugin Overlay the freshly installed published plugin cache with this worktree's runtime/template fixes before launch
  -h, --help             Show help

Example:
  ./scripts/new-prod-test.sh --repo-url https://github.com/openfga/openfga.git --name openfga-published --hotpatch-local-plugin
EOF
}

REPO_URL=""
REPO_PATH=""
RUN_ROOT="$HOME/tmp/architect-prod-tests"
RUN_NAME_SUFFIX=""
MARKETPLACE_URL="https://github.com/willhennessy/architect.git"
PLUGIN_INSTALL_NAME="architect@plugins"
CLAUDE_MODEL="claude-haiku-4-5"
PLAN_PROMPT="/architect:plan Design a simple news feed web app with frontend and backend. Draw the architecture diagram. Generate at least 1 container and 2 components. Keep your token usage low."
INIT_PROMPT="/architect:init"
CLAUDE_PROMPT="$PLAN_PROMPT"
PLUGIN_CACHE_DIR="$HOME/.claude/plugins/cache/plugins/architect"
MARKETPLACE_GIT_DIR="$HOME/.claude/plugins/marketplaces/plugins"
MARKETPLACE_SHALLOW_LOCK="$MARKETPLACE_GIT_DIR/.git/shallow.lock"
CHANNEL_SYSTEM_PROMPT="When an architect-comments channel event arrives, treat the channel text as the user-visible acknowledgment, inspect the referenced job and output root from the channel metadata, especially comments_summary and comments_json, implement the requested updates directly, use update_feedback_status for progress, use finalize_feedback_update instead of guessing render commands, and do not stop after proposing a plan unless you are blocked or the feedback is genuinely ambiguous or high-risk. If the comment is a connectivity check, a simple acknowledgment, or otherwise does not request an architecture change, resolve it immediately by calling update_feedback_status with state=completed and a concise message such as \"Resolved 1 comment. No architecture changes were requested.\" Do not ask a follow-up question for those no-op comments."
HOTPATCH_LOCAL_PLUGIN=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCAL_PLUGIN_ROOT="$REPO_ROOT/claude-plugin/architect"

is_github_repo_url() {
  local url="${1:-}"
  [[ "$url" =~ ^https?://github\.com/ ]] || \
    [[ "$url" =~ ^git@github\.com: ]] || \
    [[ "$url" =~ ^ssh://git@github\.com/ ]] || \
    [[ "$url" =~ ^git://github\.com/ ]]
}

reset_architect_plugin_cache() {
  rm -rf "$PLUGIN_CACHE_DIR"

  # Interrupted git operations can leave this lock behind and block refreshes.
  rm -f "$MARKETPLACE_SHALLOW_LOCK"
}

latest_installed_plugin_root() {
  find "$PLUGIN_CACHE_DIR" -mindepth 1 -maxdepth 1 -type d | sort | tail -n1
}

hotpatch_installed_plugin_cache() {
  local installed_root=""
  installed_root="$(latest_installed_plugin_root)"
  if [[ -z "$installed_root" || ! -d "$installed_root" ]]; then
    echo "Could not find installed Architect plugin root under $PLUGIN_CACHE_DIR" >&2
    exit 1
  fi

  cp "$LOCAL_PLUGIN_ROOT/runtime/architect_runtime.cjs" "$installed_root/runtime/architect_runtime.cjs"
  cp "$LOCAL_PLUGIN_ROOT/templates/diagram-app.html" "$installed_root/templates/diagram-app.html"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url)
      REPO_URL="$2"; shift 2 ;;
    --repo-path)
      REPO_PATH="$2"; shift 2 ;;
    --run-root)
      RUN_ROOT="$2"; shift 2 ;;
    --name|--run-name)
      RUN_NAME_SUFFIX="$2"; shift 2 ;;
    --hotpatch-local-plugin)
      HOTPATCH_LOCAL_PLUGIN=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1 ;;
  esac
done

if [[ -n "$REPO_URL" && -n "$REPO_PATH" ]]; then
  echo "Use at most one of --repo-url or --repo-path." >&2
  exit 1
fi

if [[ -n "$REPO_URL" ]] && is_github_repo_url "$REPO_URL"; then
  CLAUDE_PROMPT="$INIT_PROMPT"
fi

timestamp="$(date +%Y%m%d-%H%M%S)-$RANDOM"
if [[ -n "$RUN_NAME_SUFFIX" ]]; then
  SAFE_SUFFIX="$(printf '%s' "$RUN_NAME_SUFFIX" | tr '[:space:]' '-' | tr -cd '[:alnum:]_.-')"
  SAFE_SUFFIX="${SAFE_SUFFIX#-}"
  SAFE_SUFFIX="${SAFE_SUFFIX%-}"
  if [[ -z "$SAFE_SUFFIX" ]]; then
    echo "Invalid --name value: '$RUN_NAME_SUFFIX'" >&2
    echo "Use letters, numbers, dot, underscore, or dash." >&2
    exit 1
  fi
  RUN_DIR="$RUN_ROOT/run-$timestamp-$SAFE_SUFFIX"
  SESSION_NAME="$SAFE_SUFFIX"
else
  RUN_DIR="$RUN_ROOT/run-$timestamp"
  SESSION_NAME="$(basename "$RUN_DIR")"
fi

if [[ -e "$RUN_DIR" ]]; then
  echo "Run dir already exists: $RUN_DIR" >&2
  exit 1
fi

RUN_NAME="$(basename "$RUN_DIR")"
TARGET_REPO_DIR="$RUN_DIR/repo"

mkdir -p "$RUN_DIR"/{repo,.claude}

if [[ -n "$REPO_URL" ]]; then
  git clone "$REPO_URL" "$TARGET_REPO_DIR"
elif [[ -n "$REPO_PATH" ]]; then
  if [[ ! -d "$REPO_PATH" ]]; then
    echo "Repo path not found: $REPO_PATH" >&2
    exit 1
  fi
  mkdir -p "$TARGET_REPO_DIR"
  cp -a "$REPO_PATH"/. "$TARGET_REPO_DIR/"
else
  mkdir -p "$TARGET_REPO_DIR"
  cat > "$TARGET_REPO_DIR/README.md" <<'EOF'
No repo was provided for this run.

This is intentional for plan-only production install tests.
EOF
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "Run ready: $RUN_DIR" >&2
  echo "ERROR: could not find 'claude' in PATH." >&2
  exit 127
fi

CLAUDE_CMD=(claude)

echo "Configuring published Architect marketplace and plugin..."
echo "Resetting shared Architect plugin cache..."
reset_architect_plugin_cache
(
  cd "$RUN_DIR"
  "${CLAUDE_CMD[@]}" plugin marketplace add "$MARKETPLACE_URL" --scope local
  "${CLAUDE_CMD[@]}" plugin marketplace update plugins
  "${CLAUDE_CMD[@]}" plugin install "$PLUGIN_INSTALL_NAME" --scope local
)

if (( HOTPATCH_LOCAL_PLUGIN )); then
  echo "Hotpatching installed Architect plugin cache from this worktree..."
  hotpatch_installed_plugin_cache
fi

cat > "$RUN_DIR/notes.md" <<EOF
# Production Install Test Run Notes

- mode: published-plugin
- run_dir: $RUN_DIR
- run_name: $RUN_NAME
- session_name: $SESSION_NAME
- repo_dir: $TARGET_REPO_DIR
- created_at_utc: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Install commands

\`\`\`bash
rm -rf $PLUGIN_CACHE_DIR
rm -f $MARKETPLACE_SHALLOW_LOCK
claude plugin marketplace add $MARKETPLACE_URL --scope local
claude plugin marketplace update plugins
claude plugin install $PLUGIN_INSTALL_NAME --scope local
\`\`\`

## Claude launch

This run auto-starts Claude in this directory with:

claude --name "$SESSION_NAME" --model "$CLAUDE_MODEL" --permission-mode plan --dangerously-load-development-channels plugin:architect@plugins --append-system-prompt "$CHANNEL_SYSTEM_PROMPT" --dangerously-skip-permissions -- "$CLAUDE_PROMPT"

(Working directory: $RUN_DIR)

## Default Architect outputs

If you do not specify a custom output path in Claude, Architect should write visible artifacts under:

- $RUN_DIR/architecture/
- $RUN_DIR/architecture/diagram.html

## Plugin configuration

- marketplace_url: $MARKETPLACE_URL
- plugin_install_name: $PLUGIN_INSTALL_NAME
- install_scope: local
- model: $CLAUDE_MODEL
- hotpatch_local_plugin: $HOTPATCH_LOCAL_PLUGIN

## Prompt

\`\`\`
$CLAUDE_PROMPT
\`\`\`

This run intentionally exercises the public GitHub marketplace install flow instead of the repo-local plugin bundle so you can validate the published end-user path without mutating your normal Claude config.
EOF

echo "Run ready: $RUN_DIR"
echo "Created: $RUN_DIR/notes.md"
echo "Launching Claude with the published Architect plugin configured..."

cd "$RUN_DIR"
exec "${CLAUDE_CMD[@]}" \
  --name "$SESSION_NAME" \
  --model "$CLAUDE_MODEL" \
  --permission-mode plan \
  --dangerously-load-development-channels plugin:architect@plugins \
  --append-system-prompt "$CHANNEL_SYSTEM_PROMPT" \
  --dangerously-skip-permissions \
  -- \
  "$CLAUDE_PROMPT"
