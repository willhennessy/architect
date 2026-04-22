#!/usr/bin/env bash
set -euo pipefail

# One-shot isolated Architect test runner.
# Supports either:
#   - the published GitHub marketplace install path
#   - the repo-local plugin bundle under development

usage() {
  cat <<'EOF'
Usage:
  run-test.sh --plugin-source <published|prod|local> [--repo-url <git-url> | --repo-path <local-path>]

Options:
  --plugin-source <source>  Plugin source to test: published|prod|local
  --repo-url <url>          Clone target repo into isolated run folder (optional)
  --repo-path <path>        Copy local repo into isolated run folder (optional)
  --run-root <path>         Parent folder for source-specific runs (default: ~/tmp/architect-test-runs)
  --name <suffix>           Optional folder name suffix appended after timestamp; also used as Claude session name
  --skills <csv>            Skill dirs to snapshot for local runs (default: architect-plan,architect-init,architect-diagram)
  --model <model>           Claude model override (default: claude-haiku-4-5)
  --prompt <text>           Explicit Claude prompt to run on launch
  --no-default-prompt       Launch Claude without the built-in default prompt for the selected source
  -h, --help                Show help

Examples:
  ./scripts/run-test.sh --plugin-source published --name published-smoke
  ./scripts/run-test.sh --plugin-source local --repo-url https://github.com/openfga/openfga.git --name openfga-local
EOF
}

PLUGIN_SOURCE=""
REPO_URL=""
REPO_PATH=""
RUN_ROOT="$HOME/tmp/architect-test-runs"
RUN_NAME_SUFFIX=""
SKILLS_CSV="architect-plan,architect-init,architect-diagram"
CLAUDE_MODEL=""
EXPLICIT_PROMPT=""
NO_DEFAULT_PROMPT=0

MARKETPLACE_URL="https://github.com/willhennessy/architect.git"
PUBLISHED_PLUGIN_INSTALL_NAME="architect@plugins"
LOCAL_PLUGIN_INSTALL_NAME="architect@architect-local"
DEFAULT_MODEL="claude-haiku-4-5"
PLAN_PROMPT="/architect:plan Design a simple news feed web app with frontend and backend. Make assumptions. Do NOT ask me any questions up front. You MUST generate the interactive architecture diagram. You MUST generate at least 1 container and 2 components. Keep your token usage low."
INIT_PROMPT="/architect:init"
CHANNEL_SYSTEM_PROMPT="When an architect-comments channel event arrives, treat the channel text as the user-visible acknowledgment, inspect the referenced job and output root from the channel metadata, especially comments_summary and comments_json, implement the requested updates directly, use update_feedback_status for progress, use finalize_feedback_update instead of guessing render commands, and do not stop after proposing a plan unless you are blocked or the feedback is genuinely ambiguous or high-risk. If the comment is a connectivity check, a simple acknowledgment, or otherwise does not request an architecture change, resolve it immediately by calling update_feedback_status with state=completed and a concise message such as \"Resolved 1 comment. No architecture changes were requested.\" Do not ask a follow-up question for those no-op comments."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_ROOT="$REPO_ROOT/skills"
LOCAL_PLUGIN_ROOT="$REPO_ROOT/claude-plugin/architect"
PLUGIN_MARKETPLACE_SOURCE_DIR="$REPO_ROOT/claude-plugin"
PLUGIN_CACHE_DIR="$HOME/.claude/plugins/cache/plugins/architect"
MARKETPLACE_GIT_DIR="$HOME/.claude/plugins/marketplaces/plugins"
MARKETPLACE_SHALLOW_LOCK="$MARKETPLACE_GIT_DIR/.git/shallow.lock"

normalize_plugin_source() {
  case "${1:-}" in
    local) echo "local" ;;
    prod|published) echo "published" ;;
    *)
      echo "" ;;
  esac
}

