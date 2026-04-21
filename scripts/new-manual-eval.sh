#!/usr/bin/env bash
set -euo pipefail

# One-shot isolated manual eval setup.
# Creates a per-run sandbox with:
#   - isolated Architect git worktree used as the Claude workspace
#   - copied source skill snapshot for reference
#   - copied shared skill references (skills/references)
#   - copied Architect Claude plugin snapshot
#   - isolated eval target repo checkout/copy under the worktree

usage() {
  cat <<'EOF'
Usage:
  new-manual-eval.sh [--repo-url <git-url> | --repo-path <local-path>]

Options:
  --repo-url <url>       Clone target repo into the eval worktree (optional)
  --repo-path <path>     Copy local repo into the eval worktree (optional)
  --run-root <path>      Parent folder for runs (default: ~/tmp/architect-manual-evals)
  --name <suffix>        Optional folder name suffix appended after timestamp; also used as Claude session name
  --skills <csv>         Skill dirs to snapshot for reference (default: architect-plan,architect-init,architect-diagram)
  --with-skill           Configure the Architect plugin for this run (default)
  --without-skill        Do not configure the Architect plugin (baseline run)
  -h, --help             Show help

Example:
  ./scripts/new-manual-eval.sh --repo-url https://github.com/openfga/openfga.git --name openfga-baseline
EOF
}

REPO_URL=""
REPO_PATH=""
RUN_ROOT="$HOME/tmp/architect-manual-evals"
RUN_NAME_SUFFIX=""
SKILLS_CSV="architect-plan,architect-init,architect-diagram"
WITH_SKILL=1

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
    --skills)
      SKILLS_CSV="$2"; shift 2 ;;
    --with-skill)
      WITH_SKILL=1; shift ;;
    --without-skill)
      WITH_SKILL=0; shift ;;
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHITECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_ROOT="$ARCHITECT_ROOT/skills"

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

WORKTREE_DIR="$RUN_DIR/worktree"
TARGET_REPO_DIR="$WORKTREE_DIR/repo"

mkdir -p "$RUN_DIR/skills"

PLUGIN_MARKETPLACE_DIR="$ARCHITECT_ROOT/claude-plugin"
PLUGIN_DIR="$PLUGIN_MARKETPLACE_DIR/architect"
PLUGIN_INSTALL_NAME="architect@architect-local"

if (( WITH_SKILL )); then
  echo "Syncing Architect plugin bundle..."
  python3 "$ARCHITECT_ROOT/scripts/sync-claude-plugin.py"

  # Copy shared references used by multiple skills (e.g., architecture-contract.md)
  if [[ -d "$SKILLS_ROOT/references" ]]; then
    cp -R "$SKILLS_ROOT/references" "$RUN_DIR/skills/references"
  fi

  IFS=',' read -r -a SKILLS <<< "$SKILLS_CSV"
  for s in "${SKILLS[@]}"; do
    src="$SKILLS_ROOT/$s"
    dst="$RUN_DIR/skills/$s"
    if [[ ! -d "$src" ]]; then
      echo "Skill not found: $src" >&2
      exit 1
    fi
    cp -R "$src" "$dst"
  done

  if [[ ! -d "$PLUGIN_MARKETPLACE_DIR" ]]; then
    echo "Claude plugin root not found: $PLUGIN_MARKETPLACE_DIR" >&2
    exit 1
  fi
fi

echo "Creating isolated Architect worktree..."
git -C "$ARCHITECT_ROOT" worktree add --detach "$WORKTREE_DIR" HEAD

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

This is intentional for plan-only/manual evals (e.g., testing architect-plan).
EOF
fi

if (( WITH_SKILL )); then
  MODE="with-skill"
else
  MODE="without-skill"
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "Run ready: $RUN_DIR" >&2
  echo "ERROR: could not find 'claude' in PATH." >&2
  exit 127
fi

CLAUDE_CMD=(claude)
LAUNCH_CMD_DISPLAY="claude"

CHANNEL_SYSTEM_PROMPT="When an architect-comments channel event arrives, acknowledge it immediately, inspect the referenced job and output root, implement the requested updates directly, use update_feedback_status for progress, use finalize_feedback_update instead of guessing render commands, and do not stop after proposing a plan unless you are blocked or the feedback is genuinely ambiguous or high-risk."

if (( WITH_SKILL )); then
  echo "Configuring local Architect marketplace and plugin..."
  (
    cd "$WORKTREE_DIR"
    "${CLAUDE_CMD[@]}" plugin marketplace add "$PLUGIN_MARKETPLACE_DIR" --scope local
    "${CLAUDE_CMD[@]}" plugin install "$PLUGIN_INSTALL_NAME" --scope local
  )
fi

cat > "$WORKTREE_DIR/notes.md" <<EOF
# Manual Eval Run Notes

- mode: $MODE
- run_dir: $RUN_DIR
- run_name: $RUN_NAME
- session_name: $SESSION_NAME
- worktree_dir: $WORKTREE_DIR
- repo_dir: $TARGET_REPO_DIR
- skills_dir: $RUN_DIR/skills
- created_at_utc: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Claude launch

This run auto-starts Claude in this directory with:

$LAUNCH_CMD_DISPLAY --name "$SESSION_NAME"$( (( WITH_SKILL )) && printf ' --dangerously-load-development-channels plugin:architect@architect-local' ) --permission-mode plan$( (( WITH_SKILL )) && printf ' --append-system-prompt "%s"' "$CHANNEL_SYSTEM_PROMPT" )

(Working directory: $WORKTREE_DIR)

## Default Architect outputs

If you do not specify a custom output path in Claude, Architect should write visible artifacts under:

- $WORKTREE_DIR/architecture/
- $WORKTREE_DIR/architecture/diagram.html

EOF

if (( WITH_SKILL )); then
cat >> "$WORKTREE_DIR/notes.md" <<EOF

## Plugin configuration

- marketplace_dir: $PLUGIN_MARKETPLACE_DIR
- plugin_install_name: $PLUGIN_INSTALL_NAME
- plugin_dir: $PLUGIN_DIR
- source skill snapshot: $RUN_DIR/skills

This run syncs the repo-local Architect plugin, installs architect@architect-local, and launches Claude with that plugin enabled.
EOF
fi

echo "Run ready: $RUN_DIR"
echo "Created: $WORKTREE_DIR/notes.md"
if (( WITH_SKILL )); then
  echo "Launching Claude with the Architect plugin configured..."
else
  echo "Launching Claude without the Architect plugin..."
fi

cd "$WORKTREE_DIR"
if (( WITH_SKILL )); then
  exec "${CLAUDE_CMD[@]}" \
    --name "$SESSION_NAME" \
    --dangerously-load-development-channels "plugin:architect@architect-local" \
    --permission-mode plan \
    --append-system-prompt "$CHANNEL_SYSTEM_PROMPT"
else
  exec "${CLAUDE_CMD[@]}" --name "$SESSION_NAME" --permission-mode plan
fi