is_github_repo_url() {
  local url="${1:-}"
  [[ "$url" =~ ^https?://github\.com/ ]] || \
    [[ "$url" =~ ^git@github\.com: ]] || \
    [[ "$url" =~ ^ssh://git@github\.com/ ]] || \
    [[ "$url" =~ ^git://github\.com/ ]]
}

reset_architect_plugin_cache() {
  rm -rf "$PLUGIN_CACHE_DIR"
  rm -f "$MARKETPLACE_SHALLOW_LOCK"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin-source)
      PLUGIN_SOURCE="$(normalize_plugin_source "${2:-}")"; shift 2 ;;
    --repo-url)
      REPO_URL="$2"; shift 2 ;;
    --repo-path)
      REPO_PATH="$2"; shift 2 ;;
    --run-root)
      RUN_ROOT="$2"; shift 2 ;;
    --name|--run-name)
      RUN_NAME_SUFFIX="$2"; shift 2 ;;
    --skills)
      SKILLS_CSV="$2"; shift 2 ;;
    --model)
      CLAUDE_MODEL="$2"; shift 2 ;;
    --prompt)
      EXPLICIT_PROMPT="$2"; shift 2 ;;
    --no-default-prompt)
      NO_DEFAULT_PROMPT=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1 ;;
  esac
done

if [[ -z "$PLUGIN_SOURCE" ]]; then
  echo "--plugin-source is required: published|prod|local" >&2
  usage
  exit 1
fi

if [[ -n "$REPO_URL" && -n "$REPO_PATH" ]]; then
  echo "Use at most one of --repo-url or --repo-path." >&2
  exit 1
fi

if [[ -z "$CLAUDE_MODEL" ]]; then
  CLAUDE_MODEL="$DEFAULT_MODEL"
fi

CLAUDE_PROMPT="$EXPLICIT_PROMPT"
if [[ -z "$CLAUDE_PROMPT" && "$NO_DEFAULT_PROMPT" -eq 0 ]]; then
  if [[ -n "$REPO_URL" ]] && is_github_repo_url "$REPO_URL"; then
    CLAUDE_PROMPT="$INIT_PROMPT"
  else
    CLAUDE_PROMPT="$PLAN_PROMPT"
  fi
fi

timestamp="$(date +%Y%m%d-%H%M%S)-$RANDOM"
SOURCE_RUN_ROOT="$RUN_ROOT/$PLUGIN_SOURCE"
mkdir -p "$SOURCE_RUN_ROOT"
if [[ -n "$RUN_NAME_SUFFIX" ]]; then
  SAFE_SUFFIX="$(printf '%s' "$RUN_NAME_SUFFIX" | tr '[:space:]' '-' | tr -cd '[:alnum:]_.-')"
  SAFE_SUFFIX="${SAFE_SUFFIX#-}"
  SAFE_SUFFIX="${SAFE_SUFFIX%-}"
  if [[ -z "$SAFE_SUFFIX" ]]; then
    echo "Invalid --name value: '$RUN_NAME_SUFFIX'" >&2
    echo "Use letters, numbers, dot, underscore, or dash." >&2
    exit 1
  fi
  RUN_DIR="$SOURCE_RUN_ROOT/run-$timestamp-$SAFE_SUFFIX"
  SESSION_NAME="$SAFE_SUFFIX"
else
  RUN_DIR="$SOURCE_RUN_ROOT/run-$timestamp"
  SESSION_NAME="$(basename "$RUN_DIR")"
fi

if [[ -e "$RUN_DIR" ]]; then
  echo "Run dir already exists: $RUN_DIR" >&2
  exit 1
fi

RUN_NAME="$(basename "$RUN_DIR")"
TARGET_REPO_DIR="$RUN_DIR/repo"
mkdir -p "$RUN_DIR"/{repo,architecture,.claude}

if [[ "$PLUGIN_SOURCE" == "local" ]]; then
  mkdir -p "$RUN_DIR"/skills
fi

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

This is intentional for plan-only Architect test runs.
EOF
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "Run ready: $RUN_DIR" >&2
  echo "ERROR: could not find 'claude' in PATH." >&2
  exit 127
fi

CLAUDE_CMD=(claude)
RUN_PLUGIN_MARKETPLACE_DIR="$RUN_DIR/claude-plugin"
RUN_PLUGIN_DIR="$RUN_PLUGIN_MARKETPLACE_DIR/architect"
PLUGIN_LOAD_CHANNEL=""
PLUGIN_INSTALL_NAME=""
VALIDATION_SCOPE_TEXT=""
PLUGIN_CONFIGURATION_TEXT=""

if [[ "$PLUGIN_SOURCE" == "local" ]]; then
  echo "Syncing Architect plugin bundle..."
  python3 "$REPO_ROOT/scripts/sync-claude-plugin.py"

  if [[ -d "$SKILLS_ROOT/references" ]]; then
    cp -R "$SKILLS_ROOT/references" "$RUN_DIR/skills/references"
  fi

  IFS=',' read -r -a SKILLS <<< "$SKILLS_CSV"
  for skill_name in "${SKILLS[@]}"; do
    src="$SKILLS_ROOT/$skill_name"
    dst="$RUN_DIR/skills/$skill_name"
    if [[ ! -d "$src" ]]; then
      echo "Skill not found: $src" >&2
      exit 1
    fi
    cp -R "$src" "$dst"
  done

  if [[ ! -d "$PLUGIN_MARKETPLACE_SOURCE_DIR" ]]; then
    echo "Claude plugin root not found: $PLUGIN_MARKETPLACE_SOURCE_DIR" >&2
    exit 1
  fi

  mkdir -p "$RUN_PLUGIN_MARKETPLACE_DIR"
  cp -R "$PLUGIN_MARKETPLACE_SOURCE_DIR"/. "$RUN_PLUGIN_MARKETPLACE_DIR"/

  echo "Configuring local Architect marketplace and plugin..."
  (
    cd "$RUN_DIR"
    "${CLAUDE_CMD[@]}" plugin marketplace add "$RUN_PLUGIN_MARKETPLACE_DIR" --scope local
    "${CLAUDE_CMD[@]}" plugin install "$LOCAL_PLUGIN_INSTALL_NAME" --scope local
  )

  PLUGIN_LOAD_CHANNEL="plugin:architect@architect-local"
  PLUGIN_INSTALL_NAME="$LOCAL_PLUGIN_INSTALL_NAME"
  VALIDATION_SCOPE_TEXT="$(cat <<'EOF'
This run uses the synced repo-local Architect plugin bundle copied into the run directory.
Use this mode to validate local runtime, template, and prompt changes before publishing.
EOF
)"
  PLUGIN_CONFIGURATION_TEXT="$(cat <<EOF
- plugin_source: local
- source_marketplace_dir: $PLUGIN_MARKETPLACE_SOURCE_DIR
- run_marketplace_dir: $RUN_PLUGIN_MARKETPLACE_DIR
- plugin_install_name: $PLUGIN_INSTALL_NAME
- plugin_dir: $RUN_PLUGIN_DIR
- source_skill_snapshot: $RUN_DIR/skills
- model: ${CLAUDE_MODEL:-default}

This run syncs the repo-local Architect plugin, copies that marketplace into the run directory, installs $PLUGIN_INSTALL_NAME from the copied marketplace, and launches Claude with that plugin enabled.
EOF
)"
else
  echo "Configuring published Architect marketplace and plugin..."
  echo "Resetting shared Architect plugin cache..."
  reset_architect_plugin_cache
  (
    cd "$RUN_DIR"
    "${CLAUDE_CMD[@]}" plugin marketplace add "$MARKETPLACE_URL" --scope local
    "${CLAUDE_CMD[@]}" plugin marketplace update plugins
    "${CLAUDE_CMD[@]}" plugin install "$PUBLISHED_PLUGIN_INSTALL_NAME" --scope local
  )

  PLUGIN_LOAD_CHANNEL="plugin:architect@plugins"
  PLUGIN_INSTALL_NAME="$PUBLISHED_PLUGIN_INSTALL_NAME"
  VALIDATION_SCOPE_TEXT="$(cat <<'EOF'
This run installs the currently published GitHub marketplace bundle only.
Use this mode to validate the end-user published install path.
EOF
)"
  PLUGIN_CONFIGURATION_TEXT="$(cat <<EOF
- plugin_source: published
- marketplace_url: $MARKETPLACE_URL
- plugin_install_name: $PLUGIN_INSTALL_NAME
- install_scope: local
- model: ${CLAUDE_MODEL:-default}

This run intentionally exercises the public GitHub marketplace install flow instead of the repo-local plugin bundle so you can validate the published end-user path without mutating your normal Claude config.
EOF
)"
fi

LAUNCH_CMD_DISPLAY="claude --name \"$SESSION_NAME\""
if [[ -n "$CLAUDE_MODEL" ]]; then
  LAUNCH_CMD_DISPLAY="$LAUNCH_CMD_DISPLAY --model \"$CLAUDE_MODEL\""
fi
LAUNCH_CMD_DISPLAY="$LAUNCH_CMD_DISPLAY --permission-mode plan --dangerously-load-development-channels \"$PLUGIN_LOAD_CHANNEL\" --append-system-prompt \"$CHANNEL_SYSTEM_PROMPT\""
if [[ "$PLUGIN_SOURCE" == "published" ]]; then
  LAUNCH_CMD_DISPLAY="$LAUNCH_CMD_DISPLAY --dangerously-skip-permissions"
fi
if [[ -n "$CLAUDE_PROMPT" ]]; then
  LAUNCH_CMD_DISPLAY="$LAUNCH_CMD_DISPLAY -- \"$CLAUDE_PROMPT\""
fi

cat > "$RUN_DIR/notes.md" <<EOF
# Architect Test Run Notes

- plugin_source: $PLUGIN_SOURCE
- run_dir: $RUN_DIR
- run_name: $RUN_NAME
- session_name: $SESSION_NAME
- repo_dir: $TARGET_REPO_DIR
- created_at_utc: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Claude launch

This run auto-starts Claude in this directory with:

$LAUNCH_CMD_DISPLAY

(Working directory: $RUN_DIR)

## Default Architect outputs

If you do not specify a custom output path in Claude, Architect should write visible artifacts under:

- $RUN_DIR/architecture/
- $RUN_DIR/architecture/diagram.html

## Plugin configuration

$PLUGIN_CONFIGURATION_TEXT

## Validation scope

$VALIDATION_SCOPE_TEXT
EOF

if [[ -n "$CLAUDE_PROMPT" ]]; then
  cat >> "$RUN_DIR/notes.md" <<EOF

## Prompt

\`\`\`
$CLAUDE_PROMPT
\`\`\`
EOF
fi

echo "Run ready: $RUN_DIR"
echo "Created: $RUN_DIR/notes.md"
echo "Validation mode: $PLUGIN_SOURCE"
echo "Launching Claude with plugin source '$PLUGIN_SOURCE'..."

LAUNCH_ARGS=(--name "$SESSION_NAME")
if [[ -n "$CLAUDE_MODEL" ]]; then
  LAUNCH_ARGS+=(--model "$CLAUDE_MODEL")
fi
LAUNCH_ARGS+=(--permission-mode plan)
LAUNCH_ARGS+=(--dangerously-load-development-channels "$PLUGIN_LOAD_CHANNEL")
LAUNCH_ARGS+=(--append-system-prompt "$CHANNEL_SYSTEM_PROMPT")
if [[ "$PLUGIN_SOURCE" == "published" ]]; then
  LAUNCH_ARGS+=(--dangerously-skip-permissions)
fi

cd "$RUN_DIR"
if [[ -n "$CLAUDE_PROMPT" ]]; then
  exec "${CLAUDE_CMD[@]}" "${LAUNCH_ARGS[@]}" -- "$CLAUDE_PROMPT"
fi

exec "${CLAUDE_CMD[@]}" "${LAUNCH_ARGS[@]}"
